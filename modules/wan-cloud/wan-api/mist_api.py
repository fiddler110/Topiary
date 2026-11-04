"""The simulated Mist REST API (/api/v1/...) that the real `Juniper/mist` Terraform provider talks to.

Generic, spec-shaped and forgiving: each org collection is a dict of JSON objects in the org store. What the provider
needs from a server (docs/SRX-MIST-PLAN.md 9.1) is implemented here, each rule marked R1..R7:
  R1 chunked request bodies (server.py)      R5 echo what was sent, in the same shape
  R2 scope ids on every answer               R6 inventory claim/assign/unassign/delete and profile assign
  R3 paging headers on every list            R7 an empty collection is [], a missing object is 404
  R4 PUT: "-name" deletes, others replace, server-owned fields are never taken from the request
Nothing slow happens under an org lock: a handler locks, reads/changes the dict, saves, unlocks.
"""
import re
import time
import uuid

import wan_ids
from store import COLLECTIONS

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
MAC_RE = re.compile(r"^[0-9a-f]{12}$")
MAX_LIMIT = 1000

# What a client may never set (R4). Devices also own their identity fields.
OWNED = {"id", "org_id", "site_id", "created_time", "modified_time"}
DEVICE_OWNED = OWNED | {"type", "mac", "serial", "model", "magic", "connected", "deviceprofile_id"}

# Label for events, required fields, and the JSON type of fields we know (anything else is passed through).
# Validation is deliberately small: required name, and the list/object/string shape of well-known fields.
_GW = {"port_config": dict, "ip_configs": dict, "service_policies": list, "dns_servers": list, "ntp_servers": list,
       "dhcpd_config": dict, "extra_routes": dict, "extra_routes6": dict, "networks": list, "path_preferences": dict,
       "bgp_config": dict, "routing_policies": dict, "vrf_config": dict, "vrf_instances": dict,
       "tunnel_configs": dict, "oob_ip_config": dict}
KINDS = {
    "networks": ("network", ("name", "subnet"),
                 {"name": str, "subnet": str, "subnet6": str, "gateway": str, "vlan_id": (str, int),
                  "tenants": dict, "internal_access": dict, "internet_access": dict, "multicast": dict}),
    "services": ("service", ("name",),
                 {"name": str, "type": str, "addresses": list, "specs": list, "apps": list, "app_categories": list,
                  "hostnames": list, "description": str}),
    "servicepolicies": ("service policy", ("name",),
                        {"name": str, "action": str, "services": list, "tenants": list, "idp": dict,
                         "antivirus": dict, "ssl_proxy": dict, "appqoe": dict, "path_preferences": str}),
    "gatewaytemplates": ("gateway template", ("name",), {"name": str, "type": str, **_GW}),
    "deviceprofiles": ("gateway profile", ("name",), {"name": str, "type": str, **_GW}),
    "sitegroups": ("site group", ("name",), {"name": str}),
    "vpns": ("vpn", ("name",), {"name": str, "type": str, "paths": dict}),
    "idpprofiles": ("idp profile", ("name",), {"name": str}),
    "avprofiles": ("av profile", ("name",), {"name": str}),
    "sites": ("site", ("name",), {"name": str, "address": str, "country_code": str, "timezone": str, "notes": str,
                                  "latlng": dict, "gatewaytemplate_id": str}),
    "device": ("device", (), {"name": str, "notes": str, "vars": dict, **_GW}),
    "setting": ("site setting", (), {"vars": dict}),
}
ENUMS = {("servicepolicies", "action"): ("allow", "deny")}


class ApiError(Exception):
    def __init__(self, status, detail, body=None):
        super().__init__(detail)
        self.status, self.detail, self.body = status, detail, body


def now():
    return int(time.time())


def bad(detail):
    return ApiError(400, detail)


def not_found(what="Not found"):
    return ApiError(404, what)


def validate(kind, fields, creating):
    """400 `{"detail": ...}` for a missing required field or a field of the wrong JSON type."""
    _label, required, types = KINDS[kind]
    if creating:
        for name in required:
            if fields.get(name) in (None, ""):
                raise bad(f"{name}: this field is required")
    for name, value in fields.items():
        want = types.get(name)
        if value is None or want is None:
            continue
        if not isinstance(value, want):
            raise bad(f"{name}: invalid type, expected {(want if isinstance(want, type) else want[0]).__name__}")
        if name in ("name",) and value == "":
            raise bad("name: must not be empty")
        allowed = ENUMS.get((kind, name))
        if allowed and value not in allowed:
            raise bad(f"{name}: must be one of {', '.join(allowed)}")


