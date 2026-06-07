#!/usr/bin/env python3
"""
Tests for post-bootstrap deployment verification (Scripts/cluster_create/verify_utils.py).

Covers the URL reachability probing and the two-phase verdict of
verify_deployment() (Flux convergence + URL reachability). All network and
kubectl I/O is mocked.
"""
import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from Scripts.cluster_create import verify_utils as vu  # noqa: E402


# ---------------------------------------------------------------------------
# _all_urls_ok
# ---------------------------------------------------------------------------

class TestAllUrlsOk:
    def test_true_when_all_reachable(self):
        assert vu._all_urls_ok([("u1", True, ""), ("u2", True, "")]) is True

    def test_false_when_any_unreachable(self):
        assert vu._all_urls_ok([("u1", True, ""), ("u2", False, "boom")]) is False

    def test_false_when_empty_or_none(self):
        assert vu._all_urls_ok([]) is False
        assert vu._all_urls_ok(None) is False


# ---------------------------------------------------------------------------
# _probe_url — any HTTP response means reachable; only conn/DNS/TLS errors fail
# ---------------------------------------------------------------------------

class TestProbeUrl:
    def test_2xx_is_reachable(self):
        resp = MagicMock()
        resp.status = 200
        cm = MagicMock()
        cm.__enter__.return_value = resp
        with patch("urllib.request.urlopen", return_value=cm):
            ok, detail = vu._probe_url("https://auth.example.org", 5)
        assert ok is True
        assert detail == "HTTP 200"

    def test_http_error_status_is_still_reachable(self):
        err = urllib.error.HTTPError("https://x", 401, "Unauthorized", hdrs=None, fp=None)
        with patch("urllib.request.urlopen", side_effect=err):
            ok, detail = vu._probe_url("https://hubble.example.org", 5)
        assert ok is True
        assert detail == "HTTP 401"

    def test_connection_error_is_unreachable(self):
        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.URLError("connection refused")):
            ok, detail = vu._probe_url("https://auth.example.org", 5)
        assert ok is False
        assert "connection refused" in detail


# ---------------------------------------------------------------------------
# _check_urls — builds one HTTPS URL per service subdomain
# ---------------------------------------------------------------------------

class TestCheckUrls:
    def test_builds_url_per_subdomain(self):
        with patch.object(vu, "_probe_url", return_value=(True, "HTTP 200")) as probe:
            rows = vu._check_urls("example.org")
        urls = [name for name, _, _ in rows]
        assert urls == [
            "https://auth.example.org",
            "https://headlamp.example.org",
            "https://hubble.example.org",
        ]
        assert all(ok for _, ok, _ in rows)
        assert probe.call_count == 3


# ---------------------------------------------------------------------------
# verify_deployment — two-phase verdict
# ---------------------------------------------------------------------------

_READY_ROWS = [("ns/x", True, "")]


def _patch_env():
    """Common patches: kubectl present, kubeconfig resolved, all Flux resources ready."""
    return [
        patch.object(vu, "_kubectl_available", return_value=True),
        patch("Scripts.cluster_create.flux_utils._require_kubeconfig"),
        patch.object(vu, "_collect", return_value=(list(_READY_ROWS), "")),
    ]


class TestVerifyDeployment:
    def test_success_when_flux_ready_and_urls_reachable(self):
        patches = _patch_env()
        for p in patches:
            p.start()
        try:
            with patch.object(vu, "_check_urls",
                              return_value=[("https://auth.example.org", True, "HTTP 200")]), \
                 patch.object(vu, "_print_admin_credentials") as creds:
                ok = vu.verify_deployment(domain="example.org", timeout=1, url_timeout=1)
        finally:
            for p in patches:
                p.stop()
        assert ok is True
        creds.assert_called_once_with("example.org")

    def test_fails_when_urls_unreachable(self):
        patches = _patch_env()
        for p in patches:
            p.start()
        try:
            with patch.object(vu, "_check_urls",
                              return_value=[("https://auth.example.org", False, "timeout")]):
                # url_timeout=0 so the URL poll exits after a single check (no sleep).
                ok = vu.verify_deployment(domain="example.org", timeout=1, url_timeout=0)
        finally:
            for p in patches:
                p.stop()
        assert ok is False

    def test_flux_only_verdict_when_no_domain(self):
        patches = _patch_env()
        for p in patches:
            p.start()
        try:
            with patch.object(vu, "_check_urls") as check:
                ok = vu.verify_deployment(domain=None, timeout=1, url_timeout=1)
        finally:
            for p in patches:
                p.stop()
        assert ok is True
        check.assert_not_called()

    def test_returns_false_when_kubectl_missing(self):
        with patch.object(vu, "_kubectl_available", return_value=False):
            ok = vu.verify_deployment(domain="example.org", timeout=1, url_timeout=1)
        assert ok is False
