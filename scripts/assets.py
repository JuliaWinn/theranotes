"""Write browser assets with content hashes for cache-safe filenames."""

from hashlib import sha256


def write_asset(dist, name, content):
    stem, suffix = name.rsplit(".", 1)
    digest = sha256(content.encode()).hexdigest()[:12]
    path = f"/assets/{stem}.{digest}.{suffix}"
    (dist / "assets").mkdir(exist_ok=True)
    (dist / path.lstrip("/")).write_text(content)
    return path
