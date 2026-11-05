import unittest

import docker_api
import policy


class TemplateTests(unittest.TestCase):
    def spec(self, **over):
        args = dict(image="dojo/hello:1.0", env_pairs=[("MESSAGE", "hi")], host_port=20001,
                    cpu=0.25, memory_gb=0.125, labels={"dojo.owner": "student01"})
        args.update(over)
        return docker_api.build_create_request(**args)

    def test_hardened_defaults(self):
        hc = self.spec()["HostConfig"]
        self.assertFalse(hc["Privileged"])
        self.assertEqual(hc["CapDrop"], ["ALL"])
        self.assertIn("no-new-privileges", hc["SecurityOpt"])
        self.assertEqual(hc["Memory"], 128 * 1024 * 1024)
        for forbidden in ("Binds", "Mounts", "Devices", "NetworkMode", "PidMode", "IpcMode",
                          "UsernsMode", "CapAdd", "Links", "ExtraHosts"):
            self.assertNotIn(forbidden, hc)

    def test_containers_come_back_when_cloud_host_restarts(self):
        hc = self.spec()["HostConfig"]
        self.assertEqual(hc["RestartPolicy"], {"Name": "unless-stopped"})  # not "always", not "no"
        self.assertEqual(set(hc["RestartPolicy"]), {"Name"})  # no MaximumRetryCount and the like

    def test_only_expected_top_level_keys(self):
        self.assertEqual(set(self.spec()), {"Image", "Env", "Labels", "ExposedPorts", "HostConfig"})

    def test_caps_are_clamped(self):
        s = self.spec(cpu=64, memory_gb=512)
        self.assertEqual(s["HostConfig"]["NanoCpus"], int(policy.MAX_CPU * 1e9))
        self.assertEqual(s["HostConfig"]["Memory"], int(policy.MAX_MEMORY_GB * 1024 ** 3))

    def test_image_allow_list_enforced_even_if_policy_bypassed(self):
        with self.assertRaises(docker_api.DockerError):
            self.spec(image="alpine:latest")
        with self.assertRaises(docker_api.DockerError):
            self.spec(image="dojo/hello:1.0 --privileged")

    def test_label_cannot_unmark_managed(self):
        self.assertEqual(self.spec(labels={"dojo.managed": "false"})["Labels"]["dojo.managed"], "true")

    def test_port_is_a_number_only(self):
        self.assertEqual(self.spec(host_port="20005")["HostConfig"]["PortBindings"]["80/tcp"][0]["HostPort"], "20005")
        with self.assertRaises(ValueError):
            self.spec(host_port="1; rm -rf /")


class FakeDocker(docker_api.Executor):
    """An Executor whose Docker calls are scripted: `answers` maps (method, path prefix) to a list of results
    (a (status, body) pair, or an exception to raise), used in order. Every call is recorded."""
    def __init__(self, answers, **kw):
        super().__init__("/nonexistent", **kw)
        self.answers, self.calls = answers, []

    def _call(self, method, path, body=None, timeout=30):
        self.calls.append((method, path.split("?")[0], timeout))
        for (m, prefix), results in self.answers.items():
            if m == method and path.startswith(prefix) and results:
                r = results.pop(0) if len(results) > 1 else results[0]
                if isinstance(r, Exception):
                    raise r
                return r
        raise AssertionError(f"unexpected call {method} {path}")


class CreateTests(unittest.TestCase):
    """The 20-bot stall (2026-11-05): a create that timed out left a `Created` container behind and every retry
    met a 409 name conflict. A create must leave nothing behind when it fails, and clear a leftover when it meets one."""
    NAME = "dojo-s1-rg-app"

    def create(self, ex):
        ex.create(self.NAME, "dojo/hello:1.0", [], 20001, 0.25, 0.125, {})

    def removed(self, ex):
        return [c for c in ex.calls if c[0] == "DELETE"]

    def test_success_removes_nothing(self):
        ex = FakeDocker({("POST", "/containers/create"): [(201, b"{}")], ("POST", f"/containers/{self.NAME}/start"): [(204, b"")]})
        self.create(ex)
        self.assertEqual(self.removed(ex), [])
        self.assertTrue(all(t == docker_api.CREATE_TIMEOUT for m, _, t in ex.calls))

    def test_timeout_on_create_removes_the_half_made_container(self):
        ex = FakeDocker({("POST", "/containers/create"): [docker_api.DockerError("cloud-host unreachable: timed out")],
                         ("DELETE", "/containers/"): [(204, b"")]})
        with self.assertRaises(docker_api.DockerError):
            self.create(ex)
        self.assertEqual(len(self.removed(ex)), 1)

    def test_timeout_on_start_removes_the_container(self):
        ex = FakeDocker({("POST", "/containers/create"): [(201, b"{}")],
                         ("POST", f"/containers/{self.NAME}/start"): [docker_api.DockerError("timed out")],
                         ("DELETE", "/containers/"): [(204, b"")]})
        with self.assertRaises(docker_api.DockerError):
            self.create(ex)
        self.assertEqual(len(self.removed(ex)), 1)

    def test_name_conflict_clears_the_leftover_and_creates_again(self):
        ex = FakeDocker({("POST", "/containers/create"): [(409, b'{"message":"Conflict."}'), (201, b"{}")],
                         ("POST", f"/containers/{self.NAME}/start"): [(204, b"")],
                         ("DELETE", "/containers/"): [(204, b"")]})
        self.create(ex)
        self.assertEqual([c[0] for c in ex.calls], ["POST", "DELETE", "POST", "POST"])

    def test_unreachable_cleanup_still_reports_the_first_error(self):
        boom = docker_api.DockerError("timed out")
        ex = FakeDocker({("POST", "/containers/create"): [boom],
                         ("DELETE", "/containers/"): [docker_api.DockerError("unreachable")]})
        with self.assertRaises(docker_api.DockerError) as ctx:
            self.create(ex)
        self.assertIs(ctx.exception, boom)

    def test_only_a_few_creates_reach_dockerd_at_once(self):
        import threading
        import time
        inside, peak, lock = [0], [0], threading.Lock()

        class Slow(FakeDocker):
            def _call(self, method, path, body=None, timeout=30):
                if method == "POST" and path.startswith("/containers/create"):
                    with lock:
                        inside[0] += 1
                        peak[0] = max(peak[0], inside[0])
                    time.sleep(0.05)
                    with lock:
                        inside[0] -= 1
                return super()._call(method, path, body, timeout)

        ex = Slow({("POST", "/containers/create"): [(201, b"{}")], ("POST", "/containers/"): [(204, b"")]},
                  create_concurrency=3)
        threads = [threading.Thread(target=self.create, args=(ex,)) for _ in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(peak[0], 3)


if __name__ == "__main__":
    unittest.main()
