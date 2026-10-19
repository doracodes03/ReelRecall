import argparse
import csv
import logging
import uuid
from pathlib import Path

from app.core.database import SessionLocal
from app.models.user import User
from app.models.video import Video
from app.services.indexing_service import IndexingService
from app.utils.url_validation import normalize_video_url

ROOT = Path(__file__).resolve().parents[3]
logger = logging.getLogger("dataset_import")
DEFAULT_MANIFEST = ROOT / "dataset" / "manifest.csv"


def import_manifest(manifest: Path, owner_email: str, index: bool) -> tuple[int, int]:
    session = SessionLocal()
    imported = 0
    skipped = 0
    try:
        owner = session.query(User).filter_by(email=owner_email.strip().lower()).one_or_none()
        if owner is None:
            raise ValueError("No account exists for --owner-email")
        with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
            for row_number, row in enumerate(csv.DictReader(handle), start=2):
                source_url = (row.get("source_url") or "").strip()
                if not source_url:
                    logger.warning("Skipping row %s: source_url is empty", row_number)
                    skipped += 1
                    continue
                try:
                    canonical_url, platform, external_id = normalize_video_url(source_url)
                except ValueError as exc:
                    logger.warning("Skipping row %s: invalid source_url: %s", row_number, exc)
                    skipped += 1
                    continue

                exists = (
                    session.query(Video)
                    .filter_by(user_id=owner.id, canonical_url=canonical_url)
                    .first()
                )
                if exists:
                    skipped += 1
                    continue

                media_path: Path | None = None
                local_path = (row.get("local_path") or "").strip()
                if local_path:
                    candidate = (ROOT / local_path).resolve()
                    dataset_root = (ROOT / "dataset").resolve()
                    if candidate.is_relative_to(dataset_root) and candidate.is_file():
                        media_path = candidate
                    else:
                        logger.warning(
                            "Row %s references a missing or out-of-dataset media path",
                            row_number,
                        )

                duration_text = (row.get("duration_seconds") or "").strip()
                try:
                    duration = int(float(duration_text)) if duration_text else None
                except ValueError:
                    duration = None
                license_value = (row.get("license") or "").strip() or None
                manifest_status = (row.get("download_status") or "").strip()
                try:
                    manifest_source = str(manifest.resolve().relative_to(ROOT))
                except ValueError:
                    manifest_source = str(manifest.resolve())
                video = Video(
                    id=str(uuid.uuid4()),
                    user_id=owner.id,
                    title=(row.get("title") or "").strip() or "Untitled video",
                    url=canonical_url,
                    canonical_url=canonical_url,
                    source=platform,
                    creator=(row.get("creator") or "").strip() or None,
                    external_video_id=external_id,
                    duration=duration,
                    source_caption=None,
                    source_metadata={
                        "dataset_manifest": manifest_source,
                        "dataset_license": license_value,
                        "download_status": manifest_status or None,
                    },
                    metadata_status="pending",
                    permission_status="unknown",
                    local_media_path=(
                        str(media_path.relative_to(ROOT)) if media_path else None
                    ),
                    manual_category=(row.get("category") or "").strip() or None,
                    manual_category_source=(
                        "dataset_manifest" if (row.get("category") or "").strip() else None
                    ),
                    curation_notes=(row.get("notes") or "").strip() or None,
                    curation_notes_source=(
                        "dataset_manifest" if (row.get("notes") or "").strip() else None
                    ),
                    stage_statuses={"import": "completed", "indexing": "queued"},
                    status="queued",
                )
                session.add(video)
                session.commit()
                imported += 1
                if index:
                    IndexingService().process(session, video.id)
        return imported, skipped
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import dataset manifest rows into one user's private library."
    )
    parser.add_argument("--owner-email", required=True)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--index",
        action="store_true",
        help="Run the configured indexing stages after each row is imported.",
    )
    args = parser.parse_args()
    manifest = args.manifest.resolve()
    if not manifest.is_file():
        parser.error(f"Manifest does not exist: {manifest}")
    imported, skipped = import_manifest(manifest, args.owner_email, args.index)
    print(f"Imported {imported} video(s); skipped {skipped} row(s).")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
