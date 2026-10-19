import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core import security
from app.api.dependencies import get_current_user, get_db
from app.core.database import Base
from app.main import app
from app.models.user import User
from app.models.embedding import Embedding
from app.models.video import Video
from app.models.video_content import VideoContent
from app.retrieval.explanations import Evidence, explain_match
from app.retrieval.hybrid_search import (
    _documents,
    _lexical_score,
    _protein_quantity,
    _tokens,
    search_videos,
)
from app.schemas.search import SearchRequest
from app.services.indexing_service import (
    IndexingService,
    _upsert_content,
    index_video_batch,
)
from app.services.summary_service import SummaryService
from app.services.embedding_service import build_embedding_inputs
from app.utils.url_validation import normalize_video_url
from app.utils.ffmpeg import find_ffmpeg


class FFmpegDiscoveryTests(unittest.TestCase):
    def test_finds_ffmpeg_installed_by_winget_without_path_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = (
                root
                / "Microsoft"
                / "WinGet"
                / "Packages"
                / "Gyan.FFmpeg.Shared_test"
                / "ffmpeg-build"
                / "bin"
                / "ffmpeg.exe"
            )
            executable.parent.mkdir(parents=True)
            executable.touch()

            with (
                patch.object(os, "name", "nt"),
                patch.dict(os.environ, {"LOCALAPPDATA": str(root)}, clear=False),
                patch("app.utils.ffmpeg.shutil.which", return_value=None),
                patch("app.utils.ffmpeg.settings.ffmpeg_path", ""),
            ):
                self.assertEqual(find_ffmpeg(), str(executable.resolve()))


class BulkIndexingWorkerTests(unittest.TestCase):
    def test_unexpected_video_failure_does_not_stop_the_batch(self) -> None:
        with (
            patch(
                "app.services.indexing_service.index_video",
                side_effect=[RuntimeError("unexpected failure"), None],
            ) as index_video,
            patch("app.services.indexing_service.logger") as logger,
        ):
            index_video_batch(["video-fails", "video-succeeds"])

        self.assertEqual(index_video.call_count, 2)
        self.assertEqual(
            [call.args[0] for call in index_video.call_args_list],
            ["video-fails", "video-succeeds"],
        )
        logger.exception.assert_called_once_with(
            "Bulk indexing failed unexpectedly for video %s", "video-fails"
        )


