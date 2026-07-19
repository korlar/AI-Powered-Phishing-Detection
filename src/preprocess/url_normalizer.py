from __future__ import annotations

from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit

TRACKING_PREFIXES = ("utm_",)
TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


def normalize_url(url: str) -> str:
    candidate = url.strip().lower()
    if candidate.startswith("www."):
        candidate = f"https://{candidate}"

    split = urlsplit(candidate)
    scheme = split.scheme.lower() or "https"
    netloc = split.netloc.lower()
    path = quote(unquote(split.path), safe="/:%")

    filtered_query = [
        (key, value)
        for key, value in parse_qsl(split.query, keep_blank_values=True)
        if key.lower() not in TRACKING_KEYS and not key.lower().startswith(TRACKING_PREFIXES)
    ]
    query = urlencode(filtered_query, doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))
