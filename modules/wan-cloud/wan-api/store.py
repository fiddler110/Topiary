"""Per-org JSON store: one file per org in <data>/orgs/<org_id>.json, written atomically.

Each org has its own lock. A handler takes the org's lock, reads or changes `data`, calls save() and lets go; nothing
slow (network, subprocess, rendering) happens while it is held. Layout of `data`: docs/SRX-MIST-PLAN.md 10.5, plus
`idpprofiles`, `avprofiles` (same shape as the other collections) and `clusters` (HA pairs).
"""
import copy
import json
import os
import threading
import time

import wan_ids

# Org collections keyed by object id. `sites` is org-owned too, though the API reads one at /sites/{id}.
COLLECTIONS = ("networks", "services", "servicepolicies", "gatewaytemplates", "deviceprofiles", "sitegroups",
               "vpns", "idpprofiles", "avprofiles", "sites")
EVENTS_KEPT = 1000


def seed(key, user, org_id):
    """A fresh org: no objects, nothing claimed, the delivery of four gateways on the packing slip."""
    now = int(time.time())
    data = {"org": {"id": org_id, "name": f"Dojo Org {user}", "created_time": now, "modified_time": now}}
    for name in COLLECTIONS:
        data[name] = {}
    data.update(site_settings={}, delivery=wan_ids.delivery(key, user), inventory=[], devices={}, clusters={},
                events=[])
    return data


def _normalise(data):
    """Fill in keys an older file lacks, so every handler can assume they exist."""
    for name in COLLECTIONS + ("site_settings", "devices", "clusters"):
        data.setdefault(name, {})
    for name in ("inventory", "delivery", "events"):
        data.setdefault(name, [])
    return data


class OrgStore:
    def __init__(self, path, data):
        self.path = path
        self.data = _normalise(data)
        self.lock = threading.Lock()

    def save(self):
        """Write the file atomically. The caller holds self.lock."""
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.data, f)
        os.replace(tmp, self.path)

    def event(self, actor, action, path):
        """Append to the event log (the caller holds self.lock and saves)."""
        events = self.data["events"]
        events.append({"ts": int(time.time()), "actor": actor, "action": str(action)[:160], "path": str(path)[:200]})
        if len(events) > EVENTS_KEPT:
            del events[:len(events) - EVENTS_KEPT]

    def snapshot(self, events=200):
        """A deep copy of the store with only the newest EVENTS events: safe to use after the lock is let go."""
        with self.lock:
            snap = copy.deepcopy(self.data)
        snap["events"] = snap["events"][-events:] if events else []
        return snap


class Store:
    def __init__(self, data_dir):
        self.dir = os.path.join(data_dir, "orgs")
        os.makedirs(self.dir, exist_ok=True)
        self.orgs = {}
        self.sites = {}              # site id -> org id (every site of every loaded org)
        self.lock = threading.Lock()  # guards `orgs` and `sites` only

    def ensure_org(self, org_id, user, key):
        """Load the org's file, or create it from the seed. Idempotent: an existing store is kept."""
        path = os.path.join(self.dir, org_id + ".json")
        data = None
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data = json.load(f)
            except (OSError, ValueError):
                os.replace(path, path + ".corrupt")   # keep it for a look, start the org again from the seed
        org = OrgStore(path, data if isinstance(data, dict) else seed(key, user, org_id))
        with org.lock:
            org.save()
        with self.lock:
            self.orgs[org_id] = org
            for site_id in org.data["sites"]:
                self.sites[site_id] = org_id
        return org

    def get(self, org_id):
        return self.orgs.get(org_id)

    def org_of_site(self, site_id):
        with self.lock:
            return self.sites.get(site_id)

    def index_site(self, site_id, org_id):
        with self.lock:
            self.sites[site_id] = org_id

    def drop_site(self, site_id):
        with self.lock:
            self.sites.pop(site_id, None)

    def reset(self, org_id, user, key):
        """Back to the seed: every object, claim and event gone, the delivery unclaimed again."""
        org = self.orgs[org_id]
        with org.lock:
            old_sites = list(org.data["sites"])
            org.data.clear()
            org.data.update(_normalise(seed(key, user, org_id)))
            org.save()
        with self.lock:
            for site_id in old_sites:
                self.sites.pop(site_id, None)