class ProvenanceBoundaryTests(unittest.TestCase):
    def test_embedding_inputs_exclude_annotations_and_evaluation_labels(self) -> None:
        video = SimpleNamespace(
            title="Source title",
            source_caption="Source caption",
            manual_category="CATEGORYUNIQUELABEL",
            curation_notes="CURATION_ONLY_SENTINEL",
            evaluation_label="EVALUATION_ONLY_SENTINEL",
            source_metadata={"tags": ["DATASET_ONLY_SENTINEL"]},
        )
        content = SimpleNamespace(
            id="content-1",
            content_type="transcript",
            source_type="audio",
            source_field="original_transcript",
            processing_status="completed",
            text="The speaker describes a linked list.",
        )
        annotation_as_content = SimpleNamespace(
            id="annotation-1",
            content_type="transcript",
            source_type="audio",
            source_field="curation_notes",
            processing_status="completed",
            text="CURATION_ONLY_SENTINEL",
        )
        evaluation_as_content = SimpleNamespace(
            id="evaluation-1",
            content_type="evaluation_judgment",
            source_type="model_generated",
            source_field="evaluation_label",
            processing_status="completed",
            text="EVALUATION_ONLY_SENTINEL",
        )

        inputs = build_embedding_inputs(
            video, [content, annotation_as_content, evaluation_as_content]
        )
        combined = " ".join(item["text"] for item in inputs)

        self.assertIn("Source title", combined)
        self.assertIn("The speaker describes", combined)
        self.assertNotIn("CATEGORYUNIQUELABEL", combined)
        self.assertNotIn("CURATION_ONLY_SENTINEL", combined)
        self.assertNotIn("EVALUATION_ONLY_SENTINEL", combined)
        self.assertNotIn("DATASET_ONLY_SENTINEL", combined)

    def test_search_documents_exclude_annotations_by_default(self) -> None:
        video = SimpleNamespace(
            id="v1",
            title="A source title",
            source_caption="A source caption",
            source="youtube",
            creator="creator",
            duration=30,
            source_metadata={"tags": []},
            manual_category="CATEGORYUNIQUELABEL",
            curation_notes="CURATION_ONLY_SENTINEL",
        )

        forged_annotation = SimpleNamespace(
            id="annotation-content",
            video_id="v1",
            content_type="transcript",
            text="CURATION_ONLY_SENTINEL",
            source_type="audio",
            source_field="curation_notes",
            processing_status="completed",
            timestamp_start=None,
        )
        forged_judgment = SimpleNamespace(
            id="evaluation-content",
            video_id="v1",
            content_type="evaluation_judgment",
            text="EVALUATION_ONLY_SENTINEL",
            source_type="model_generated",
            source_field="evaluation_label",
            processing_status="completed",
            timestamp_start=None,
        )
        docs = _documents(
            [video],
            [forged_annotation, forged_judgment],
            include_annotations=False,
        )
        searchable_text = " ".join(document.text for document in docs)

        self.assertNotIn("CATEGORYUNIQUELABEL", searchable_text)
        self.assertNotIn("CURATION_ONLY_SENTINEL", searchable_text)
        self.assertNotIn("EVALUATION_ONLY_SENTINEL", searchable_text)
        self.assertTrue(all(document.is_metadata for document in docs))

    def test_search_request_defaults_to_annotation_free_benchmark(self) -> None:
        from app.schemas.search import SearchRequest

        request = SearchRequest(query="a memory query")

        self.assertTrue(request.benchmark)
        self.assertFalse(request.include_user_annotations)

    def test_lexical_score_uses_content_overlap(self) -> None:
        score = _lexical_score({"linked", "list"}, "A linked list reversal tutorial")

        self.assertGreater(score, 0)
        self.assertEqual(_lexical_score({"cafe"}, "A linked list reversal tutorial"), 0)

    def test_gram_abbreviations_and_protein_amounts_are_normalized(self) -> None:
        query = "healthy recipe 45gm protein"

        self.assertIn("45g", _tokens(query))
        self.assertIn("45g", _tokens("45 grams of protein"))
        self.assertEqual(_protein_quantity(query), 45)
        self.assertEqual(_protein_quantity("around 45g protein per serving"), 45)
        self.assertGreater(
            _lexical_score(
                _tokens(query),
                "Healthy recipe with around 45g protein per serving",
                _protein_quantity(query),
            ),
            _lexical_score(
                _tokens(query),
                "Healthy recipe with 33g protein in a wrap",
                _protein_quantity(query),
            ),
        )


class UserScopedSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine, expire_on_commit=False)()
        self.session.add_all(
            [
                User(
                    id="owner-1",
                    email="owner1@example.com",
                    full_name="Owner One",
                    hashed_password="",
                ),
                User(
                    id="owner-2",
                    email="owner2@example.com",
                    full_name="Owner Two",
                    hashed_password="",
                ),
            ]
        )
        self.session.add(
            Video(
                id="video-1",
                user_id="owner-1",
                title="Linked list tutorial",
                url="https://www.youtube.com/watch?v=AbCdEf12345",
                canonical_url="https://www.youtube.com/watch?v=AbCdEf12345",
                source="youtube",
                permission_status="unknown",
                manual_category="CATEGORYUNIQUELABEL",
                curation_notes="CURATION_ONLY_SENTINEL",
                source_metadata={},
                stage_statuses={},
                status="indexed",
            )
        )
        self.session.add(
            VideoContent(
                id="content-1",
                video_id="video-1",
                content_type="transcript",
                text="Reverse the linked list by updating each next pointer.",
                source_type="audio",
                source_field="original_transcript",
                content_key="stable-content-key",
                processing_status="completed",
            )
        )
        self.session.commit()

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_stage_status_updates_are_persisted(self) -> None:
        video = self.session.query(Video).filter_by(id="video-1").one()
        video.stage_statuses["metadata"] = "completed"
        self.session.commit()
        self.session.expire_all()

        reloaded = self.session.query(Video).filter_by(id="video-1").one()
        self.assertEqual(reloaded.stage_statuses["metadata"], "completed")

    def test_bulk_reindex_is_authenticated_user_scoped_and_skips_active_videos(self) -> None:
        self.session.add_all(
            [
                Video(
                    id="owner-1-queued",
                    user_id="owner-1",
                    title="Queued video",
                    url="https://www.youtube.com/watch?v=QuEuEd12345",
                    canonical_url="https://www.youtube.com/watch?v=QuEuEd12345",
                    source="youtube",
                    permission_status="unknown",
                    source_metadata={},
                    stage_statuses={},
                    status="queued",
                ),
                Video(
                    id="owner-1-processing",
                    user_id="owner-1",
                    title="Processing video",
                    url="https://www.youtube.com/watch?v=PrOcEs12345",
                    canonical_url="https://www.youtube.com/watch?v=PrOcEs12345",
                    source="youtube",
                    permission_status="unknown",
                    source_metadata={},
                    stage_statuses={},
                    status="processing",
                ),
                Video(
                    id="owner-2-video",
                    user_id="owner-2",
                    title="Another user's video",
                    url="https://www.youtube.com/watch?v=AnOtHe12345",
                    canonical_url="https://www.youtube.com/watch?v=AnOtHe12345",
                    source="youtube",
                    permission_status="authorized",
                    source_metadata={},
                    stage_statuses={},
                    status="indexed",
                ),
            ]
        )
        self.session.commit()

        def override_db():
            yield self.session

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: self.session.query(User).filter_by(
            id="owner-1"
        ).one()
        try:
            with patch("app.api.routes.videos.index_video_batch") as batch:
                client = TestClient(app)
                response = client.post("/videos/reindex-all")

            self.assertEqual(response.status_code, 202)
            self.assertEqual(
                response.json(),
                {
                    "total_count": 3,
                    "queued_count": 1,
                    "already_active_count": 2,
                    "queued_video_ids": ["video-1"],
                },
            )
            batch.assert_called_once_with(["video-1"])

            with patch("app.api.routes.videos.index_video_batch") as batch:
                duplicate_response = TestClient(app).post("/videos/reindex-all")
            self.assertEqual(duplicate_response.status_code, 202)
            self.assertEqual(duplicate_response.json()["queued_count"], 0)
            batch.assert_not_called()
            self.assertIsNone(
                self.session.query(Video).filter_by(id="owner-2-video").one().stage_statuses.get(
                    "indexing"
                )
            )
        finally:
            app.dependency_overrides.clear()

    def test_bulk_reindex_requires_authentication(self) -> None:
        def override_db():
            yield self.session

        app.dependency_overrides[get_db] = override_db
        try:
            response = TestClient(app).post("/videos/reindex-all")
            self.assertEqual(response.status_code, 401)
        finally:
            app.dependency_overrides.clear()

    def test_bulk_reindex_accepts_an_empty_library(self) -> None:
        def override_db():
            yield self.session

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: self.session.query(User).filter_by(
            id="owner-2"
        ).one()
        try:
            with patch("app.api.routes.videos.index_video_batch") as batch:
                response = TestClient(app).post("/videos/reindex-all")
            self.assertEqual(response.status_code, 202)
            self.assertEqual(
                response.json(),
                {
                    "total_count": 0,
                    "queued_count": 0,
                    "already_active_count": 0,
                    "queued_video_ids": [],
                },
            )
            batch.assert_not_called()
        finally:
            app.dependency_overrides.clear()

    def test_search_returns_owned_evidence_and_keeps_labels_out(self) -> None:
        request = SearchRequest(query="reverse linked list", mode="lexical")

        response = search_videos(self.session, request, "owner-1")

        self.assertEqual([item.video_id for item in response.results], ["video-1"])
        self.assertEqual(response.results[0].evidence.source_field, "original_transcript")
        self.assertIn("transcript", response.results[0].match_reason)
        self.assertEqual(
            search_videos(
                self.session,
                SearchRequest(query="CATEGORYUNIQUELABEL", mode="lexical"),
                "owner-1",
            ).results,
            [],
        )
        self.assertEqual(
            search_videos(
                self.session,
                SearchRequest(
                    query="CATEGORYUNIQUELABEL",
                    mode="lexical",
                    benchmark=False,
                    include_user_annotations=True,
                ),
                "owner-1",
            ).results,
            [],
        )
        self.assertEqual(
            search_videos(
                self.session,
                SearchRequest(
                    query="CURATION_ONLY_SENTINEL",
                    mode="lexical",
                    benchmark=False,
                    include_user_annotations=True,
                ),
                "owner-1",
            ).results[0].evidence.source_type,
            "user_annotation",
        )

    def test_search_never_returns_another_users_video(self) -> None:
        response = search_videos(
            self.session,
            SearchRequest(query="reverse linked list", mode="lexical"),
            "owner-2",
        )

        self.assertEqual(response.results, [])

    def test_semantic_search_embeds_query_and_ranks_matching_vectors(self) -> None:
        self.session.add(
            Embedding(
                id="semantic-vector",
                video_id="video-1",
                content_record_id="content-1",
                modality="text",
                source="content:content-1",
                model="test-model",
                vector="[0.70710678,0.70710678]",
            )
        )
        self.session.commit()

        class FakeEmbeddingService:
            available = True
            model_name = "test-model"

            @staticmethod
            def embed(query: str) -> list[float]:
                if query != "find spoken evidence":
                    raise AssertionError("Semantic query text was not passed to embed")
                return [0.70710678, 0.70710678]

        with patch(
            "app.retrieval.hybrid_search.EmbeddingService",
            return_value=FakeEmbeddingService(),
        ):
            response = search_videos(
                self.session,
                SearchRequest(query="find spoken evidence", mode="semantic"),
                "owner-1",
            )

        self.assertEqual([item.video_id for item in response.results], ["video-1"])
        self.assertIn("semantic", response.results[0].channels)

    def test_hybrid_prefers_extracted_content_over_unrelated_metadata(self) -> None:
        self.session.add(
            Video(
                id="durga-video",
                user_id="owner-1",
                title="Durga Puja reel",
                url="https://www.youtube.com/watch?v=ZyXwVu98765",
                canonical_url="https://www.youtube.com/watch?v=ZyXwVu98765",
                source="youtube",
                permission_status="unknown",
                source_metadata={},
                stage_statuses={},
                status="metadata_only",
            )
        )
        self.session.add(
            VideoContent(
                id="dupatta-content",
                video_id="video-1",
                content_type="visual_description",
                text="A bright red dupatta is paired with a contrasting green outfit.",
                source_type="video_frame",
                source_field="visual_frame_description",
                content_key="dupatta-content-key",
                processing_status="completed",
            )
        )
        self.session.commit()

        class NoEmbeddings:
            available = False
            model_name = ""

        with patch(
            "app.retrieval.hybrid_search.EmbeddingService",
            return_value=NoEmbeddings(),
        ):
            response = search_videos(
                self.session,
                SearchRequest(
                    query="red dupatta color combination",
                    mode="hybrid",
                ),
                "owner-1",
            )

        self.assertEqual([item.video_id for item in response.results], ["video-1"])
        self.assertEqual(
            response.results[0].evidence.source_field,
            "visual_frame_description",
        )

    def test_hybrid_ranks_exact_protein_amount_over_generic_recipe_metadata(self) -> None:
        self.session.add_all(
            [
                Video(
                    id="salad-45g",
                    user_id="owner-1",
                    title="45g Protein, 360 Calories | High-Protein Paneer Tikka Salad",
                    url="https://www.youtube.com/watch?v=SaLaD123456",
                    canonical_url="https://www.youtube.com/watch?v=SaLaD123456",
                    source="youtube",
                    source_caption=(
                        "Healthy vegetarian recipe with around 45g protein."
                    ),
                    permission_status="unknown",
                    source_metadata={"tags": []},
                    stage_statuses={},
                    status="metadata_only",
                ),
                Video(
                    id="wrap-33g",
                    user_id="owner-1",
                    title="High-Protein Wrap",
                    url="https://www.youtube.com/watch?v=WrAp1234567",
                    canonical_url="https://www.youtube.com/watch?v=WrAp1234567",
                    source="youtube",
                    source_caption="Healthy recipe with 33g protein in a paneer wrap.",
                    permission_status="unknown",
                    source_metadata={"tags": ["healthy recipes", "protein recipe"]},
                    stage_statuses={},
                    status="metadata_only",
                ),
            ]
        )
        self.session.commit()

        class NoEmbeddings:
            available = False
            model_name = ""

        with patch(
            "app.retrieval.hybrid_search.EmbeddingService",
            return_value=NoEmbeddings(),
        ):
            response = search_videos(
                self.session,
                SearchRequest(query="healthy recipe 45gm protein", mode="hybrid"),
                "owner-1",
            )

        self.assertEqual(response.results[0].video_id, "salad-45g")

    def test_duplicate_content_upsert_reuses_the_same_record(self) -> None:
        video = self.session.query(Video).filter_by(id="video-1").one()
        first = _upsert_content(
            self.session,
            video,
            content_type="transcript",
            content_text="A stable transcript segment.",
            source_type="audio",
            source_field="original_transcript",
            timestamp_start=1.25,
        )
        self.session.flush()
        second = _upsert_content(
            self.session,
            video,
            content_type="transcript",
            content_text="A stable transcript segment.",
            source_type="audio",
            source_field="original_transcript",
            timestamp_start=1.25,
        )
        self.session.flush()

        self.assertEqual(first.id, second.id)
        self.assertEqual(
            self.session.query(VideoContent)
            .filter_by(video_id="video-1", content_key=first.content_key)
            .count(),
            1,
        )

    def test_unsupported_reindexing_preserves_prior_evidence_and_vector(self) -> None:
        video = self.session.query(Video).filter_by(id="video-1").one()
        old_content = VideoContent(
            id="previous-transcript",
            video_id=video.id,
            content_type="transcript",
            text="Previously indexed spoken evidence.",
            source_type="audio",
            source_field="original_transcript",
            content_key="previous-transcript-key",
            processing_status="completed",
        )
        old_vector = Embedding(
            id="previous-vector",
            video_id=video.id,
            content_record_id=old_content.id,
            modality="text",
            source=f"content:{old_content.id}",
            model="test-model",
            vector="[0.1,0.2]",
        )
        self.session.add_all([old_content, old_vector])
        self.session.commit()

        class FakeMetadataService:
            def extract(self, url: str) -> dict[str, str]:
                return {"id": "AbCdEf12345", "url": url}

            @staticmethod
            def source_fields(info: dict[str, str]) -> dict[str, object]:
                return {
                    "title": "Updated title",
                    "source_caption": info["url"],
                }

        class UnsupportedTranscriber:
            @staticmethod
            def transcribe(path: Path) -> dict[str, object]:
                if path.suffix != ".mp4":
                    raise ValueError("Unexpected test media path")
                return {"status": "unsupported", "segments": [], "language": None}

        class UnsupportedOCR:
            @staticmethod
            def extract(path: Path) -> dict[str, object]:
                if path.suffix != ".mp4":
                    raise ValueError("Unexpected test media path")
                return {"status": "unsupported", "items": []}

        class UnsupportedVision:
            @staticmethod
            def describe_frames(path: Path) -> dict[str, object]:
                if path.suffix != ".mp4":
                    raise ValueError("Unexpected test media path")
                return {"status": "unsupported", "items": []}

        class NoSummary:
            @staticmethod
            def summarize(
                metadata: dict[str, object],
                evidence: list[dict[str, object]],
            ) -> None:
                if "title" not in metadata or evidence:
                    raise ValueError("Unexpected summary test input")
                return None

        class NoEmbeddings:
            available = False

        service = IndexingService(
            metadata_service=FakeMetadataService(),
            transcript_service=UnsupportedTranscriber(),
            ocr_service=UnsupportedOCR(),
            visual_service=UnsupportedVision(),
            summary_service=NoSummary(),
            embedding_service=NoEmbeddings(),
        )
        with patch.object(
            IndexingService, "_resolve_media_path", return_value=Path("local.mp4")
        ):
            indexed_video = service.process(self.session, video.id)

        preserved_content = (
            self.session.query(VideoContent)
            .filter_by(id="previous-transcript")
            .one()
        )
        preserved_vector = (
            self.session.query(Embedding)
            .filter_by(id="previous-vector")
            .one_or_none()
        )
        self.assertEqual(preserved_content.processing_status, "completed")
        self.assertIsNotNone(preserved_vector)
        self.assertEqual(indexed_video.stage_statuses["indexing"], "completed")


