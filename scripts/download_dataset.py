
import argparse
import csv
from datetime import datetime, timezone
import os
import re
import shutil
import sys
from pathlib import Path

import yt_dlp

sys.stdout.reconfigure(errors="replace")
sys.stderr.reconfigure(errors="replace")

# Resolve paths relative to the repository root.
ROOT_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT_DIR / "dataset"
MANIFEST_PATH = DATASET_DIR / "manifest.csv"

# Only download media you own or have permission to download.
# Notes are retained for later OCR, transcript and search evaluation.

VIDEOS = [
    # CODING & TECH
    ("coding", "https://www.instagram.com/reel/DeRzghmosRv/?utm_source=ig_web_copy_link&vrfl=NTc4MTIwNjQ2YQ==", ""),
    ("coding", "https://www.instagram.com/reel/DeXYB_KyeFq/?utm_source=ig_web_copy_link&vrfl=NTc4MTIwNjQ2YQ==", ""),
    ("coding", "https://www.instagram.com/reel/Cx-lmEhvzMX/?utm_source=ig_web_copy_link&rpxt=MzRlODBiNWFlZA==&srtk=MzRlODBiNWFlZA==", ""),
    ("coding", "https://www.instagram.com/reel/CxHzvX8NldL/?utm_source=ig_web_copy_link&dlrf=MzRlODBiNWFlZA==&srtk=MzRlODBiNWFlZA==", ""),
    ("coding", "https://www.instagram.com/reel/CzK9qR-LWDm/?utm_source=ig_web_copy_link&vrfl=MzRlODBiNWFlZA==&srtk=MzRlODBiNWFlZA==", ""),
    ("coding", "https://youtube.com/shorts/M3cFQzFyx1E?si=6IMbuRJnVxkhp0iy", ""),
    ("coding", "https://youtube.com/shorts/9FqdCPmmr0I?si=peq-NBVupfvlp5_C", ""),
    ("coding", "https://youtube.com/shorts/XNsV9aoQMdA?si=mPV8VaEYRCDU57pf", ""),
    ("coding", "https://youtube.com/shorts/UwQb6mQFybM?si=95VVqvScqMLauEGr", ""),
    ("coding", "https://youtube.com/shorts/yytVIJ1d8zY?si=ABMDFEuq6-axFvD7", ""),

    # RECIPES & COOKING
    ("recipes", "https://youtube.com/shorts/zDH3a-1fQJo?si=oEa-VpiGiuwOtaiz", "Paneer"),
    ("recipes", "https://youtube.com/shorts/GANEfs_BXAo?si=-KKG9Tzrs5CTe9WW", "Paneer"),
    ("recipes", "https://youtube.com/shorts/4NhWuOx9mww?si=V1L6dLR8owILmyAo", "Paneer"),
    ("recipes", "https://youtube.com/shorts/CjatazWXZMM?si=64h_Zr8ILqVLpr-X", "Healthy dessert"),
    ("recipes", "https://youtube.com/shorts/ZpjkkIO5yrc?si=j80ueQ_W2i29CljV", "Healthy dessert"),
    ("recipes", "https://youtube.com/shorts/6ovWYj_Ifdg?si=XYDacDJ_T0OKnR9B", "Banana cake"),

    # FASHION & STYLING
    ("fashion", "https://youtube.com/shorts/-wQil75p6fY?si=UEoC-rlMj2FxMD_T", "Colour combination"),
    ("fashion", "https://youtube.com/shorts/hbboqvL_W9I?si=tdtIHrsxJlpdXMQQ", "Dupatta and suit colour combination"),
    ("fashion", "https://youtube.com/shorts/Gy5U4OWJERU?si=XpHE7qOy_mwK5GQl", "Saree colour combination"),
    ("fashion", "https://youtube.com/shorts/OVD94rVdouo?si=2IJ-Ebla1RFPrgm1", "Puja colour combination"),
    ("fashion", "https://youtube.com/shorts/I-Ms4UAM1kw?si=y1wtdlPk0VotpQr6", "Durga Puja look; retrieve caption"),
    ("fashion", "https://youtube.com/shorts/9kBEeXRAyzA?si=8W3nxBxJ2ejmmSnh", "Durga Puja look"),
    ("fashion", "https://youtube.com/shorts/wgDhkCRsJj8?si=7xWgGJ-63C99EaZH", "Durga Puja look"),
    ("fashion", "https://youtube.com/shorts/PstH2H29dnQ?si=2bFPh_lJmh3Knylz", "Durga Ashtami look"),
    ("fashion", "https://youtube.com/shorts/SD48K2Yz7Q0?si=HSQ-3sbLoE8KbDwj", "Ashtami look; retrieve caption"),
    ("fashion", "https://youtube.com/shorts/QnWqTpt-3F8?si=_FnflTwUhgQZIikB", "Garba look; retrieve caption"),
    ("fashion", "https://youtube.com/shorts/nGN0Gun-p6s?si=fwjLjvJ2ZuGHHbs3", "Navratri look; retrieve OCR text"),
]


COLUMNS = [
    "video_id",
    "source_url",
    "platform",
    "category",
    "title",
    "creator",
    "duration_seconds",
    "local_path",
    "notes",
    "license",
    "download_status",
    "error",
    "processed_at",
]


def find_ffmpeg():
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return Path(ffmpeg).parent

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        packages_dir = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        for package_dir in packages_dir.glob("Gyan.FFmpeg*"):
            for candidate in package_dir.glob("*/bin/ffmpeg.exe"):
                return candidate.parent

    return None


def identify_platform(url):
    if "instagram.com" in url.lower():
        return "instagram"
    if "youtube.com" in url.lower() or "youtu.be" in url.lower():
        return "youtube"
    return "unknown"


