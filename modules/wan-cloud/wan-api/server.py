#!/usr/bin/env python3
"""Dojo WAN control plane ("wan-api"): a simulated Juniper Mist REST API for the real `Juniper/mist` provider.

Two listeners:
  443  (TLS, the lab's own CA)  /api/v1/...  the Mist API (token auth: `Authorization: Token <t>`)
                                /dojo-state/...  Terraform http state backend (Basic auth: user + token)
  8080 (plain, behind Caddy)    /wan/ portal, /wan/api/... JSON (X-Gateway-Token), /readyz, /_dojo/reset/<user>

Stdlib only, one file per concern, like modules/dojo-cloud/cloud-api. Contract: docs/SRX-MIST-PLAN.md section 10.
"""
import hmac
import json
import os
import re
import secrets
import signal
import ssl
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

import auth as auth_mod
import mist_api
import pki
import portal_api
import store as store_mod
import tfstate
import wan_ids

BODY_LIMIT = 4 * 1024 * 1024
CLIENT_GONE = (OSError,)   # the peer hung up or the TLS session died (ssl.SSLError is an OSError)


def log(msg):
    print(msg, flush=True)


class RateLimit:
    """A token bucket per authenticated identity: a tripwire against a runaway loop, far above what a lab does, not a
    budget (0 = off). Never keyed by source IP (all students share one address). The lock covers arithmetic only."""

    def __init__(self, burst, per_sec, clock=time.monotonic):
        self.burst, self.rate, self.clock = float(burst), float(per_sec), clock
        self.buckets = {}  # key -> (tokens, last)
        self.lock = threading.Lock()

    def take(self, key, scale=1):
        """0 if the request may go now, else seconds until one may."""
        if self.burst <= 0 or self.rate <= 0:
            return 0
        burst, rate = self.burst * scale, self.rate * scale
        with self.lock:
            now = self.clock()
            tokens, last = self.buckets.get(key, (burst, now))
            tokens = min(burst, tokens + (now - last) * rate)
            if tokens >= 1:
                self.buckets[key] = (tokens - 1, now)
                return 0
            self.buckets[key] = (tokens, now)
            return max(1, int((1 - tokens) / rate + 0.999))


def _rate(env, name, default):
    try:
        return float(env.get(name, default))
    except ValueError:
        return float(default)


def load_signing_key(secrets_dir):
    """32 random bytes, hex, 0600, written once. The terminal's root broker reads the same file."""
    os.makedirs(secrets_dir, exist_ok=True)
    path = f"{secrets_dir}/signing.key"
    if not os.path.exists(path):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(secrets.token_hex(32))
    with open(path, "rb") as f:
        return f.read().strip()