def split_body(body):
    """-> (fields to set, names to delete). A key "-name" asks to delete "name" (R4)."""
    if not isinstance(body, dict):
        raise bad("request body must be a JSON object")
    sets = {k: v for k, v in body.items() if not k.startswith("-")}
    drops = [k[1:] for k in body if k.startswith("-")]
    return sets, drops


def merge(base, body, owned=OWNED):
    """Mist PUT semantics (R4): "-name" deletes name; other keys replace; owned fields are never taken."""
    sets, drops = split_body(body)
    out = dict(base)
    for name in drops:
        if name not in owned:
            out.pop(name, None)
    for name, value in sets.items():
        if name not in owned:
            out[name] = value
    out["modified_time"] = now()
    return out


def paged(items, query, extra=None):
    """A list answer with the paging headers every list carries (R3)."""
    try:
        limit = max(1, min(MAX_LIMIT, int(query.get("limit") or MAX_LIMIT)))
        page = max(1, int(query.get("page") or 1))
    except ValueError:
        raise bad("limit and page must be numbers")
    headers = {"X-Page-Limit": str(limit), "X-Page-Page": str(page), "X-Page-Total": str(len(items))}
    headers.update(extra or {})
    return 200, items[(page - 1) * limit:page * limit], headers


def uuid_ok(value):
    return bool(UUID_RE.match(value or ""))


