import pytest
from app.crawlers.extractor import ContentExtractor
from app.crawlers.robots import RobotsManager
from app.crawlers.url_utils import (
    is_internal_link,
    normalize_domain,
    normalize_url,
    validate_ip_security,
    validate_url_syntax,
)


def test_domain_normalization():
    assert normalize_domain("https://WWW.Example.com/about?x=1") == "example.com"
    assert normalize_domain("http://sub.domain.co.uk/") == "sub.domain.co.uk"
    assert normalize_domain("meetuniversity.com") == "meetuniversity.com"
    with pytest.raises(ValueError):
        normalize_domain("invalid domain without dots")


def test_url_syntax_and_protocol_validation():
    ok, _ = validate_url_syntax("https://valid-target.com/page")
    assert ok is True

    # Reject non-http
    bad_proto, err = validate_url_syntax("file:///etc/passwd")
    assert bad_proto is False
    assert "Unsupported protocol" in err

    # Reject embedded user:pass
    bad_cred, err = validate_url_syntax("https://admin:secret@target.com")
    assert bad_cred is False
    assert "credentials" in err

    # Reject non-standard ports
    bad_port, err = validate_url_syntax("https://target.com:8080")
    assert bad_port is False
    assert "Port 8080 is not permitted" in err


def test_ssrf_ip_security():
    # Loopback
    is_safe, err = validate_ip_security("127.0.0.1")
    assert is_safe is False
    assert "Loopback" in err or "forbidden" in err

    is_safe_lh, err = validate_ip_security("localhost")
    assert is_safe_lh is False

    # Private RFC1918
    is_safe_priv1, err = validate_ip_security("192.168.1.100")
    assert is_safe_priv1 is False
    assert "Private" in err

    is_safe_priv2, err = validate_ip_security("10.0.0.5")
    assert is_safe_priv2 is False

    is_safe_priv3, err = validate_ip_security("172.16.5.1")
    assert is_safe_priv3 is False

    # Cloud metadata service
    is_safe_meta, err = validate_ip_security("169.254.169.254")
    assert is_safe_meta is False
    assert "metadata" in err or "Link-local" in err or "forbidden" in err


def test_internal_link_and_external_domain_rejection():
    base = "company.com"
    # Same domain
    assert is_internal_link("https://company.com/about", base) is True
    assert is_internal_link("https://www.company.com/products", base) is True
    # Subdomain allowed
    assert is_internal_link("https://blog.company.com/news", base) is True
    # External domain rejected
    assert is_internal_link("https://evil.com/hack", base) is False
    assert is_internal_link("https://notcompany.com", base) is False
    assert is_internal_link("https://company.com.attacker.com", base) is False


def test_content_extraction_and_hashing():
    sample_html = """
    <!DOCTYPE html>
    <html>
      <head>
        <title>Signal Stack AI - Executive Platform</title>
        <link rel="canonical" href="https://example.com/platform">
      </head>
      <body>
        <nav><a href="/home">Home</a></nav>
        <main>
          <h1>Enterprise Signal Monitoring</h1>
          <p>Signal Stack AI monitors market shifts, executive hiring trends, and competitor product launches in real time.</p>
          <p>Our autonomous engine extracts key intelligence signals for executive briefings.</p>
        </main>
        <footer><p>&copy; 2026 Signal Stack</p></footer>
      </body>
    </html>
    """
    title, text, canonical, content_hash = ContentExtractor.extract(sample_html, "https://example.com/platform")
    assert title == "Signal Stack AI - Executive Platform"
    assert canonical == "https://example.com/platform"
    assert "Signal Stack AI monitors market shifts" in text
    assert len(content_hash) == 64  # SHA-256


def test_robots_txt_disallow():
    robots_mgr = RobotsManager(user_agent="SignalStackAI-Bot")
    sample_robots = (
        "User-agent: *\n"
        "Disallow: /admin/\n"
        "Disallow: /private/\n"
        "Allow: /public/\n"
        "Sitemap: https://example.com/sitemap.xml\n"
    )
    robots_mgr.parse_content(sample_robots)

    assert robots_mgr.can_fetch("https://example.com/public/about") is True
    assert robots_mgr.can_fetch("https://example.com/admin/settings") is False
    assert robots_mgr.can_fetch("https://example.com/private/vault") is False
    assert "https://example.com/sitemap.xml" in robots_mgr.sitemaps
