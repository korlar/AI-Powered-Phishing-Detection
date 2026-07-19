"""Comprehensive tests for email parsing utilities."""

from src.preprocess.email_parser import clean_email_text, extract_urls, html_to_text


class TestHtmlToText:
    """Tests for the html_to_text function."""

    def test_strips_simple_html_tags(self):
        text = html_to_text("<p>Hello <b>world</b></p>")
        assert "Hello" in text
        assert "world" in text
        assert "<" not in text

    def test_strips_script_tags_and_content(self):
        html = "<div>Safe</div><script>alert('xss')</script><p>Content</p>"
        text = html_to_text(html)
        assert "Safe" in text
        assert "Content" in text
        assert "alert" not in text
        assert "script" not in text.lower()

    def test_strips_style_tags_and_content(self):
        html = "<style>body{color:red}</style><p>Visible</p>"
        text = html_to_text(html)
        assert "Visible" in text
        assert "color" not in text

    def test_handles_nested_tags(self):
        html = "<div><span><a href='x'>Click</a></span></div>"
        text = html_to_text(html)
        assert "Click" in text

    def test_collapses_whitespace(self):
        html = "<p>Hello    \n\n   world</p>"
        text = html_to_text(html)
        # Should not have excessive whitespace
        assert "  " not in text

    def test_handles_empty_html(self):
        assert html_to_text("") == ""

    def test_handles_plain_text(self):
        text = html_to_text("Just plain text")
        assert "Just plain text" in text


class TestExtractUrls:
    """Tests for the extract_urls function."""

    def test_finds_http_url(self):
        urls = extract_urls("Visit http://example.com today")
        assert "http://example.com" in urls

    def test_finds_https_url(self):
        urls = extract_urls("Go to https://secure.example.com/login")
        assert "https://secure.example.com/login" in urls

    def test_finds_www_url(self):
        urls = extract_urls("Check www.example.com for details")
        assert "www.example.com" in urls

    def test_finds_multiple_urls(self):
        text = "Visit https://a.com and http://b.com and www.c.com"
        urls = extract_urls(text)
        assert len(urls) == 3

    def test_strips_trailing_punctuation(self):
        urls = extract_urls("Go to https://example.com.")
        assert urls[0] == "https://example.com"

    def test_strips_trailing_parenthesis(self):
        urls = extract_urls("(see https://example.com)")
        assert urls[0] == "https://example.com"

    def test_strips_trailing_semicolon(self):
        urls = extract_urls("Link: https://example.com;")
        assert urls[0] == "https://example.com"

    def test_returns_empty_for_no_urls(self):
        urls = extract_urls("This text has no links at all")
        assert urls == []

    def test_handles_none_input(self):
        urls = extract_urls(None)
        assert urls == []

    def test_handles_empty_string(self):
        urls = extract_urls("")
        assert urls == []

    def test_finds_url_with_query_params(self):
        urls = extract_urls("https://example.com/search?q=test&page=1")
        assert len(urls) == 1
        assert "q=test" in urls[0]

    def test_finds_url_with_path(self):
        urls = extract_urls("Check https://example.com/a/b/c/page.html now")
        assert "https://example.com/a/b/c/page.html" in urls


class TestCleanEmailText:
    """Tests for the clean_email_text function."""

    def test_cleans_html_email(self):
        raw = "<html><body><h1>Alert!</h1><script>x()</script><p>Your account</p></body></html>"
        result = clean_email_text(raw)
        assert "Alert!" in result
        assert "Your account" in result
        assert "<" not in result
        assert "script" not in result.lower()

    def test_preserves_plain_text(self):
        raw = "Dear user, please verify your account."
        result = clean_email_text(raw)
        assert result == raw

    def test_collapses_excessive_whitespace(self):
        raw = "Hello    \n\n   world    again"
        result = clean_email_text(raw)
        assert "  " not in result

    def test_detects_html_by_closing_tag(self):
        raw = "Hello <b>world</b>"
        result = clean_email_text(raw)
        assert "Hello" in result
        assert "world" in result

    def test_strips_leading_trailing_whitespace(self):
        raw = "   Hello world   "
        result = clean_email_text(raw)
        assert result == "Hello world"
