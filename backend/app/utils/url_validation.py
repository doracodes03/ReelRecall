import re
from urllib.parse import parse_qsl, urlsplit


_HOSTS = {
    "instagram.com": "instagram",
    "www.instagram.com": "instagram",
    "youtube.com": "youtube",
    "www.youtube.com": "youtube",
    "m.youtube.com": "youtube",
    "youtu.be": "youtube",
}
_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{6,20}$")


def normalize_video_url(value: str) -> tuple[str, str, str]:
    """Return (canonical URL, platform, external ID) for supported public URL forms."""
    parsed = urlsplit(value.strip())
    if parsed.scheme.lower() != "https":
        raise ValueError("Only HTTPS video URLs are supported")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("Credentials and non-standard ports are not allowed")

    host = (parsed.hostname or "").lower().rstrip(".")
    platform = _HOSTS.get(host)
    if platform is None:
        raise ValueError("Only YouTube and Instagram video URLs are supported")

    segments = [part for part in parsed.path.split("/") if part]
    video_id = ""
    if platform == "youtube":
        if host == "youtu.be":
            video_id = segments[0] if segments else ""
        elif segments and segments[0] == "shorts" and len(segments) == 2:
            video_id = segments[1]
        elif segments and segments[0] == "watch":
            video_id = dict(parse_qsl(parsed.query)).get("v", "")
        if not _VIDEO_ID.fullmatch(video_id):
            raise ValueError("URL must identify a YouTube video or Short")
        canonical = f"https://www.youtube.com/watch?v={video_id}"
    else:
        if len(segments) == 2 and segments[0] in {"reel", "reels", "p"}:
            video_id = segments[1]
        if not _VIDEO_ID.fullmatch(video_id):
            raise ValueError("URL must identify an Instagram Reel or post")
        canonical = f"https://www.instagram.com/reel/{video_id}/"

    return canonical, platform, video_id


def is_valid_url(value: str) -> bool:
    try:
        normalize_video_url(value)
    except (ValueError, TypeError):
        return False
    return True