class ProvenanceAndEvidenceTests(unittest.TestCase):
    def test_url_is_canonicalized_without_tracking_parameters(self) -> None:
        canonical, platform, external_id = normalize_video_url(
            "https://youtube.com/shorts/AbCdEf12345?si=tracking"
        )

        self.assertEqual(canonical, "https://www.youtube.com/watch?v=AbCdEf12345")
        self.assertEqual(platform, "youtube")
        self.assertEqual(external_id, "AbCdEf12345")

    def test_match_explanation_cites_source_and_timestamp(self) -> None:
        reason = explain_match(
            Evidence(
                "Reverse the linked list by changing the next pointer.",
                "audio",
                "original_transcript",
                12.5,
            ),
        )

        self.assertIn("transcript", reason)
        self.assertIn("12.5s", reason)
        self.assertIn("linked list", reason)

    def test_password_hashing_and_token_verification(self) -> None:
        original_secret = security.settings.jwt_secret
        security.settings.jwt_secret = "test-signing-secret-" * 3
        try:
            encoded = security.hash_password("a-long-test-password")
            token = security.create_access_token("test-user")

            self.assertTrue(security.verify_password("a-long-test-password", encoded))
            self.assertFalse(security.verify_password("wrong-password", encoded))
            self.assertEqual(security.decode_access_token(token), "test-user")
        finally:
            security.settings.jwt_secret = original_secret

    def test_summary_prompt_filters_annotations_and_invalid_evidence(self) -> None:
        prompt = SummaryService.build_prompt(
            {
                "title": "Platform title",
                "source_caption": "Platform caption",
                "manual_category": "CATEGORYUNIQUELABEL",
                "curation_notes": "CURATION_ONLY_SENTINEL",
            },
            [
                {
                    "id": "transcript-1",
                    "source_field": "original_transcript",
                    "text": "The speaker explains linked lists.",
                },
                {
                    "id": "annotation-1",
                    "source_field": "curation_notes",
                    "text": "CURATION_ONLY_SENTINEL",
                },
            ],
        )

        self.assertIn("Platform title", prompt)
        self.assertIn("The speaker explains", prompt)
        self.assertNotIn("CATEGORYUNIQUELABEL", prompt)
        self.assertNotIn("CURATION_ONLY_SENTINEL", prompt)

    def test_summary_results_require_citations_to_sent_evidence(self) -> None:
        original_model = security.settings.summary_model
        original_base = security.settings.summary_api_base
        security.settings.summary_model = "test-model"
        security.settings.summary_api_base = "https://summary.invalid/v1"
        response_body = {
            "model": "test-model",
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"summary":"Explains linked lists.",'
                            '"summary_evidence_ids":["transcript-1","annotation-1"],'
                            '"concepts":[{"text":"linked lists",'
                            '"evidence_ids":["transcript-1","annotation-1"]}]}'
                        )
                    }
                }
            ],
        }
        captured: dict[str, object] = {}

        class FakeResponse:
            @staticmethod
            def raise_for_status() -> None:
                return None

            @staticmethod
            def json() -> dict[str, object]:
                return response_body

        def fake_post(*args: object, **kwargs: object) -> FakeResponse:
            captured["args"] = args
            captured.update(kwargs)
            return FakeResponse()

        try:
            with patch("app.services.summary_service.requests.post", fake_post):
                result = SummaryService().summarize(
                    {
                        "title": "Platform title",
                        "manual_category": "CATEGORYUNIQUELABEL",
                    },
                    [
                        {
                            "id": "transcript-1",
                            "source_field": "original_transcript",
                            "text": "The speaker explains linked lists.",
                        },
                        {
                            "id": "annotation-1",
                            "source_field": "curation_notes",
                            "text": "CURATION_ONLY_SENTINEL",
                        },
                    ],
                )
        finally:
            security.settings.summary_model = original_model
            security.settings.summary_api_base = original_base

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["summary_evidence_ids"], ["transcript-1"])
        self.assertEqual(
            result["concepts"][0]["evidence_ids"],
            ["transcript-1"],
        )
        self.assertNotIn("CATEGORYUNIQUELABEL", str(captured))
        self.assertNotIn("CURATION_ONLY_SENTINEL", str(captured))


class EvaluationMetricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = Path(__file__).resolve().parents[2] / "scripts" / "evaluate_retrieval.py"
        spec = importlib.util.spec_from_file_location("evaluate_retrieval", path)
        if spec is None or spec.loader is None:
            raise RuntimeError("Unable to load retrieval evaluator")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.evaluate_case = staticmethod(module.evaluate_case)

    def test_metrics_use_ranked_ids_and_local_judgments(self) -> None:
        metrics = self.evaluate_case(
            ["relevant-1", "not-relevant", "relevant-2"],
            {"relevant-1", "relevant-2"},
        )

        self.assertEqual(metrics["recall_at_5"], 1.0)
        self.assertEqual(metrics["recall_at_10"], 1.0)
        self.assertEqual(metrics["precision_at_5"], 0.4)
        self.assertEqual(metrics["precision_at_10"], 0.2)
        self.assertEqual(metrics["mrr_at_10"], 1.0)
        self.assertGreater(metrics["ndcg_at_10"], 0)
        self.assertEqual(metrics["zero_result"], 0.0)

    def test_metrics_reject_unjudged_queries(self) -> None:
        with self.assertRaises(ValueError):
            self.evaluate_case([], set())


if __name__ == "__main__":
    unittest.main()
