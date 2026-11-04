"""The per-org JSON store and the seed. Run: python3 -B -m unittest test_store"""
import json
import os
import tempfile
import threading
import unittest

import store
import wan_ids

KEY = b"k" * 64


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.s = store.Store(self.tmp)
        self.org_id = wan_ids.org_id(KEY, "student01")

    def test_seed_follows_the_contract(self):
        org = self.s.ensure_org(self.org_id, "student01", KEY)
        d = org.data
        self.assertEqual(d["org"]["name"], "Dojo Org student01")
        self.assertEqual(d["org"]["id"], self.org_id)
        self.assertEqual([x["model"] for x in d["delivery"]], ["SRX300", "SRX300", "SRX345", "SRX345"])
        self.assertEqual(d["inventory"], [])     # unclaimed devices are not in the inventory
        for name in store.COLLECTIONS + ("site_settings", "devices"):
            self.assertEqual(d[name], {})
        for slip in d["delivery"]:
            self.assertRegex(slip["magic"], r"^[0-9A-Z]{15}$")
            self.assertRegex(slip["mac"], r"^[0-9a-f]{12}$")

    def test_file_is_written_and_kept_on_restart(self):
        org = self.s.ensure_org(self.org_id, "student01", KEY)
        with org.lock:
            org.data["networks"]["x"] = {"id": "x"}
            org.save()
        path = os.path.join(self.tmp, "orgs", self.org_id + ".json")
        self.assertEqual(json.load(open(path))["networks"], {"x": {"id": "x"}})
        again = store.Store(self.tmp).ensure_org(self.org_id, "student01", KEY)   # idempotent: kept
        self.assertEqual(again.data["networks"], {"x": {"id": "x"}})
        self.assertFalse(os.path.exists(path + ".tmp"))

    def test_corrupt_file_is_set_aside_and_reseeded(self):
        os.makedirs(os.path.join(self.tmp, "orgs"), exist_ok=True)
        path = os.path.join(self.tmp, "orgs", self.org_id + ".json")
        open(path, "w").write("{not json")
        org = self.s.ensure_org(self.org_id, "student01", KEY)
        self.assertEqual(org.data["org"]["id"], self.org_id)
        self.assertTrue(os.path.exists(path + ".corrupt"))

    def test_older_file_gets_missing_keys(self):
        os.makedirs(os.path.join(self.tmp, "orgs"), exist_ok=True)
        path = os.path.join(self.tmp, "orgs", self.org_id + ".json")
        json.dump({"org": {"id": self.org_id}, "networks": {}}, open(path, "w"))
        org = self.s.ensure_org(self.org_id, "student01", KEY)
        self.assertEqual(org.data["clusters"], {})
        self.assertEqual(org.data["events"], [])

    def test_events_are_capped_and_snapshot_trims(self):
        org = self.s.ensure_org(self.org_id, "student01", KEY)
        with org.lock:
            for i in range(store.EVENTS_KEPT + 50):
                org.event("a", f"act {i}", "/p")
        self.assertEqual(len(org.data["events"]), store.EVENTS_KEPT)
        snap = org.snapshot(events=200)
        self.assertEqual(len(snap["events"]), 200)
        self.assertEqual(snap["events"][-1]["action"], f"act {store.EVENTS_KEPT + 49}")
        snap["networks"]["z"] = 1      # a copy: the store is untouched
        self.assertNotIn("z", org.data["networks"])

    def test_site_index_and_reset(self):
        org = self.s.ensure_org(self.org_id, "student01", KEY)
        with org.lock:
            org.data["sites"]["s1"] = {"id": "s1"}
        self.s.index_site("s1", self.org_id)
        self.assertEqual(self.s.org_of_site("s1"), self.org_id)
        self.s.reset(self.org_id, "student01", KEY)
        self.assertIsNone(self.s.org_of_site("s1"))
        self.assertEqual(org.data["sites"], {})

    def test_per_org_lock_serialises_writers(self):
        org = self.s.ensure_org(self.org_id, "student01", KEY)

        def work():
            for _ in range(50):
                with org.lock:
                    org.data["counter"] = org.data.get("counter", 0) + 1
                    org.save()
        threads = [threading.Thread(target=work) for _ in range(6)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(org.data["counter"], 300)
        self.assertEqual(json.load(open(org.path))["counter"], 300)


if __name__ == "__main__":
    unittest.main()
