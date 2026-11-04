"""Render the Junos `set` configuration a Mist-managed SRX would receive (training preview).

    render(store, device_id) -> str

`store` is the per-org JSON store (docs/SRX-MIST-PLAN.md 10.5). Nothing here is a real
Junos commit: it is a readable, deterministic approximation so students can see what
their Terraform produces. It never raises; odd input becomes a `# skipped: ...` line.

Precedence, per top-level key: gateway template < device profile < device config.
Dicts merge recursively by key (port_config, ip_configs, networks, ...); lists and
scalars are replaced by the higher layer. `{{var}}` in any string is replaced from the
site setting `vars`; an unknown variable is left in place and reported with a
`# WARNING: unknown variable` line.

Simplifications (all deliberate):
  * Only gateways: system host-name/name-server/ntp, interfaces, security zones, source
    NAT, a static default route, applications, security policies, DHCP server.
  * Port names are used as the Junos interface name (`ge-0/0/1`); ports named as a list or
    range ("ge-0/0/1-3", "a,b") are skipped. No reth/HA, LAGs, VRRP, OSPF/BGP, VPNs,
    path preferences, IDP, ssl_proxy or other Mist features.
  * WAN ports (usage wan) become unit 0 in zone `untrust`; static or dhcp only (PPPoE is
    skipped). The default route comes from the first static WAN with a `gateway`.
  * LAN ports (usage lan) carry the listed networks. A network with a vlan_id becomes a
    tagged unit numbered by the VLAN id; without one it is unit 0. Each network is one
    zone named after it (non-[A-Za-z0-9_-] characters become `_`) holding that unit.
    The unit address comes from `ip_configs[network]` (static only).
  * Source NAT: one interface-NAT rule-set per LAN zone towards `untrust`, only when the
    device has a WAN interface (real Mist NATs per service policy; this is coarser).
  * Applications come from org services used by this device's policies: `custom`
    services use `specs` (protocol, port_range; "a,b" becomes one term each, "any" or
    empty means no port). `apps` (application-identified) services get a comment and are
    left out of policies: this preview has no application identification.
  * Security policies come from `service_policies`: each entry's servicepolicy_id is
    resolved in the org (entry keys override it). `tenants` name org networks and become
    from-zones (`any` or none: every LAN zone). `services` name org services (`any` ok).
    The to-zone is the LAN zone whose subnet contains a service address, else `untrust`.
    Addresses other than 0.0.0.0/0 become global address-book entries. `allow` is
    permit, `deny` is deny. Policy order follows the list. Junos denies the rest.
  * DHCP: `dhcpd_config` (enabled; per-network entries, directly or under `config`) with
    type local becomes a `system services dhcp-local-server` group plus an address pool.
  * `additional_config_cmds` are appended verbatim, last.
"""
import ipaddress
import re

_VAR = re.compile(r"\{\{\s*([A-Za-z0-9_.\-]+)\s*\}\}")
_SAFE = re.compile(r"[^A-Za-z0-9_-]")


def _d(v):
    return v if isinstance(v, dict) else {}


def _l(v):
    return v if isinstance(v, list) else []


