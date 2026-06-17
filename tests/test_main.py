"""Tests for the Web Tool Set application."""

import pytest
from fastapi.testclient import TestClient
import importlib
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app  # noqa: E402

client = TestClient(app)


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_root_returns_html(self):
        """Test that root endpoint returns HTML."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_root_contains_title(self):
        """Test that root page contains the app title."""
        response = client.get("/")
        assert "Web Tool Set" in response.text


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check(self):
        """Test health check endpoint returns healthy status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "webToolSet"


class TestRateLimiting:
    """Tests for global rate limiting."""

    def test_rate_limit_per_minute_env_override(self, monkeypatch):
        """Test rate limit config can be overridden by environment variable."""
        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "7")

        import app.config as config

        try:
            reloaded_config = importlib.reload(config)
            assert reloaded_config.RATE_LIMIT_PER_MINUTE == 7
        finally:
            monkeypatch.delenv("RATE_LIMIT_PER_MINUTE", raising=False)
            importlib.reload(config)

    def test_default_rate_limit_returns_429(self):
        """Test the default rate limit is enforced by the application."""
        rate_limit_client = TestClient(app, client=("rate-limit-test", 50000))

        try:
            for _ in range(60):
                response = rate_limit_client.get("/api/health")
                assert response.status_code == 200

            response = rate_limit_client.get("/api/health")
            assert response.status_code == 429
        finally:
            app.state.limiter.limiter.storage.reset()


class TestMyIpEndpoint:
    """Tests for the /api/myip endpoint."""

    def test_myip_returns_ip(self):
        """Test that myip endpoint returns an IP address."""
        response = client.get("/api/myip")
        assert response.status_code == 200
        data = response.json()
        assert "ip" in data
        assert data["ip"] is not None


class TestPingEndpoint:
    """Tests for the /api/ping endpoint."""

    def test_ping_localhost(self):
        """Test ping to localhost."""
        # Skip if ICMP is not allowed (e.g., in some CI environments)
        try:
            import icmplib

            icmplib.ping("127.0.0.1", count=1)
        except Exception:
            pytest.skip("ICMP not available")

        response = client.get("/api/ping/127.0.0.1")
        assert response.status_code == 200
        data = response.json()
        assert "delay" in data
        assert data["error"] is None

    def test_ping_ipv6_localhost(self):
        """Test ping to IPv6 localhost."""
        try:
            import icmplib

            icmplib.ping("::1", count=1)
        except Exception:
            pytest.skip("ICMP not available")

        response = client.get("/api/ping/::1")
        assert response.status_code == 200
        data = response.json()
        assert "delay" in data

    def test_ping_invalid_host(self):
        """Test ping to invalid host returns error."""
        response = client.get("/api/ping/invalid.host.that.does.not.exist.example")
        assert response.status_code in [400, 404, 500]
        data = response.json()
        assert data.get("error") is not None


class TestTcpPingEndpoint:
    """Tests for the /api/tcping endpoint."""

    def test_tcping_google_dns(self):
        """Test TCP ping to Google DNS (8.8.8.8:53)."""
        response = client.get("/api/tcping/8.8.8.8?port=53&timeout=3")
        # May fail due to network issues, so we just check structure
        assert response.status_code in [200, 400]
        data = response.json()
        assert "delay" in data or "error" in data

    def test_tcping_invalid_port(self):
        """Test TCP ping with invalid port."""
        response = client.get("/api/tcping/127.0.0.1?port=99999")
        assert response.status_code == 422  # Validation error


class TestNslookupEndpoint:
    """Tests for the /api/nslookup endpoint."""

    def test_nslookup_resolves_hostname(self):
        """Test nslookup resolves a well-known hostname."""
        response = client.get("/api/nslookup/dns.google")
        # May fail without network access, so accept error structure too.
        assert response.status_code in [200, 404, 500]
        data = response.json()
        assert data["name"] == "dns.google"
        if response.status_code == 200:
            assert len(data["addresses"]) > 0
        else:
            assert data["error"] is not None

    def test_nslookup_invalid_host(self):
        """Test nslookup with a non-existent host returns an error."""
        response = client.get(
            "/api/nslookup/invalid.host.that.does.not.exist.example"
        )
        assert response.status_code in [404, 500]
        data = response.json()
        assert data["error"] is not None


class TestDigEndpoint:
    """Tests for the /api/dig endpoint."""

    def test_dig_a_record(self):
        """Test dig for an A record."""
        response = client.get("/api/dig/dns.google?type=A")
        assert response.status_code in [200, 404, 500]
        data = response.json()
        assert data["name"] == "dns.google"
        assert data["record_type"] == "A"
        if response.status_code == 200:
            assert len(data["records"]) > 0

    def test_dig_default_type(self):
        """Test dig defaults to A record type."""
        response = client.get("/api/dig/dns.google")
        assert response.status_code in [200, 404, 500]
        data = response.json()
        assert data["record_type"] == "A"

    def test_dig_invalid_type(self):
        """Test dig with an unsupported record type returns validation error."""
        response = client.get("/api/dig/dns.google?type=INVALID")
        assert response.status_code == 422


