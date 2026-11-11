"""Atlas AI — Live Search Security, SSRF, and Reliability Test Suite."""

import ipaddress
import pytest

from backend import live_search


def test_ssrf_comprehensive_ip_denylist():
    # Loopback IPv4 & IPv6
    assert live_search.is_ip_blocked(ipaddress.ip_address("127.0.0.1")) is True
    assert live_search.is_ip_blocked(ipaddress.ip_address("127.123.45.67")) is True
    assert live_search.is_ip_blocked(ipaddress.ip_address("::1")) is True

    # Cloud metadata
    assert live_search.is_ip_blocked(ipaddress.ip_address("169.254.169.254")) is True

    # Private RFC 1918
    assert live_search.is_ip_blocked(ipaddress.ip_address("10.0.0.1")) is True
    assert live_search.is_ip_blocked(ipaddress.ip_address("172.16.0.5")) is True
    assert live_search.is_ip_blocked(ipaddress.ip_address("192.168.1.1")) is True

    # Carrier-grade NAT & benchmark
    assert live_search.is_ip_blocked(ipaddress.ip_address("100.64.0.1")) is True
    assert live_search.is_ip_blocked(ipaddress.ip_address("198.18.0.1")) is True

    # IPv4-mapped IPv6 edge cases
    assert live_search.is_ip_blocked(ipaddress.ip_address("::ffff:127.0.0.1")) is True
    assert live_search.is_ip_blocked(ipaddress.ip_address("::ffff:169.254.169.254")) is True
    assert live_search.is_ip_blocked(ipaddress.ip_address("::ffff:192.168.0.1")) is True

    # Public routable IPs must NOT be blocked
    assert live_search.is_ip_blocked(ipaddress.ip_address("8.8.8.8")) is False
    assert live_search.is_ip_blocked(ipaddress.ip_address("1.1.1.1")) is False


def test_url_ssrf_validation_rejections():
    # Non-HTTP schemes
    assert live_search.is_safe_url("file:///etc/passwd") is False
    assert live_search.is_safe_url("ftp://ftp.example.com") is False
    assert live_search.is_safe_url("gopher://evil.com") is False

    # Metadata and localhost hostnames
    assert live_search.is_safe_url("http://169.254.169.254/latest/meta-data/") is False
    assert live_search.is_safe_url("http://localhost:8000") is False
    assert live_search.is_safe_url("http://127.0.0.1:8001/health") is False
    assert live_search.is_safe_url("http://metadata.google.internal/computeMetadata/v1/") is False
    assert live_search.is_safe_url("https://internal-service.corp/") is False

    # Blocked ports
    assert live_search.is_safe_url("http://example.com:22/") is False
    assert live_search.is_safe_url("http://example.com:3306/") is False
    assert live_search.is_safe_url("http://example.com:6379/") is False

    # Legitimate external web URLs
    assert live_search.is_safe_url("https://en.wikipedia.org/wiki/Artificial_intelligence") is True
    assert live_search.is_safe_url("https://arxiv.org/abs/2301.00001") is True


def test_safe_redirect_handler():
    handler = live_search.SafeRedirectHandler(max_redirects=3)
    # Target to internal metadata must raise HTTPError 403
    with pytest.raises(Exception) as excinfo:
        handler.redirect_request(
            req=None, fp=None, code=302, msg="Found", headers={},
            newurl="http://169.254.169.254/secret"
        )
    assert "SSRF guard" in str(excinfo.value) or "403" in str(excinfo.value)


def test_provider_circuit_breaker():
    tracker = live_search.ProviderHealthTracker()
    assert tracker.is_available("test_provider") is True

    # Record 3 failures
    tracker.record_failure("test_provider", "Connection timed out")
    tracker.record_failure("test_provider", "Connection timed out")
    tracker.record_failure("test_provider", "Connection timed out")

    # Should now be on cooldown
    assert tracker.is_available("test_provider") is False

    # Recording success resets cooldown
    tracker.record_success("test_provider")
    assert tracker.is_available("test_provider") is True


def test_live_search_empty_and_unavailable_handling():
    # Empty query
    res = live_search.execute_live_web_search("")
    assert res["status"] == "empty"
    assert res["results"] == []

    # Whitespace only
    res2 = live_search.execute_live_web_search("    ")
    assert res2["status"] == "empty"
    assert res2["results"] == []


def test_authority_scoring():
    gov_score = live_search.calculate_authority_score("https://isro.gov.in/chandrayaan3")
    edu_score = live_search.calculate_authority_score("https://cs.stanford.edu/people")
    wiki_score = live_search.calculate_authority_score("https://en.wikipedia.org/wiki/Python")
    blog_score = live_search.calculate_authority_score("https://myrandomtechblog123.com/post/1")

    assert gov_score >= 0.90
    assert edu_score >= 0.90
    assert wiki_score >= 0.80
    assert blog_score < 0.60
