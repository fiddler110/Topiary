"""stack config parsing and content-addressed tags for Compose-built images."""
import unittest
from unittest import mock

from dojo import stack
from dojo.start import _content_image_tags

CONFIG = """networks:
  web_lab:
services:
  achievements:
    image: gitopsdojo/allocator:local
    mem_limit: 128m
  bootstrap:
    restart: 'no'
  cloud-host:
    mem_limit: 3g
  sensei:
    restart: unless-stopped
  web-terminal:
    mem_limit: 3G
volumes:
  data:
    name: x
"""


class MemLimits(unittest.TestCase):
    def test_parse(self):
        limits, oneshot = stack.parse_mem_limits(CONFIG)
        self.assertEqual(limits, {"achievements": 128, "bootstrap": None, "cloud-host": 3072,
                                  "sensei": None, "web-terminal": 3072})
        self.assertEqual(oneshot, ["bootstrap"])

    def test_sizes(self):
        self.assertEqual([stack._mb(v) for v in ("512m", "2g", "2048k", "1073741824", "1.5g", "big")],
                         [512, 2048, 2, 1024, 1536, None])


BUILT = {"services": {
    "sensei-a": {"build": {"context": "../modules/sensei", "args": {}},
                 "image": "gitopsdojo/sensei:git-fundamentals"},
    "sensei-b": {"build": {"context": "../modules/sensei", "args": {}},
                 "image": "gitopsdojo/sensei:tofu-basics"},
    "runner-pool": {"build": {"context": "../modules/runner-pool/pool",
                                "args": {"JOB_TOOLS": "tofu"}},
                    "image": "gitopsdojo/runner-pool:cloud-policy-as-code"},
    "runner-alias": {"image": "gitopsdojo/runner-pool:cloud-policy-as-code"},
    "external": {"image": "docker.io/library/alpine:3"},
}}


class BuildImages(unittest.TestCase):
  def test_build_specs_only_include_services_with_build_blocks(self):
    self.assertEqual(set(stack.parse_build_specs(BUILT)), {"sensei-a", "sensei-b", "runner-pool"})

  def test_service_images_include_aliases_and_compose_defaults(self):
    images = stack.parse_service_images(BUILT)
    self.assertEqual(images["runner-alias"], "gitopsdojo/runner-pool:cloud-policy-as-code")
    self.assertEqual(images["sensei-a"], "gitopsdojo/sensei:git-fundamentals")

  def test_rendered_override_is_deterministic(self):
    images = {"sensei": "gitopsdojo/sensei:local", "runner-pool": "gitopsdojo/runner-pool:cloud-policy-as-code"}
    hashes = {"sensei": "abcd", "runner-pool": "1234"}
    self.assertEqual(stack.render_image_override(images, hashes),
                     stack.render_image_override(dict(reversed(list(images.items()))), hashes))

  def test_identical_inputs_share_a_tag_and_aliases_follow_it(self):
    from dojo.runtime import Runtime
    with mock.patch("dojo.start.config_document", return_value=BUILT):
      build_tags, hashes, overrides = _content_image_tags(Runtime(), [], {})
    self.assertEqual(hashes["sensei-a"], hashes["sensei-b"])
    self.assertEqual(overrides["sensei-a"], "gitopsdojo/sensei:git-fundamentals")
    self.assertNotEqual(hashes["sensei-a"], hashes["runner-pool"])


if __name__ == "__main__":
    unittest.main()


class ModuleGenerators(unittest.TestCase):
    """modules/<m>/generate.py: its stdout becomes .generated/modules/<m>.yml, listed after the module's compose.yml."""

    def setUp(self):
        import tempfile
        from pathlib import Path
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.modules, self.engine = root / "modules", root / "engine"
        self.engine.mkdir()
        for name, gen in (("plain", None), ("gen", "import os\nprint('x: ' + os.environ['PROBE'])\n"),
                          ("bad", "import sys\nsys.stderr.write('nope')\nsys.exit(3)\n")):
            (self.modules / name).mkdir(parents=True)
            (self.modules / name / "compose.yml").write_text("services: {}\n")
            if gen:
                (self.modules / name / "generate.py").write_text(gen)
        patches = [mock.patch.object(stack.paths, "MODULES", self.modules),
                   mock.patch.object(stack.paths, "ENGINE", self.engine)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)

    def res(self, modules, **env):
        return mock.Mock(modules=modules, env={"PROBE": "1", **env})

    def test_no_generator_is_unchanged(self):
        self.assertEqual(stack.extra_files(self.res(["plain"])), ["../modules/plain/compose.yml"])

    def test_generated_file_follows_the_compose_file(self):
        files = stack.extra_files(self.res(["gen", "plain"]))
        self.assertEqual(files, ["../modules/gen/compose.yml", ".generated/modules/gen.yml",
                                 "../modules/plain/compose.yml"])
        self.assertEqual((self.engine / ".generated/modules/gen.yml").read_text(), "x: 1\n")

    def test_resolved_env_reaches_the_generator(self):
        stack.extra_files(self.res(["gen"], PROBE="42"))
        self.assertEqual((self.engine / ".generated/modules/gen.yml").read_text(), "x: 42\n")

    def test_dry_run_writes_elsewhere(self):
        files = stack.extra_files(self.res(["gen"]), dry_run=True)
        self.assertEqual(files[1], ".generated/dry-run/modules/gen.yml")
        self.assertFalse((self.engine / ".generated/modules").exists())

    def test_unchanged_output_is_not_rewritten(self):
        stack.extra_files(self.res(["gen"]))
        path = self.engine / ".generated/modules/gen.yml"
        before = path.stat().st_mtime_ns
        stack.extra_files(self.res(["gen"]))
        self.assertEqual(path.stat().st_mtime_ns, before)

    def test_failure_carries_the_generators_message(self):
        with self.assertRaisesRegex(RuntimeError, "bad/generate.py failed: nope"):
            stack.extra_files(self.res(["bad"]))