class TestReverseIpEndpoint:
    """Tests for the /api/reverse-ip endpoint."""

    def test_reverse_ip_resolves(self):
        """Test reverse lookup of a well-known IP (8.8.8.8)."""
        response = client.get("/api/reverse-ip/8.8.8.8")
        # May fail without network access, so accept error structure too.
        assert response.status_code in [200, 404, 500]
        data = response.json()
        assert data["address"] == "8.8.8.8"
        if response.status_code == 200:
            assert len(data["hostnames"]) > 0
        else:
            assert data["error"] is not None

    def test_reverse_ip_invalid_address(self):
        """Test reverse lookup with an invalid IP returns a 400 error."""
        response = client.get("/api/reverse-ip/not-an-ip")
        assert response.status_code == 400
        data = response.json()
        assert data["error"] is not None

    def test_reverse_ip_no_argument(self):
        """Test reverse lookup falls back to the client IP when none is given."""
        response = client.get("/api/reverse-ip")
        # The client IP may or may not be a valid/resolvable address (the test
        # client reports a non-IP host), so just check the response structure.
        assert response.status_code in [200, 400, 404, 500]
        data = response.json()
        assert "address" in data
        assert "hostnames" in data or data["error"] is not None


class TestTracerouteEndpoint:
    """Tests for the /api/traceroute endpoint."""

    def test_traceroute_structure(self):
        """Test traceroute returns the expected structure."""
        response = client.get("/api/traceroute/127.0.0.1?max_hops=1&timeout=1")
        # Requires raw socket privileges; accept error structure too.
        assert response.status_code in [200, 404, 500]
        data = response.json()
        assert data["address"] == "127.0.0.1"
        assert "hops" in data or "error" in data

    def test_traceroute_invalid_max_hops(self):
        """Test traceroute with out-of-range max_hops returns validation error."""
        response = client.get("/api/traceroute/127.0.0.1?max_hops=999")
        assert response.status_code == 422


class TestWhoisEndpoint:
    """Tests for the /api/whois endpoint."""

    def test_whois_domain(self):
        """Test whois lookup for a well-known domain."""
        response = client.get("/api/whois/example.com")
        # Requires outbound TCP/43; accept error structure too.
        assert response.status_code in [200, 404, 500]
        data = response.json()
        assert data["query"] == "example.com"
        if response.status_code == 200:
            assert data["raw"]
            assert data["server"] is not None
        else:
            assert data["error"] is not None

    def test_whois_invalid_timeout(self):
        """Test whois with out-of-range timeout returns validation error."""
        response = client.get("/api/whois/example.com?timeout=999")
        assert response.status_code == 422


class TestWakeOnLanEndpoint:
    """Tests for the /api/wol endpoint."""

    def test_wol_valid_mac(self):
        """Test WOL with valid MAC address."""
        response = client.get("/api/wol/AA:BB:CC:DD:EE:FF")
        assert response.status_code == 200
        data = response.json()
        assert data["rst"] == "success"

    def test_wol_invalid_mac(self):
        """Test WOL with invalid MAC address."""
        response = client.get("/api/wol/invalid")
        assert response.status_code == 422  # Validation error

    def test_wol_lowercase_mac(self):
        """Test WOL with lowercase MAC address."""
        response = client.get("/api/wol/aa:bb:cc:dd:ee:ff")
        assert response.status_code == 200
        data = response.json()
        assert data["rst"] == "success"


class TestPortCheckEndpoint:
    """Tests for the /api/port endpoint."""

    def test_port_open(self):
        """Test that an actually open port is detected as open."""
        import socket
        import threading

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]

        def accept_and_close():
            try:
                conn, _ = server.accept()
                conn.close()
            except Exception:
                pass

        t = threading.Thread(target=accept_and_close, daemon=True)
        t.start()

        response = client.get(f"/api/port/127.0.0.1/{port}")
        server.close()
        t.join(timeout=2)

        assert response.status_code == 200
        data = response.json()
        assert data["open"] is True
        assert data["latency"] is not None
        assert data["address"] == "127.0.0.1"
        assert data["port"] == port

    def test_port_closed(self):
        """Test that a closed port is correctly reported."""
        response = client.get("/api/port/127.0.0.1/19998")
        data = response.json()
        assert data["open"] is False
        assert data["error"] is not None

    def test_port_invalid_range_low(self):
        """Test that port 0 is rejected with a validation error."""
        response = client.get("/api/port/127.0.0.1/0")
        assert response.status_code == 422

    def test_port_invalid_range_high(self):
        """Test that port 65536 is rejected with a validation error."""
        response = client.get("/api/port/127.0.0.1/65536")
        assert response.status_code == 422

    def test_port_invalid_host(self):
        """Test that an invalid hostname returns an error without raising."""
        response = client.get("/api/port/this.host.does.not.exist.invalid/80")
        data = response.json()
        assert data["open"] is False
        assert data["error"] is not None

    def test_port_response_structure(self):
        """Test that the response always contains required fields."""
        response = client.get("/api/port/127.0.0.1/19998")
        data = response.json()
        assert "address" in data
        assert "port" in data
        assert "open" in data


class TestLegacyEndpoints:
    """Tests for legacy API endpoints (backward compatibility)."""

    def test_legacy_ping(self):
        """Test legacy ping endpoint."""
        try:
            import icmplib

            icmplib.ping("127.0.0.1", count=1)
        except Exception:
            pytest.skip("ICMP not available")

        response = client.get("/ping/127.0.0.1")
        assert response.status_code == 200

    def test_legacy_myip(self):
        """Test legacy myip endpoint."""
        response = client.get("/myip")
        assert response.status_code == 200

    def test_legacy_wol(self):
        """Test legacy WOL endpoint."""
        response = client.get("/wol/AA:BB:CC:DD:EE:FF")
        assert response.status_code == 200


class TestStaticFiles:
    """Tests for static file serving."""

    def test_css_file(self):
        """Test that CSS file is accessible."""
        response = client.get("/static/css/style.css")
        assert response.status_code == 200
        assert "text/css" in response.headers["content-type"]

    def test_js_file(self):
        """Test that JS file is accessible."""
        response = client.get("/static/js/app.js")
        assert response.status_code == 200
        assert "javascript" in response.headers["content-type"]