class MistApi:
    def __init__(self, store, auth):
        self.store, self.auth = store, auth

    # ---- access ------------------------------------------------------------------------------------------------
    def org_for(self, user, org_id):
        """The OrgStore the user may use. 403 for someone else's org, 404 for one that does not exist."""
        if not self.auth.can_access_org(user, org_id):
            raise ApiError(403, "Permission Denied")
        org = self.store.get(org_id) if uuid_ok(org_id) else None
        if org is None:
            raise not_found()
        return org

    def site_for(self, user, site_id):
        """(OrgStore, site id) for a site the user may use; another org's site looks like a missing one."""
        org_id = self.store.org_of_site(site_id) if uuid_ok(site_id) else None
        if org_id is None or not self.auth.can_access_org(user, org_id):
            raise not_found()
        return self.store.get(org_id)

    # ---- routing -----------------------------------------------------------------------------------------------
    def handle(self, user, method, path, query, read_json):
        """-> (status, body, headers). body: dict/list (JSON) or str (text/plain). `read_json()` parses the request
        body (it can raise ApiError). ApiError becomes {"detail": ...}."""
        try:
            return self.route(user, method, path, query, read_json)
        except ApiError as exc:
            return exc.status, exc.body if exc.body is not None else {"detail": exc.detail}, {}

    def route(self, user, method, path, query, read_json):
        parts = [p for p in path.split("/") if p]
        if parts[:2] != ["api", "v1"] or len(parts) < 3:
            raise not_found()
        rest = parts[2:]
        head = rest[0]
        if head == "self" and len(rest) == 1:
            return self.only(method, "GET") or self.self_info(user)
        if head == "orgs" and len(rest) >= 2:
            return self.org_route(user, method, rest[1], rest[2:], query, read_json)
        if head == "sites" and len(rest) >= 2:
            return self.site_route(user, method, rest[1], rest[2:], query, read_json)
        raise not_found()

    @staticmethod
    def only(method, *allowed):
        if method not in allowed:
            raise ApiError(405, f"{method} is not allowed")
        return None

    def self_info(self, user):
        privileges = [{"scope": "org", "org_id": o["id"], "name": o["name"], "role": "admin", "orgs": []}
                      for o in self.auth.orgs_for(user)]
        return 200, {"email": f"{user}@dojo.lab", "first_name": user, "last_name": "", "name": user,
                     "privileges": privileges, "tags": []}, {}

    def org_route(self, user, method, org_id, rest, query, read_json):
        org = self.org_for(user, org_id)
        if not rest:
            self.only(method, "GET")
            with org.lock:
                return 200, dict(org.data["org"]), {}
        head = rest[0]
        if head in COLLECTIONS:
            if len(rest) == 1:
                if method == "GET":
                    return self.list_collection(org, head, query)
                if method == "POST":
                    return self.create(org, user, head, read_json(), f"/api/v1/orgs/{org_id}/{head}")
                raise ApiError(405, f"{method} is not allowed")
            obj_id = rest[1]
            if len(rest) == 2:
                return self.item(org, user, method, head, obj_id, read_json)
            if head == "deviceprofiles" and len(rest) == 3 and rest[2] in ("assign", "unassign"):
                self.only(method, "POST")
                return self.profile_assign(org, user, obj_id, rest[2], read_json())
        if head == "inventory" and len(rest) == 1:
            if method == "GET":
                return self.list_inventory(org, query)
            if method == "POST":
                return self.claim(org, user, read_json())
            if method == "PUT":
                return self.inventory_op(org, user, read_json())
            raise ApiError(405, f"{method} is not allowed")
        if head == "dojo" and len(rest) == 2 and method == "GET":
            if rest[1] == "delivery":
                return self.delivery(org, query)
            if rest[1] == "events":
                with org.lock:
                    return paged(list(org.data["events"][-200:]), query)
        raise not_found()

    def site_route(self, user, method, site_id, rest, query, read_json):
        org = self.site_for(user, site_id)
        base = f"/api/v1/sites/{site_id}"
        if not rest:
            return self.item(org, user, method, "sites", site_id, read_json)
        if rest == ["setting"]:
            if method == "GET":
                with org.lock:
                    return 200, self.setting_view(org, site_id), {}
            self.only(method, "PUT")
            return self.put_setting(org, user, site_id, read_json(), base + "/setting")
        if rest[0] == "devices":
            if len(rest) == 1:
                self.only(method, "GET")
                with org.lock:
                    items = [self.device_view(org, e) for e in org.data["inventory"] if e.get("site_id") == site_id]
                return paged(items, query)
            dev_id = rest[1]
            if len(rest) == 2:
                if method == "GET":
                    with org.lock:
                        return 200, self.device_view(org, self.device_entry(org, site_id, dev_id)), {}
                self.only(method, "PUT")
                return self.put_device(org, user, site_id, dev_id, read_json(), f"{base}/devices/{dev_id}")
            if rest[2:] == ["ha"]:
                if method == "GET":
                    return self.get_cluster(org, site_id, dev_id)
                if method == "POST":
                    return self.create_cluster(org, user, site_id, dev_id, read_json(), f"{base}/devices/{dev_id}/ha")
                self.only(method, "DELETE")
                return self.delete_cluster(org, user, site_id, dev_id, f"{base}/devices/{dev_id}/ha")
            if rest[2:] == ["dojo", "config"]:
                self.only(method, "GET")
                return self.rendered_config(org, site_id, dev_id)
        raise not_found()

    # ---- generic org objects -----------------------------------------------------------------------------------
    def list_collection(self, org, kind, query):
        with org.lock:
            items = [dict(o) for o in org.data[kind].values()]    # creation order: dicts keep it, even through JSON
        if kind == "deviceprofiles" and query.get("type"):   # the data source lists with ?type=gateway
            items = [o for o in items if o.get("type") == query["type"]]
        return paged(items, query)

    def create(self, org, user, kind, body, path):
        sets, _drops = split_body(body)
        validate(kind, sets, creating=True)
        obj_id, t = str(uuid.uuid4()), now()
        obj = {k: v for k, v in sets.items() if k not in OWNED}
        obj.update(id=obj_id, org_id=org.data["org"]["id"], created_time=t, modified_time=t)
        if kind == "sites":
            obj.setdefault("timezone", "UTC")
        if kind == "deviceprofiles":
            obj.setdefault("type", "gateway")
        with org.lock:
            org.data[kind][obj_id] = obj
            org.event(user, f"create {KINDS[kind][0]} '{obj.get('name', '')}'", path + "/" + obj_id)
            org.save()
        if kind == "sites":
            self.store.index_site(obj_id, org.data["org"]["id"])
        return 200, dict(obj), {}

    def item(self, org, user, method, kind, obj_id, read_json):
        base = (f"/api/v1/sites/{obj_id}" if kind == "sites"
                else f"/api/v1/orgs/{org.data['org']['id']}/{kind}/{obj_id}")
        if method == "GET":
            with org.lock:
                return 200, dict(self.existing(org, kind, obj_id)), {}
        if method == "PUT":
            body = read_json()
            sets, _drops = split_body(body)
            validate(kind, sets, creating=False)
            with org.lock:
                obj = merge(self.existing(org, kind, obj_id), body)
                org.data[kind][obj_id] = obj
                org.event(user, f"update {KINDS[kind][0]} '{obj.get('name', '')}'", base)
                org.save()
                return 200, dict(obj), {}
        if method == "DELETE":
            with org.lock:
                obj = self.existing(org, kind, obj_id)
                del org.data[kind][obj_id]
                if kind == "sites":
                    self.drop_site_contents(org, obj_id)
                org.event(user, f"delete {KINDS[kind][0]} '{obj.get('name', '')}'", base)
                org.save()
            if kind == "sites":
                self.store.drop_site(obj_id)
            return 200, {}, {}
        raise ApiError(405, f"{method} is not allowed")

    @staticmethod
    def existing(org, kind, obj_id):
        obj = org.data[kind].get(obj_id)
        if obj is None:
            raise not_found()
        return obj

    @staticmethod
    def drop_site_contents(org, site_id):
        """Deleting a site takes its settings with it and sends its gateways back to the inventory, unassigned."""
        org.data["site_settings"].pop(site_id, None)
        for entry in org.data["inventory"]:
            if entry.get("site_id") == site_id:
                MistApi.unassign_entry(org, entry)

    # ---- site setting ------------------------------------------------------------------------------------------
    @staticmethod
    def setting_view(org, site_id):
        """Never 404 for a site that exists (R7); always carries its scope ids (R2). Caller holds the lock."""
        out = dict(org.data["site_settings"].get(site_id, {}))
        out.update(site_id=site_id, org_id=org.data["org"]["id"])
        return out

    def put_setting(self, org, user, site_id, body, path):
        sets, _drops = split_body(body)
        validate("setting", sets, creating=False)
        with org.lock:
            stored = merge(org.data["site_settings"].get(site_id, {}), body)
            org.data["site_settings"][site_id] = stored
            org.event(user, "update site setting", path)
            org.save()
            return 200, self.setting_view(org, site_id), {}

    # ---- devices -----------------------------------------------------------------------------------------------
    @staticmethod
    def device_entry(org, site_id, dev_id):
        for entry in org.data["inventory"]:
            if entry["id"] == dev_id and entry.get("site_id") == site_id:
                return entry
        raise not_found()

    @staticmethod
    def device_view(org, entry):
        """What GET .../devices/{id} answers: the device's own settings under the inventory identity (R2, R4)."""
        out = dict(org.data["devices"].get(entry["id"], {}))
        out.update(id=entry["id"], org_id=org.data["org"]["id"], site_id=entry.get("site_id"), mac=entry["mac"],
                   serial=entry["serial"], model=entry["model"], type=entry.get("type", "gateway"),
                   magic=entry.get("magic"), connected=False, deviceprofile_id=entry.get("deviceprofile_id"))
        out.setdefault("created_time", entry.get("created_time", 0))
        out.setdefault("modified_time", entry.get("created_time", 0))
        return out

    def put_device(self, org, user, site_id, dev_id, body, path):
        sets, _drops = split_body(body)
        validate("device", sets, creating=False)
        with org.lock:
            entry = self.device_entry(org, site_id, dev_id)
            stored = merge(org.data["devices"].get(dev_id, {}), body, DEVICE_OWNED)
            stored.setdefault("created_time", stored["modified_time"])
            org.data["devices"][dev_id] = stored
            org.event(user, f"update device '{stored.get('name', entry['serial'])}'", path)
            org.save()
            return 200, self.device_view(org, entry), {}

    def rendered_config(self, org, site_id, dev_id):
        with org.lock:
            self.device_entry(org, site_id, dev_id)
        return self.render_text(org, dev_id)

    def render_text(self, org, dev_id):
        """(status, text, headers) with the Junos `set` preview; 501 until renderer.py exists. The lock is let go
        before rendering: it works on a copy."""
        try:
            import renderer   # lazily: another part of the module, and optional for the API itself
        except ImportError:
            raise ApiError(501, "The config renderer is not installed.")
        return 200, renderer.render(org.snapshot(events=0), dev_id), {"Content-Type": "text/plain; charset=utf-8"}

    # ---- inventory ---------------------------------------------------------------------------------------------
    @staticmethod
    def inventory_view(org, entry):
        out = {"id": entry["id"], "org_id": org.data["org"]["id"], "mac": entry["mac"], "serial": entry["serial"],
               "model": entry["model"], "type": entry.get("type", "gateway"), "magic": entry.get("magic"),
               "site_id": entry.get("site_id"), "deviceprofile_id": entry.get("deviceprofile_id"),
               "connected": False, "adopted": False, "created_time": entry.get("created_time", 0),
               "modified_time": entry.get("created_time", 0)}
        name = org.data["devices"].get(entry["id"], {}).get("name")
        if name:
            out["name"] = name
        return out

    def list_inventory(self, org, query):
        with org.lock:
            items = [self.inventory_view(org, e) for e in org.data["inventory"]]
        for field in ("serial", "mac", "model", "type"):
            if query.get(field):
                items = [i for i in items if str(i.get(field)).lower() == query[field].lower()]
        if query.get("site_id"):
            items = [i for i in items if i["site_id"] == query["site_id"]]
        if query.get("unassigned") == "true":
            items = [i for i in items if not i["site_id"]]
        return paged(items, query)

    def claim(self, org, user, body):
        """POST: claim by code (R6). Unknown code -> error; already claimed -> duplicated (still 200)."""
        if not isinstance(body, list) or not all(isinstance(c, str) for c in body):
            raise bad("the request body must be a list of claim codes")
        out = {"added": [], "duplicated": [], "error": [], "reason": [], "inventory_added": [],
               "inventory_duplicated": []}
        with org.lock:
            for code in body:
                slip = next((d for d in org.data["delivery"] if d["magic"] == code), None)
                if slip is None:
                    out["error"].append(code)
                    out["reason"].append("invalid claim code")
                    continue
                brief = {"mac": slip["mac"], "magic": code, "model": slip["model"], "serial": slip["serial"],
                         "type": "gateway"}
                if any(e["serial"] == slip["serial"] for e in org.data["inventory"]):
                    out["duplicated"].append(code)
                    out["inventory_duplicated"].append(brief)
                    continue
                org.data["inventory"].append({
                    "id": wan_ids.device_id(slip["mac"]), "serial": slip["serial"], "mac": slip["mac"],
                    "model": slip["model"], "type": "gateway", "site_id": None, "deviceprofile_id": None,
                    "magic": code, "created_time": now()})
                out["added"].append(code)
                out["inventory_added"].append(brief)
                org.event(user, f"claim {slip['model']} {slip['serial']}", f"/api/v1/orgs/{org.data['org']['id']}/inventory")
            if out["added"]:
                org.save()
        return 200, out, {}

    @staticmethod
    def find_entries(org, body):
        """Inventory entries named by `macs` and/or `serials`; names we cannot find are returned apart."""
        found, missing = [], []
        for field in ("macs", "serials"):
            names = body.get(field) or []
            if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
                raise bad(f"{field}: must be a list of strings")
            for name in names:
                entry = next((e for e in org.data["inventory"] if e[field[:-1]] == name), None)
                if entry is None:
                    missing.append(name)
                elif entry not in found:
                    found.append(entry)
        return found, missing

    @staticmethod
    def unassign_entry(org, entry):
        """Back to the inventory: no site, no profile, none of the device's own settings, not in a cluster."""
        entry["site_id"] = None
        entry["deviceprofile_id"] = None
        org.data["devices"].pop(entry["id"], None)
        for cid in [c for c, v in org.data["clusters"].items() if entry["mac"] in v["nodes"]]:
            del org.data["clusters"][cid]

    def inventory_op(self, org, user, body):
        if not isinstance(body, dict):
            raise bad("request body must be a JSON object")
        op = body.get("op")
        path = f"/api/v1/orgs/{org.data['org']['id']}/inventory"
        if op not in ("assign", "unassign", "delete", "upgrade_to_mist", "downgrade_to_jsi"):
            raise bad(f"op: unsupported value {op!r}")
        with org.lock:
            entries, missing = self.find_entries(org, body)
            out = {"op": op, "success": [], "error": list(missing), "reason": ["not in the inventory"] * len(missing)}
            if op == "assign":
                site_id = body.get("site_id")
                if site_id not in org.data["sites"]:
                    raise bad("site_id: site not found")
            for entry in entries:
                label = entry["mac"] if body.get("macs") else entry["serial"]
                if op == "assign":
                    if body.get("no_reassign") and entry.get("site_id") not in (None, site_id):
                        out["error"].append(label)
                        out["reason"].append("already assigned to another site")
                        continue
                    if entry.get("site_id") != site_id:
                        self.unassign_entry(org, entry)
                        entry["site_id"] = site_id
                        org.event(user, f"assign {entry['serial']} to site", path)
                elif op == "unassign":
                    self.unassign_entry(org, entry)
                    org.event(user, f"unassign {entry['serial']}", path)
                elif op == "delete":
                    self.unassign_entry(org, entry)
                    org.data["inventory"].remove(entry)
                    org.event(user, f"unclaim {entry['serial']}", path)
                out["success"].append(label)
            org.save()
        # Unknown names fail an assign/unassign (400, with error and reason in step: the provider indexes both);
        # deleting something already gone is not worth failing a destroy for.
        failed = op in ("assign", "unassign") and out["error"] and not out["success"]
        return (400 if failed else 200), out, {}

    def delivery(self, org, query):
        """The packing slip: what was delivered, and whether it is claimed yet."""
        with org.lock:
            claimed = {e["serial"] for e in org.data["inventory"]}
            items = [dict(d, claimed=d["serial"] in claimed) for d in org.data["delivery"]]
        return paged(items, query)

    # ---- gateway profile assignment ----------------------------------------------------------------------------
    def profile_assign(self, org, user, profile_id, op, body):
        if not isinstance(body, dict):
            raise bad("request body must be a JSON object")
        with org.lock:
            profile = self.existing(org, "deviceprofiles", profile_id)
            entries, missing = self.find_entries(org, {"macs": body.get("macs") or []})
            out = {"success": [], "error": list(missing), "reason": ["not in the inventory"] * len(missing)}
            for entry in entries:
                if op == "assign":
                    entry["deviceprofile_id"] = profile_id    # R6: the assign resource refreshes from the inventory
                elif entry.get("deviceprofile_id") == profile_id:
                    entry["deviceprofile_id"] = None
                out["success"].append(entry["mac"])
            org.event(user, f"{op} profile '{profile.get('name', '')}' ({len(entries)} device(s))",
                      f"/api/v1/orgs/{org.data['org']['id']}/deviceprofiles/{profile_id}/{op}")
            org.save()
        return 200, out, {}

    # ---- gateway clusters (mist_device_gateway_cluster) ----------------------------------------------------------
    def create_cluster(self, org, user, site_id, dev_id, body, path):
        nodes = body.get("nodes") if isinstance(body, dict) else None
        macs = [n.get("mac") for n in nodes if isinstance(n, dict)] if isinstance(nodes, list) else []
        if len(macs) != 2 or not all(isinstance(m, str) and MAC_RE.match(m) for m in macs) or macs[0] == macs[1]:
            raise bad("nodes: exactly two distinct device MAC addresses are required")
        if dev_id != wan_ids.device_id(macs[0]):
            raise bad("the cluster id must be the first node's device id")
        with org.lock:
            for mac in macs:
                entry = next((e for e in org.data["inventory"] if e["mac"] == mac), None)
                if entry is None or entry.get("site_id") != site_id:
                    raise bad(f"device {mac} must be assigned to this site")
            for mac in macs:
                if any(mac in v["nodes"] for v in org.data["clusters"].values()):
                    # The provider matches this wording to tell "already formed" from a real failure.
                    raise bad(f"device {mac} and its peer already belong to a ha cluster")
            org.data["clusters"][dev_id] = {"site_id": site_id, "nodes": macs}
            org.event(user, f"form gateway cluster {macs[0]} + {macs[1]}", path)
            org.save()
        return 200, {"nodes": [{"mac": m} for m in macs]}, {}

    def get_cluster(self, org, site_id, dev_id):
        with org.lock:
            cluster = org.data["clusters"].get(dev_id)
            if cluster is None or cluster["site_id"] != site_id:
                raise not_found()
            return 200, {"nodes": [{"mac": m} for m in cluster["nodes"]]}, {}

    def delete_cluster(self, org, user, site_id, dev_id, path):
        with org.lock:
            cluster = org.data["clusters"].get(dev_id)
            if cluster is None or cluster["site_id"] != site_id:
                raise not_found()
            del org.data["clusters"][dev_id]
            org.event(user, "break gateway cluster", path)
            org.save()
        return 200, {}, {}