class App:
    def __init__(self, env=None):
        self.env = env if env is not None else os.environ
        e = self.env
        self.data_dir = e.get("WAN_DATA_DIR", "/data")
        self.key = load_signing_key(e.get("WAN_SECRETS_DIR", "/secrets"))
        facilitator = e.get("FACILITATOR_USERNAME", "root")
        self.auth = auth_mod.Auth(self.key, auth_mod.roster(e), facilitator)
        self.store = store_mod.Store(self.data_dir)
        for user in self.auth.users:       # idempotent: an org that already has a store keeps it
            self.store.ensure_org(self.auth.org_of[user], user, self.key)
        self.states = tfstate.StateStore(self.data_dir)
        self.mist = mist_api.MistApi(self.store, self.auth)
        self.portal = portal_api.Portal(self, e)
        self.limit = RateLimit(_rate(e, "WAN_API_RATE_BURST", 200), _rate(e, "WAN_API_RATE_PER_SEC", 20))
        self.ready = True

    def log_state_event(self, org_id, actor, action, path):
        org = self.store.get(org_id)
        if org is not None:
            with org.lock:
                org.event(actor, action, path)
                org.save()

    def reset(self, user, phase):
        """The engine's student reset: teardown puts the user's org back to the seed and forgets their Terraform
        states; provision has nothing to set up (the org is derived from the name). -> a short detail."""
        if phase == "provision":
            return "nothing to do"
        org_id = self.auth.org_of[user]
        self.store.reset(org_id, user, self.key)
        states = self.states.purge(org_id)
        return f"org reset to its delivery" + (f", {states} state(s) removed" if states else "")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    # Headers and body are separate send() calls; with keep-alive, Nagle plus delayed ACK stalls every second small
    # response by ~40 ms.
    disable_nagle_algorithm = True
    server_version = "DojoWAN/1.0"
    app = None        # set on the per-listener subclass by make_handler()
    kind = "api"      # "api" (443) or "portal" (8080)

    def log_message(self, fmt, *args):
        path = getattr(self, "path", "").split("?")[0]
        log(f"{self.client_address[0]} {getattr(self, 'command', None)} {path} -> {args[1] if len(args) > 1 else ''}")

    def handle(self):
        try:
            super().handle()
        except CLIENT_GONE:    # reset or TLS EOF between requests: nothing to answer, nothing to print
            self.close_connection = True

    def send_error(self, code, message=None, explain=None):
        self.close_connection = True
        self.request_version = "HTTP/1.1"
        self._send(code, {"detail": message or "The request could not be understood."})

    def end_headers(self):
        if self.close_connection and self.request_version != "HTTP/0.9":
            self.send_header("Connection", "close")
        super().end_headers()

    # ---- plumbing ----------------------------------------------------------------------------------------------
    def read_body(self, limit=BODY_LIMIT):
        """The request body, plain or chunked (the provider sends Transfer-Encoding: chunked, R1)."""
        if "chunked" in self.headers.get("Transfer-Encoding", "").lower():
            data = b""
            try:
                while True:
                    size = int((self.rfile.readline(1024).split(b";")[0].strip() or b"0"), 16)
                    if size == 0:
                        while self.rfile.readline(1024) not in (b"\r\n", b"\n", b""):   # trailers
                            pass
                        return data
                    data += self.rfile.read(size)
                    self.rfile.readline(1024)
                    if len(data) > limit:
                        raise mist_api.ApiError(413, "request body too large")
            except ValueError:
                raise mist_api.ApiError(400, "bad chunked body")
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
            self.close_connection = True
        if n > limit:
            self.close_connection = True   # the rest stays unread
            raise mist_api.ApiError(413, "request body too large")
        return self.rfile.read(n) if n > 0 else b""

    @staticmethod
    def parse_json(raw):
        if not raw.strip():
            return {}
        try:
            return json.loads(raw)
        except (ValueError, RecursionError):
            raise mist_api.ApiError(400, "the request body is not valid JSON")

    def _send(self, status, body=None, headers=None, ctype="application/json; charset=utf-8"):
        if isinstance(body, str):
            raw, ctype = body.encode(), "text/plain; charset=utf-8"
        elif isinstance(body, bytes):
            raw = body
        else:
            raw = b"" if body is None else json.dumps(body).encode()
        self.send_response(status)
        hdrs = {"Content-Type": ctype, **(headers or {})}
        for k, v in hdrs.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(raw)

    def handle_any(self):
        try:
            self.route()
        except CLIENT_GONE:
            self.close_connection = True
        except mist_api.ApiError as exc:
            self.close_connection = True   # a body we refused may still be unread
            self._safe_send(exc.status, {"detail": exc.detail})
        except Exception as exc:  # never leak a traceback
            log(f"internal error: {exc!r}")
            self.close_connection = True
            self._safe_send(500, {"detail": "The server hit an unexpected error."})

    def _safe_send(self, status, body):
        try:
            self._send(status, body)
        except CLIENT_GONE:
            self.close_connection = True

    do_GET = do_PUT = do_POST = do_DELETE = do_PATCH = do_HEAD = do_LOCK = do_UNLOCK = handle_any

    def route(self):
        parsed = urlparse(self.path)
        if self.kind == "api":
            return self.route_api(parsed)
        return self.route_portal(parsed)

    # ---- 443: the Mist API ---------------------------------------------------------------------------------------
    def route_api(self, parsed):
        app, path = self.app, parsed.path
        if path.startswith(tfstate.PREFIX):
            def read_body(limit):
                return self.read_body(limit)
            status, raw, headers = app.states.handle(app, app.limit, self.command, path, parsed.query,
                                                     self.headers.get("Authorization"), read_body,
                                                     app.log_state_event)
            if status in (401, 429):
                self.close_connection = True
            ctype = headers.pop("Content-Type", "application/json")
            return self._send(status, raw, headers, ctype)
        if not path.startswith("/api/v1/"):
            self.close_connection = True   # whatever body came with it stays unread
            return self._send(404, {"detail": "Not found"})
        scheme, _, token = (self.headers.get("Authorization") or "").partition(" ")
        user = app.auth.user_for_token(token.strip()) if scheme.lower() == "token" else None
        if user is None:
            self.close_connection = True
            return self._send(401, {"detail": "Authentication credentials were not provided."})
        wait = app.limit.take(user)
        if wait:
            self.close_connection = True
            return self._send(429, {"detail": "Too many requests: slow down and retry."}, {"Retry-After": str(wait)})
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        raw = self.read_body()   # always consumed, so a kept-alive connection never reads it as the next request

        def read_json():
            return self.parse_json(raw)
        status, body, headers = app.mist.handle(user, self.command, path, query, read_json)
        ctype = headers.pop("Content-Type", None)
        if ctype:
            return self._send(status, body, headers, ctype)
        return self._send(status, body, headers)

    # ---- 8080: portal, readiness, reset ----------------------------------------------------------------------------
    def route_portal(self, parsed):
        app, path = self.app, parsed.path
        self.read_body(64 * 1024)   # none of these takes a body, but it must not be left to be read as a request
        low = path.rstrip("/") or "/"
        if low in ("/readyz", "/healthz"):
            return self._send(200 if app.ready else 503, {"ready": app.ready}, {"Cache-Control": "no-store"})
        if low.startswith("/_dojo/reset/"):
            return self.student_reset(path, parsed.query)
        if low == "/wan" or low.startswith("/wan/"):
            status, headers, raw = app.portal.dispatch(self.command, path, self.headers)
            ctype = headers.pop("Content-Type", "application/json")
            return self._send(status, raw, headers, ctype)
        return self._send(404, {"detail": "Not found"})

    def student_reset(self, path, query):
        """POST /_dojo/reset/<user>?phase=teardown|provision from the engine's student reset, with the service's own
        X-Dojo-Reset-Token (students can reach this port, so nothing works without it)."""
        want = self.app.env.get("RESET_TOKEN", "")
        given = self.headers.get("X-Dojo-Reset-Token", "")
        if self.command != "POST" or not want or not hmac.compare_digest(given.encode(), want.encode()):
            return self._send(403, {"error": "reset token required"})
        user = unquote(path[len("/_dojo/reset/"):])
        phase = (parse_qs(query).get("phase") or [""])[0]
        if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", user) or user not in self.app.auth.org_of \
                or phase not in ("teardown", "provision"):
            return self._send(404, {"error": "not found"})
        return self._send(200, {"ok": True, "detail": self.app.reset(user, phase)})