def safe_filename(value):
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    return value.strip(" .")[:100] or "video"


def load_manifest():
    if not MANIFEST_PATH.exists():
        return {}

    with MANIFEST_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        rows = csv.DictReader(file)
        return {
            row["source_url"]: row
            for row in rows
            if row.get("source_url")
        }


def save_manifest(records):
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    temp_path = MANIFEST_PATH.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(records.values())

    temp_path.replace(MANIFEST_PATH)


def main():
    parser = argparse.ArgumentParser(
        description="Download listed YouTube Shorts and Instagram Reels."
    )
    parser.add_argument(
        "--cookies-from-browser",
        metavar="BROWSER",
        help=(
            "Use a logged-in browser session for restricted Instagram posts "
            "(for example: chrome or firefox)."
        ),
    )
    parser.add_argument(
        "--url",
        dest="urls",
        action="append",
        help="Process only this URL; may be supplied more than once.",
    )
    args = parser.parse_args()
    selected_videos = VIDEOS
    if args.urls:
        requested_urls = set(args.urls)
        known_urls = {url for _, url, _ in VIDEOS}
        unknown_urls = requested_urls - known_urls
        if unknown_urls:
            parser.error(
                "URL is not in the configured VIDEOS list: "
                f"{sorted(unknown_urls)[0]}"
            )
        selected_videos = [
            item for item in VIDEOS if item[1] in requested_urls
        ]

    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    records = load_manifest()

    # Restrict downloading to the explicitly listed sources.
    opts = {
        "format": (
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]"
            "/bestvideo+bestaudio/best[acodec!=none]"
        ),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "retries": 2,
        "fragment_retries": 5,
        "extractor_retries": 3,
        "socket_timeout": 30,
        "quiet": False,
        "no_warnings": False,
        "windowsfilenames": True,
    }
    if shutil.which("node"):
        opts["js_runtimes"] = {"node": {}}
    else:
        print(
            "[WARN] Node.js was not found on PATH. YouTube extraction may fail; "
            "install Node.js and restart the terminal."
        )

    ffmpeg_dir = find_ffmpeg()
    if ffmpeg_dir:
        opts["ffmpeg_location"] = str(ffmpeg_dir)
    else:
        print(
            "[WARN] FFmpeg was not found. YouTube separate audio/video streams "
            "cannot be merged; install FFmpeg and add it to PATH."
        )

    if args.cookies_from_browser:
        opts["cookiesfrombrowser"] = (args.cookies_from_browser,)

    success = 0
    failed = 0
    skipped = 0

    for category, url, notes in selected_videos:
        platform = identify_platform(url)
        category_dir = DATASET_DIR / category
        category_dir.mkdir(parents=True, exist_ok=True)

        previous = records.get(url, {})
        existing_path = ROOT_DIR / previous.get("local_path", "")

        if (
            previous.get("download_status") == "downloaded"
            and existing_path.is_file()
        ):
            print(f"\n[SKIP] Already downloaded: {url}")
            skipped += 1
            continue

        print(f"\n[{category.upper()}] {url}")

        row = {
            "video_id": "",
            "source_url": url,
            "platform": platform,
            "category": category,
            "title": "",
            "creator": "",
            "duration_seconds": "",
            "local_path": "",
            "notes": notes,
            "license": "",
            "download_status": "pending",
            "error": "",
            "processed_at": "",
        }

        try:
            output_template = str(
                category_dir / "%(id)s_%(title).100s.%(ext)s"
            )
            download_opts = {
                **opts,
                "outtmpl": output_template,
            }
            # Extract and download in one pass so format selection uses the
            # same fresh metadata that is ultimately downloaded.
            with yt_dlp.YoutubeDL(download_opts) as ydl:
                info = ydl.extract_info(url, download=True)

            if not info:
                raise RuntimeError("No video metadata returned")

            video_id = str(info.get("id") or "")
            if not video_id:
                raise RuntimeError("The platform did not return a video ID")

            title = info.get("title") or video_id or "video"
            row.update({
                "video_id": video_id,
                "title": title,
                "creator": info.get("uploader") or "",
                "duration_seconds": info.get("duration") or "",
            })

            # Locate the downloaded media file.
            candidates = list(category_dir.glob(f"{video_id}_*"))
            candidates = [
                path for path in candidates
                if path.is_file()
                and path.suffix.lower() in {
                    ".mp4", ".webm", ".mkv", ".mov"
                }
            ]

            if not candidates:
                raise RuntimeError(
                    "Download did not produce a usable video file"
                )

            downloaded_file = max(candidates, key=lambda path: path.stat().st_mtime)

            row.update({
                "local_path": downloaded_file.relative_to(ROOT_DIR).as_posix(),
                "download_status": "downloaded",
            })
            success += 1
            print(f"[OK] Saved: {downloaded_file}")

        except Exception as exc:
            row["download_status"] = "failed"
            error = str(exc)
            if platform == "instagram" and (
                "empty media response" in error.lower()
                or "login" in error.lower()
                or "cookie" in error.lower()
            ):
                error += (
                    "\nIf this Reel is private or login-gated, use "
                    "--cookies-from-browser chrome with an authorized session."
                )
            row["error"] = error[:1000]
            failed += 1
            print(f"[FAILED] {exc}")

        row["processed_at"] = datetime.now(timezone.utc).isoformat()
        records[url] = row
        save_manifest(records)

    print("\n========== DATASET REPORT ==========")
    print(f"Successful downloads: {success}")
    print(f"Failed attempts:      {failed}")
    print(f"Already downloaded:   {skipped}")
    print(f"Manifest:             {MANIFEST_PATH}")
    print(f"Dataset directory:    {DATASET_DIR}")


if __name__ == "__main__":
    main()