def _s(v):
    return v.strip() if isinstance(v, str) else (str(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else "")


def _name(v):
    return _SAFE.sub("_", _s(v)) or "unnamed"


def _merge(base, over):
    if isinstance(base, dict) and isinstance(over, dict):
        out = dict(base)
        for k, v in over.items():
            out[k] = _merge(base[k], v) if k in base else v
        return out
    return over


def _subst(obj, vars_, unknown):
    if isinstance(obj, str):
        def rep(m):
            n = m.group(1)
            if n in vars_ and isinstance(vars_[n], (str, int, float)):
                return str(vars_[n])
            if n not in unknown:
                unknown.append(n)
            return m.group(0)
        return _VAR.sub(rep, obj)
    if isinstance(obj, dict):
        return {k: _subst(obj[k], vars_, unknown) for k in sorted(obj, key=str)}
    if isinstance(obj, list):
        return [_subst(x, vars_, unknown) for x in obj]
    return obj


def _prefix(ip, mask):
    """Return 'a.b.c.d/len' from ip plus '/29', '29' or '255.255.255.248'; None if unusable."""
    ip, mask = _s(ip), _s(mask)
    if not ip:
        return None
    try:
        if "/" in ip:
            return str(ipaddress.ip_interface(ip))
        m = mask.lstrip("/")
        if m.isdigit():
            return str(ipaddress.ip_interface(f"{ip}/{int(m)}"))
        return str(ipaddress.ip_interface(f"{ip}/{m}"))
    except ValueError:
        return None


def _net(cidr):
    try:
        return ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        return None


def _find_device(store, device_id):
    for item in _l(_d(store).get("inventory")):
        if isinstance(item, dict) and item.get("id") == device_id:
            return item
    return None


def _first_dev_key(store, device_id):
    return _d(_d(store).get("devices")).get(device_id)


def render(store, device_id):
    try:
        return _render(store if isinstance(store, dict) else {}, device_id)
    except Exception as exc:   # never raise: this is a preview
        return f"# Rendered by Dojo WAN (preview, not a real device)\n# skipped: renderer error ({type(exc).__name__})\n"


def _render(store, device_id):
    inv = _find_device(store, device_id)
    devcfg = _d(_first_dev_key(store, device_id))
    site_id = (inv or {}).get("site_id") or devcfg.get("site_id")
    site = _d(_d(store.get("sites")).get(site_id)) if site_id else {}
    tmpl_id = site.get("gatewaytemplate_id")
    tmpl = _d(_d(store.get("gatewaytemplates")).get(tmpl_id)) if tmpl_id else {}
    prof_id = (inv or {}).get("deviceprofile_id") or devcfg.get("deviceprofile_id")
    prof = _d(_d(store.get("deviceprofiles")).get(prof_id)) if prof_id else {}
    vars_ = _d(_d(_d(store.get("site_settings")).get(site_id)).get("vars")) if site_id else {}

    cfg = {}
    for layer in (tmpl, prof, devcfg):
        cfg = _merge(cfg, layer)
    unknown = []
    cfg = _subst(cfg, vars_, unknown)
    org_networks = {}
    for nid, n in sorted(_d(store.get("networks")).items(), key=lambda kv: str(kv[0])):
        n = _subst(_d(n), vars_, unknown)
        if _s(n.get("name")):
            org_networks[_s(n["name"])] = n
    services = {_s(_d(s).get("name")): _subst(_d(s), vars_, unknown)
                for s in _d(store.get("services")).values() if _s(_d(s).get("name"))}
    org_policies = _d(store.get("servicepolicies"))

    out = []
    A = out.append
    A("# Rendered by Dojo WAN (preview, not a real device)")
    A(f"# device: {_s(cfg.get('name')) or device_id} ({device_id})")
    A(f"# site: {_s(site.get('name')) or site_id or '(none)'}")
    A(f"# template: {_s(tmpl.get('name')) or '(none)'}")
    A(f"# profile: {_s(prof.get('name')) or '(none)'}")
    if inv is None and not devcfg:
        A("# skipped: device not found in this org")
    warn_at = len(out)

    # ---- system
    A("")
    A("# system")
    host = _s(cfg.get("name")) or (_s((inv or {}).get("serial")) or "srx")
    A(f"set system host-name {_name(host)}")
    for s in _l(cfg.get("dns_servers")):
        if _s(s):
            A(f"set system name-server {_s(s)}")
    for s in _l(cfg.get("ntp_servers")):
        if _s(s):
            A(f"set system ntp server {_s(s)}")

    # ---- interfaces / zones
    wan_units, lan_zones, ifl = [], {}, []   # ifl: interface lines
    default_gw = None
    zone_host = {}
    for port in sorted(_d(cfg.get("port_config")), key=str):
        pc = _d(cfg["port_config"][port])
        pname = _s(port)
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*-?\d+(/\d+)*(/\d+)?", pname):
            ifl.append(f"# skipped: port {pname!r} (lists, ranges and unusual names are not rendered)")
            continue
        if pc.get("disabled") is True:
            ifl.append(f"# skipped: port {pname} is disabled")
            continue
        usage = _s(pc.get("usage"))
        if usage == "wan":
            ic = _d(pc.get("ip_config"))
            typ = _s(ic.get("type")) or "dhcp"
            if _s(pc.get("name")):
                ifl.append(f"set interfaces {pname} description \"{_name(pc['name'])}\"")
            if typ == "static":
                a = _prefix(ic.get("ip"), ic.get("netmask"))
                if not a:
                    ifl.append(f"# skipped: {pname} static address is missing or invalid")
                    continue
                ifl.append(f"set interfaces {pname} unit 0 family inet address {a}")
                if default_gw is None and _s(ic.get("gateway")):
                    default_gw = _s(ic["gateway"])
            elif typ == "dhcp":
                ifl.append(f"set interfaces {pname} unit 0 family inet dhcp")
                zone_host.setdefault("untrust", set()).add("dhcp")
            else:
                ifl.append(f"# skipped: {pname} wan type {typ!r} is not rendered")
                continue
            wan_units.append(f"{pname}.0")
        elif usage == "lan":
            nets = [_s(n) for n in _l(pc.get("networks")) if _s(n)]
            if not nets:
                ifl.append(f"# skipped: lan port {pname} has no networks")
            used = set()
            for n in nets:
                onet = org_networks.get(n)
                if onet is None:
                    ifl.append(f"# skipped: network {n!r} on {pname} is not an org network")
                    continue
                vid = onet.get("vlan_id")
                vid = int(vid) if _s(vid).isdigit() else 0
                if vid in used:
                    ifl.append(f"# skipped: network {n!r} on {pname} would reuse unit {vid}")
                    continue
                used.add(vid)
                if vid:
                    ifl.append(f"set interfaces {pname} vlan-tagging")
                    ifl.append(f"set interfaces {pname} unit {vid} vlan-id {vid}")
                ic = _d(_d(cfg.get("ip_configs")).get(n))
                a = _prefix(ic.get("ip"), ic.get("netmask")) if _s(ic.get("type") or "static") == "static" else None
                if a:
                    ifl.append(f"set interfaces {pname} unit {vid} family inet address {a}")
                else:
                    ifl.append(f"# note: network {n!r} has no static address on this device")
                z = _name(n)
                if z == "untrust":
                    z = "lan-untrust"
                lan_zones.setdefault(n, {"zone": z, "units": [], "net": org_networks[n]})["units"].append(f"{pname}.{vid}")
        else:
            ifl.append(f"# skipped: port {pname} usage {usage!r} is not rendered")
    A("")
    A("# interfaces")
    out.extend(sorted(set(ifl), key=lambda x: ifl.index(x)) if ifl else ["# (none)"])

    A("")
    A("# security zones")
    if wan_units:
        for u in wan_units:
            A(f"set security zones security-zone untrust interfaces {u}")
        for svc in sorted(zone_host.get("untrust", ())):
            A(f"set security zones security-zone untrust interfaces {wan_units[0]} host-inbound-traffic system-services {svc}")
    for n in sorted(lan_zones):
        z = lan_zones[n]
        for u in z["units"]:
            A(f"set security zones security-zone {z['zone']} interfaces {u}")
            for svc in ("ping", "dhcp", "dns"):
                A(f"set security zones security-zone {z['zone']} interfaces {u} host-inbound-traffic system-services {svc}")
    if not wan_units and not lan_zones:
        A("# (none)")

    # ---- routing
    A("")
    A("# routing")
    if default_gw:
        A(f"set routing-options static route 0.0.0.0/0 next-hop {default_gw}")
    else:
        A("# (no static default route)")

    # ---- NAT
    A("")
    A("# source NAT")
    if wan_units and lan_zones:
        for n in sorted(lan_zones):
            z = lan_zones[n]["zone"]
            rs = f"snat-{z}"
            A(f"set security nat source rule-set {rs} from zone {z}")
            A(f"set security nat source rule-set {rs} to zone untrust")
            A(f"set security nat source rule-set {rs} rule all match source-address 0.0.0.0/0")
            A(f"set security nat source rule-set {rs} rule all then source-nat interface")
    else:
        A("# (none: needs a wan interface and a lan network)")

    # ---- policies and applications
    app_lines, addr_lines, pol_lines, notes = [], [], [], []
    used_apps, used_addrs = [], set()
    for ent in _l(cfg.get("service_policies")):
        ent = _d(ent)
        base = _d(org_policies.get(ent.get("servicepolicy_id")))
        if not base and not ent.get("services"):
            pol_lines.append(f"# skipped: service policy {ent.get('servicepolicy_id')!r} not found in this org")
            continue
        pol = _subst(_merge(base, ent), vars_, unknown)
        pname = _name(pol.get("name") or ent.get("servicepolicy_id"))
        action = {"allow": "permit", "deny": "deny"}.get(_s(pol.get("action")) or "allow")
        if not action:
            pol_lines.append(f"# skipped: policy {pname} action {pol.get('action')!r}")
            continue
        tenants = [_s(t) for t in _l(pol.get("tenants")) if _s(t)]
        if not tenants or "any" in tenants:
            froms = sorted(lan_zones[n]["zone"] for n in lan_zones)
        else:
            froms = []
            for t in tenants:
                if t in lan_zones:
                    froms.append(lan_zones[t]["zone"])
                else:
                    pol_lines.append(f"# skipped: policy {pname} tenant {t!r} is not a network on this device")
        svcs = [_s(x) for x in _l(pol.get("services")) if _s(x)]
        apps, dests = [], {}   # dests: to_zone -> [address-book names]
        if not svcs or "any" in svcs:
            apps = ["any"]
            dests["untrust"] = ["any"]
        for sn in ([] if apps else svcs):
            sv = services.get(sn)
            if sv is None:
                pol_lines.append(f"# skipped: policy {pname} service {sn!r} not found in this org")
                continue
            if _s(sv.get("type")) in ("apps", "app", "app_categories"):
                notes.append(f"# service {sn}: application-identified service, not rendered (no application identification in this preview)")
                continue
            an = _name(sn)
            if an not in used_apps:
                used_apps.append(an)
            apps.append(an)
            addrs = [_s(a) for a in _l(sv.get("addresses")) if _s(a)]
            if not addrs or all(a in ("0.0.0.0/0", "any") for a in addrs):
                dests.setdefault("untrust", ["any"])
                continue
            for i, a in enumerate(addrs):
                if a in ("0.0.0.0/0", "any"):
                    dests.setdefault("untrust", ["any"])
                    continue
                net = _net(a)
                if net is None:
                    pol_lines.append(f"# skipped: policy {pname} address {a!r} is not a prefix")
                    continue
                to = "untrust"
                for n in sorted(lan_zones):
                    ln = _net(_s(lan_zones[n]["net"].get("subnet")))
                    if ln is not None and ln.version == net.version and net.subnet_of(ln):
                        to = lan_zones[n]["zone"]
                        break
                ab = f"{an}-{i + 1}"
                if ab not in used_addrs:
                    used_addrs.add(ab)
                    addr_lines.append(f"set security address-book global address {ab} {net}")
                dests.setdefault(to, [])
                if dests[to] != ["any"] and ab not in dests[to]:
                    dests[to].append(ab)
        if not apps or not froms or not dests:
            pol_lines.append(f"# skipped: policy {pname} has nothing to render")
            continue
        apps = sorted(set(apps), key=apps.index)
        for to in sorted(dests):
            for fz in sorted(set(froms), key=froms.index):
                if fz == to:
                    continue
                p = f"set security policies from-zone {fz} to-zone {to} policy {pname}"
                pol_lines.append(f"{p} match source-address any")
                for d in dests[to]:
                    pol_lines.append(f"{p} match destination-address {d}")
                for a in apps:
                    pol_lines.append(f"{p} match application {a}")
                pol_lines.append(f"{p} then {action}")

    A("")
    A("# applications")
    for an in used_apps:
        sv = next((s for k, s in services.items() if _name(k) == an), {})
        terms = 0
        for spec in _l(sv.get("specs")):
            spec = _d(spec)
            proto = _s(spec.get("protocol")).lower()
            if proto not in ("tcp", "udp", "icmp", "icmp6"):
                if proto in ("any", ""):
                    terms += 1
                    app_lines.append(f"# note: {an} spec has no protocol; any protocol is not rendered")
                else:
                    app_lines.append(f"# skipped: {an} spec protocol {proto!r}")
                continue
            ports = [p.strip() for p in _s(spec.get("port_range")).split(",") if p.strip() and p.strip() != "any"]
            for p in (ports or [None]):
                if p is not None and not re.fullmatch(r"\d+(-\d+)?", p):
                    app_lines.append(f"# skipped: {an} port {p!r}")
                    continue
                terms += 1
                t = f"set applications application {an} term t{terms}"
                app_lines.append(f"{t} protocol {proto}")
                if p is not None:
                    app_lines.append(f"{t} destination-port {p}")
        if terms == 0:
            app_lines.append(f"# skipped: service {an} has no usable specs")
    out.extend(app_lines or ["# (none)"])
    out.extend(notes)
    A("")
    A("# security policies")
    out.extend(addr_lines)
    out.extend(pol_lines or ["# (none)"])

    # ---- dhcp
    dh = _d(cfg.get("dhcpd_config"))
    A("")
    A("# dhcp server")
    dl = []
    if dh and dh.get("enabled") is not False:
        entries = _d(dh.get("config")) or {k: v for k, v in dh.items() if isinstance(v, dict)}
        for n in sorted(entries, key=str):
            e = _d(entries[n])
            if _s(e.get("type") or "local") != "local" or n not in lan_zones:
                dl.append(f"# skipped: dhcp for {n!r} (not local, or not a network on this device)")
                continue
            lz = lan_zones[n]
            ic = _d(_d(cfg.get("ip_configs")).get(n))
            pfx = _prefix(ic.get("ip"), ic.get("netmask"))
            if not pfx or not _s(e.get("ip_start")) or not _s(e.get("ip_end")):
                dl.append(f"# skipped: dhcp for {n!r} needs a static address, ip_start and ip_end")
                continue
            grp, subnet = lz["zone"], str(ipaddress.ip_interface(pfx).network)
            pool = f"set access address-assignment pool {grp} family inet"
            dl.append(f"{pool} network {subnet}")
            dl.append(f"{pool} range r1 low {_s(e['ip_start'])} high {_s(e['ip_end'])}")
            gw = _s(e.get("gateway")) or str(ipaddress.ip_interface(pfx).ip)
            dl.append(f"{pool} dhcp-attributes router {gw}")
            for dns in _l(e.get("dns_servers")):
                if _s(dns):
                    dl.append(f"{pool} dhcp-attributes name-server {_s(dns)}")
            if isinstance(e.get("lease_time"), int):
                dl.append(f"{pool} dhcp-attributes maximum-lease-time {e['lease_time']}")
            for u in lz["units"]:
                dl.append(f"set system services dhcp-local-server group {grp} interface {u}")
    out.extend(dl or ["# (none)"])

    extra = [c for c in _l(cfg.get("additional_config_cmds")) if isinstance(c, str) and c.strip()]
    if extra:
        A("")
        A("# additional_config_cmds")
        out.extend(c.rstrip() for c in extra)

    if unknown:
        out[warn_at:warn_at] = [f"# WARNING: unknown variable {{{{{n}}}}}" for n in unknown]
    return "\n".join(out) + "\n"
