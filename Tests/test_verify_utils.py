#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# NOAH - Network Operations & Automation Hub
# Copyright (C) 2026 Nicolas Engel <contact@nicolasengel.fr>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Tests for post-bootstrap deployment verification (Scripts/cluster_create/verify_utils.py).

Covers the URL reachability probing and the two-phase verdict of
verify_deployment() (Flux convergence + URL reachability). All network and
kubectl I/O is mocked.
"""
import socket
import ssl
import sys
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
# _status_code — parse the HTTP status line
# ---------------------------------------------------------------------------

class TestStatusCode:
    def test_parses_status(self):
        assert vu._status_code("HTTP/1.1 200 OK") == 200
        assert vu._status_code("HTTP/2 401 Unauthorized") == 401

    def test_none_for_non_http(self):
        assert vu._status_code("") is None
        assert vu._status_code("garbage line") is None


# ---------------------------------------------------------------------------
# _probe_host — DNS-independent: connect to node-local IPs, SNI/Host = service.
# Any HTTP response means reachable; only conn/TLS errors fail.
# ---------------------------------------------------------------------------

def _mock_cm(recv_chunks=None):
    """A MagicMock usable as a context manager (returns itself), optionally
    scripting tls.recv() with a list of byte chunks."""
    m = MagicMock()
    m.__enter__.return_value = m
    m.__exit__.return_value = False
    if recv_chunks is not None:
        m.recv.side_effect = list(recv_chunks) + [b""]
    return m


class TestProbeHost:
    def test_http_status_is_reachable(self):
        raw = _mock_cm()
        tls = _mock_cm([b"HTTP/1.1 200 OK\r\nServer: nginx\r\n\r\n"])
        ctx = MagicMock()
        ctx.wrap_socket.return_value = tls
        with patch.object(vu.socket, "create_connection", return_value=raw), \
             patch.object(vu.ssl, "create_default_context", return_value=ctx):
            ok, detail = vu._probe_host("auth.example.org", ["10.0.0.5"], 5)
        assert ok is True
        assert detail == "HTTP 200 (via 10.0.0.5)"
        # SNI/Host must be the service hostname, not the connect IP.
        assert ctx.wrap_socket.call_args.kwargs["server_hostname"] == "auth.example.org"

    def test_4xx_is_still_reachable(self):
        tls = _mock_cm([b"HTTP/1.1 401 Unauthorized\r\n\r\n"])
        ctx = MagicMock()
        ctx.wrap_socket.return_value = tls
        with patch.object(vu.socket, "create_connection", return_value=_mock_cm()), \
             patch.object(vu.ssl, "create_default_context", return_value=ctx):
            ok, detail = vu._probe_host("hubble.example.org", ["10.0.0.5"], 5)
        assert ok is True
        assert detail.startswith("HTTP 401")

    def test_tries_next_candidate_on_connection_error(self):
        tls = _mock_cm([b"HTTP/1.1 200 OK\r\n\r\n"])
        ctx = MagicMock()
        ctx.wrap_socket.return_value = tls
        # First candidate refuses; second connects.
        with patch.object(vu.socket, "create_connection",
                          side_effect=[ConnectionRefusedError("refused"), _mock_cm()]), \
             patch.object(vu.ssl, "create_default_context", return_value=ctx):
            ok, detail = vu._probe_host("auth.example.org", ["10.0.0.5", "127.0.0.1"], 5)
        assert ok is True
        assert detail == "HTTP 200 (via 127.0.0.1)"

    def test_all_candidates_fail_is_unreachable(self):
        with patch.object(vu.socket, "create_connection",
                          side_effect=socket.timeout("timed out")), \
             patch.object(vu.ssl, "create_default_context", return_value=MagicMock()):
            ok, detail = vu._probe_host("auth.example.org", ["10.0.0.5", "127.0.0.1"], 5)
        assert ok is False
        assert "timed out" in detail

    def test_tls_error_is_unreachable(self):
        ctx = MagicMock()
        ctx.wrap_socket.side_effect = ssl.SSLError("certificate verify failed")
        with patch.object(vu.socket, "create_connection", return_value=_mock_cm()), \
             patch.object(vu.ssl, "create_default_context", return_value=ctx):
            ok, detail = vu._probe_host("auth.example.org", ["10.0.0.5"], 5)
        assert ok is False
        assert "certificate verify failed" in detail


# ---------------------------------------------------------------------------
# _check_urls — builds one HTTPS URL per service subdomain, probed DNS-free
# ---------------------------------------------------------------------------

class TestCheckUrls:
    def test_builds_url_per_subdomain(self):
        with patch.object(vu, "_node_internal_ips", return_value=["10.0.0.5"]), \
             patch.object(vu, "_probe_host",
                          return_value=(True, "HTTP 200 (via 10.0.0.5)")) as probe:
            rows = vu._check_urls("example.org")
        urls = [name for name, _, _ in rows]
        assert urls == [
            "https://auth.example.org",
            "https://headlamp.example.org",
            "https://hubble.example.org",
        ]
        assert all(ok for _, ok, _ in rows)
        assert probe.call_count == 3
        # Probes the bare hostname against node-local targets (InternalIP + loopback).
        first = probe.call_args_list[0]
        assert first.args[0] == "auth.example.org"
        assert first.args[1] == ["10.0.0.5", "127.0.0.1"]


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
