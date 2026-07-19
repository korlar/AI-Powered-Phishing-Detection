from __future__ import annotations

import re
from html.parser import HTMLParser

try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:  # Allows lightweight smoke tests before dependencies are installed.
    BeautifulSoup = None  # type: ignore[assignment, misc]

URL_PATTERN = re.compile(r"https?://[^\s<>\"]+|www\.[^\s<>\"]+", re.IGNORECASE)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        return " ".join(" ".join(self.parts).split())


def html_to_text(html: str) -> str:
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return " ".join(soup.get_text(" ").split())

    parser = _TextExtractor()
    parser.feed(html)
    return parser.text()


def extract_urls(text: str) -> list[str]:
    return [match.group(0).rstrip(").,;]") for match in URL_PATTERN.finditer(text or "")]


def clean_email_text(raw_text: str) -> str:
    text = html_to_text(raw_text) if "<html" in raw_text.lower() or "</" in raw_text else raw_text
    text = re.sub(r"\s+", " ", text)
    return text.strip()
