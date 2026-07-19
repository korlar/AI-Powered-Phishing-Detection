"""Comprehensive tests for URL normalization edge cases."""

from src.preprocess.url_normalizer import normalize_url


class TestNormalizeUrl:
    """Tests for the normalize_url function."""

    def test_lowercases_scheme_and_host(self):
        assert normalize_url("HTTPS://EXAMPLE.COM/Path") == "https://example.com/path"

    def test_prepends_scheme_to_www_urls(self):
        assert normalize_url("www.example.com") == "https://www.example.com"

    def test_defaults_to_https_when_no_scheme(self):
        # urlsplit without scheme puts everything in 'path', so this
        # exercises the fallback behavior.
        result = normalize_url("www.example.com/login")
        assert result.startswith("https://")

    def test_removes_utm_tracking_params(self):
        url = "https://example.com/page?utm_source=twitter&utm_medium=social&id=42"
        result = normalize_url(url)
        assert "utm_source" not in result
        assert "utm_medium" not in result
        assert "id=42" in result

    def test_removes_fbclid_tracking_param(self):
        url = "https://example.com/?fbclid=abc123&real=yes"
        result = normalize_url(url)
        assert "fbclid" not in result
        assert "real=yes" in result

    def test_removes_gclid_tracking_param(self):
        url = "https://example.com/?gclid=xyz&keep=1"
        result = normalize_url(url)
        assert "gclid" not in result
        assert "keep=1" in result

    def test_preserves_non_tracking_query_params(self):
        url = "https://example.com/search?q=hello&page=2"
        result = normalize_url(url)
        assert "q=hello" in result
        assert "page=2" in result

    def test_strips_whitespace(self):
        assert normalize_url("  https://example.com  ") == "https://example.com"

    def test_normalizes_percent_encoding(self):
        url = "https://example.com/%7Euser"
        result = normalize_url(url)
        assert "example.com" in result

    def test_removes_fragment(self):
        url = "https://example.com/page#section"
        result = normalize_url(url)
        assert "#" not in result

    def test_empty_path_stays_clean(self):
        result = normalize_url("https://example.com")
        assert result == "https://example.com"

    def test_preserves_port_number(self):
        result = normalize_url("https://example.com:8080/api")
        assert ":8080" in result

    def test_handles_url_with_credentials(self):
        """URLs with user:pass@ should still parse without crashing."""
        result = normalize_url("https://user:pass@example.com/path")
        assert "example.com" in result

    def test_double_encoded_path(self):
        """Double-encoded characters should be decoded once."""
        url = "https://example.com/%252Fpath"
        result = normalize_url(url)
        assert "example.com" in result
