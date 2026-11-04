"""Helpers for the unit tests: a real wan-api on ephemeral ports with a temp CA, and small HTTP clients."""
import base64
import http.client
import json
import shutil
import ssl
import tempfile
import unittest

import server
import wan_ids

STUDENT, OTHER, FAC = "student01", "student02", "root"


class Lab:
    """One running server for a test class: `lab = Lab(); ... lab.close()`."""

    def __init__(self, **extra_env):
        self.tmp = tempfile.mkdtemp(prefix="wan-test-")
        env = {"WAN_DATA_DIR": self.tmp + "/data", "WAN_SECRETS_DIR": self.tmp + "/secrets", "WAN_PKI_DIR": self.tmp + "/pki",
               "WAN_HTTPS_PORT": "0", "WAN_HTTP_PORT": "0", "WAN_BIND": "127.0.0.1", "STUDENT_COUNT": "2",
               "BOT_COUNT": "1", "FACILITATOR_USERNAME": FAC, "GATEWAY_TOKEN": "gw-token", "RESET_TOKEN": "reset-token"}
        env.update(extra_env)
        self.env = env
        self._log, server.log = server.log, (lambda msg: None)
        self.app, self.servers = server.start(env)
        self.api_port = self.servers[0].server_address[1]
        self.portal_port = self.servers[1].server_address[1]
        self.ctx = ssl.create_default_context(cafile=self.tmp + "/pki/ca.crt")

    def close(self):
        for srv in self.servers:
            srv.shutdown()
            srv.server_close()
        server.log = self._log
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---- identities --------------------------------------------------------------------------------------------
    def token(self, user):
        return wan_ids.api_token(self.app.key, user)

    def org(self, user):
        return wan_ids.org_id(self.app.key, user)

    def code(self, user, n):
        return wan_ids.claim_code(self.app.key, user, n)

    def reset(self, *users):
        for user in users:
            self.app.reset(user, "teardown")
            self.app.states.purge(self.org(user))

    # ---- clients -----------------------------------------------------------------------------------------------
    def call(self, user, method, path, body=None, headers=None, chunked=False, token=None):
        """HTTPS call on the Mist API port -> (status, parsed body or text, response headers)."""
        hdrs = {"Authorization": "Token " + (token if token is not None else self.token(user))} if user or token else {}
        hdrs.update(headers or {})
        conn = http.client.HTTPSConnection("localhost", self.api_port, context=self.ctx, timeout=10)
        data = None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
        if chunked and data is not None:
            conn.request(method, path, body=iter([data[:5], data[5:]]), headers=hdrs, encode_chunked=True)
        else:
            conn.request(method, path, body=data, headers=hdrs)
        r = conn.getresponse()
        raw = r.read()
        out = (r.status, _parse(raw), dict(r.getheaders()))
        conn.close()
        return out

    def state(self, method, name, user=STUDENT, body=b"", query="", password=None, username=None):
        """Terraform http-backend call -> (status, bytes, headers)."""
        conn = http.client.HTTPSConnection("localhost", self.api_port, context=self.ctx, timeout=10)
        cred = f"{username or user}:{password if password is not None else self.token(user)}"
        conn.request(method, f"/dojo-state/{name}{query}", body=body,
                     headers={"Authorization": "Basic " + base64.b64encode(cred.encode()).decode()})
        r = conn.getresponse()
        raw = r.read()
        out = (r.status, raw, dict(r.getheaders()))
        conn.close()
        return out

    def portal(self, method, path, user=None, headers=None, token="gw-token"):
        """Plain-HTTP call on the portal port -> (status, parsed body or text, response headers)."""
        hdrs = dict(headers or {})
        if user:
            hdrs.update({"X-Auth-User": user, "X-Gateway-Token": token})
        conn = http.client.HTTPConnection("127.0.0.1", self.portal_port, timeout=10)
        conn.request(method, path, headers=hdrs)
        r = conn.getresponse()
        raw = r.read()
        out = (r.status, _parse(raw), dict(r.getheaders()))
        conn.close()
        return out


def _parse(raw):
    text = raw.decode(errors="replace")
    try:
        return json.loads(text)
    except ValueError:
        return text


class LabCase(unittest.TestCase):
    """Starts one Lab for the class and puts the two students' orgs back to the seed before each test."""
    lab_env = {}

    @classmethod
    def setUpClass(cls):
        cls.lab = Lab(**cls.lab_env)

    @classmethod
    def tearDownClass(cls):
        cls.lab.close()

    def setUp(self):
        self.lab.reset(STUDENT, OTHER, FAC)
        self.org = self.lab.org(STUDENT)
        self.base = f"/api/v1/orgs/{self.org}"

    def ok(self, method, path, body=None, user=STUDENT, **kw):
        status, data, headers = self.lab.call(user, method, path, body, **kw)
        self.assertEqual(status, 200, f"{method} {path} -> {status} {data}")
        return data

    def make(self, kind, **fields):
        """Create an org object as the student -> the object."""
        return self.ok("POST", f"{self.base}/{kind}", fields)