def make_handler(app, kind):
    return type(f"{kind.title()}Handler", (Handler,), {"app": app, "kind": kind})


def serve(app, kind, port, tls=None, bind="0.0.0.0"):
    """Starts one HTTP(S) listener on a background thread and returns it (for shutdown())."""
    server = ThreadingHTTPServer((bind, port), make_handler(app, kind))
    server.daemon_threads = True
    if tls:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(*tls)
        server.socket = ctx.wrap_socket(server.socket, server_side=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    log(f"listening on :{server.server_address[1]} ({'https' if tls else 'http'}, {kind})")
    return server


def start(env=None):
    """Make the PKI and the app, start both listeners -> (app, [api server, portal server]). Used by main() and tests."""
    env = env if env is not None else os.environ
    crt, key = pki.ensure(env.get("WAN_PKI_PRIVATE_DIR", env.get("WAN_DATA_DIR", "/data") + "/pki"),
                          env.get("WAN_PKI_DIR", "/pki"))
    app = App(env)
    bind = env.get("WAN_BIND", "0.0.0.0")
    return app, [serve(app, "api", int(env.get("WAN_HTTPS_PORT", "443")), (crt, key), bind),
                 serve(app, "portal", int(env.get("WAN_HTTP_PORT", "8080")), None, bind)]


def main():
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):   # python is PID 1: without a handler SIGTERM is ignored
        signal.signal(sig, lambda _signum, _frame: stop.set())
    _app, servers = start()
    stop.wait()
    for srv in servers:
        srv.shutdown()
        srv.server_close()
    log("stopped")


if __name__ == "__main__":
    sys.exit(main())
