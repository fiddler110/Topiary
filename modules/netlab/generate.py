#!/usr/bin/env python3
"""Writes the per-student netlab pods as a Compose file on stdout (run by ./dojo, engine/dojo/stack.py).

Compose cannot loop over students, so this does. Reads STUDENT_COUNT and the NETLAB_* settings from the
environment (module.env has the defaults). Stdlib only; the output is deterministic, so a restart rebuilds
the same pods, addresses and passwords.

Pod 00 is the facilitator's; pods 01..STUDENT_COUNT are the students'. Each pod has branch m (configured by
hand) and branch a (configured by playbooks), and each branch is
  switch on:  pc --acc10-- sw --acc20-- web      sw --trk-- fw   (fw routes between VLANs 10 and 20)
  switch off: pc --cl-- fw --wb-- web
Every data network is an internal /29 carved from NETLAB_DATA_NET; every node is also on netlab_mgmt (compose.yml).
"""
import base64
import hashlib
import hmac
import ipaddress
import json
import os
import sys

IMAGE = "gitopsdojo/netlab-node:${WORKSHOP_SLUG:-local}"
MGMT_CIDR = "10.80.0.0/24"          # must match compose.yml
LAB = {"pc": "10.10.10.10/24", "web": "10.10.20.10/24", "fw10": "10.10.10.1/24", "fw20": "10.10.20.1/24"}
# ping_group_range is "0 0": nodes run ping as root, and a rootless user namespace rejects gids it does not map.
# What sshd, nginx and the interface set-up need, measured in NETLAB-PLAN.md 9.1.
CAPS = ["NET_ADMIN", "SETUID", "SETGID", "SYS_CHROOT", "CHOWN", "DAC_OVERRIDE", "NET_BIND_SERVICE"]


class ConfigError(Exception):
    pass


def password(seed, pod):
    """The pod's root password. modules/netlab/terminal/ derives the same value for the student's home."""
    mac = hmac.new(seed.encode(), f"netlab:{pod:02d}".encode(), hashlib.sha256).digest()
    return base64.b32encode(mac).decode()[:24].lower()


def settings(env):
    def num(key, default):
        raw = env.get(key, "") or str(default)
        try:
            return int(raw)
        except ValueError:
            raise ConfigError(f"{key} must be a whole number, got {raw!r}")
    s = {"students": num("STUDENT_COUNT", 30), "max": num("NETLAB_MAX_STUDENTS", 15),
         "switch": num("NETLAB_SWITCH", 1), "manual": num("NETLAB_MANUAL_BRANCH", 1),
         "data_net": env.get("NETLAB_DATA_NET", "") or "10.81.0.0/16",
         "seed": env.get("STUDENT_PASSWORD_SEED", "")}
    if s["students"] < 1:
        raise ConfigError("STUDENT_COUNT must be at least 1")
    if s["students"] > s["max"]:
        raise ConfigError(f"netlab is capped at {s['max']} students (NETLAB_MAX_STUDENTS): each student runs "
                          f"{8 if s['switch'] else 6} containers and a rootless host runs out of kernel keys near 200. "
                          f"STUDENT_COUNT is {s['students']}.")
    if not s["seed"]:
        raise ConfigError("STUDENT_PASSWORD_SEED is empty; the pods' root passwords cannot be derived")
    return s


class Subnets:
    """/29s in order from the data network; Docker keeps the first address of each for itself."""

    def __init__(self, cidr):
        self._iter = ipaddress.ip_network(cidr).subnets(new_prefix=29)

    def next(self):
        try:
            return str(next(self._iter))
        except StopIteration:
            raise ConfigError("NETLAB_DATA_NET has no /29 left; use a larger range")


def branch_nodes(pod, b, switch, nets):
    """[(node role, [(network key, entry for NODE_PORTS)])] for one branch. nets: key -> /29."""
    def key(seg):
        return f"netlab_{pod:02d}_{b}_{seg}"

    def entry(seg, mode, vlans="", addr="", gw="", name=""):
        tail = f"|{gw}|{name}" if name else (f"|{gw}" if gw else "")
        return key(seg), f"{nets[key(seg)]}|{mode}|{vlans}|{addr}{tail}"
    if switch:
        return [("pc", [entry("acc10", "plain", "", LAB["pc"], "10.10.10.1")]),
                # Switch ports are named for what they connect to, so a lab can say `bridge vlan add dev to-pc ...`.
                ("sw", [entry("acc10", "access", "10", name="to-pc"), entry("acc20", "access", "20", name="to-web"),
                        entry("trk", "trunk", "10,20", name="to-fw")]),
                ("fw", [entry("trk", "tagged", "", f"10={LAB['fw10']},20={LAB['fw20']}")]),
                ("web", [entry("acc20", "plain", "", LAB["web"], "10.10.20.1")])]
    return [("pc", [entry("cl", "plain", "", LAB["pc"], "10.10.10.1")]),
            ("fw", [entry("cl", "plain", "", LAB["fw10"]), entry("wb", "plain", "", LAB["fw20"])]),
            ("web", [entry("wb", "plain", "", LAB["web"], "10.10.20.1")])]


def render(env):
    s = settings(env)
    subnets = Subnets(s["data_net"])
    services, networks = [], []
    for pod in range(0, s["students"] + 1):
        root_pw = password(s["seed"], pod)
        for b in ("m", "a") if s["manual"] else ("a",):
            segs = ("acc10", "acc20", "trk") if s["switch"] else ("cl", "wb")
            nets = {f"netlab_{pod:02d}_{b}_{seg}": subnets.next() for seg in segs}
            for key, cidr in nets.items():
                networks.append((key, cidr, pod, b))
            for role, ports in branch_nodes(pod, b, s["switch"], nets):
                name = f"{role}-{b}-{pod:02d}"
                services.append(service(name, role, pod, b, root_pw, [k for k, _ in ports], [p for _, p in ports]))
    out = ["# Generated by modules/netlab/generate.py; do not edit (./dojo rewrites it at every start).",
           f"# {s['students']} student pod(s) + the facilitator's, switch={s['switch']}, manual branch={s['manual']}.",
           "services:"]
    for name, body in services:
        out.append(f"  {name}:")
        out.extend(f"    {line}" for line in body)
    out.append("networks:")
    for key, cidr, pod, b in networks:
        out += [f"  {key}:", "    internal: true", f"    ipam: {{config: [{{subnet: {cidr}}}]}}",
                f"    labels: {{topiary.module: netlab, topiary.netlab.pod: \"{pod:02d}\", topiary.netlab.branch: {b}}}"]
    return "\n".join(out) + "\n"


def service(name, role, pod, b, root_pw, net_keys, ports):
    j = json.dumps
    lines = [f"image: {IMAGE}", f"container_name: {j('netlab_' + name.replace('-', '_'))}", "init: true",
             "restart: unless-stopped", "environment:",
             f"  - NODE_ROLE={role}", f"  - NODE_NAME={name}", f"  - ROOT_PASSWORD={root_pw}",
             f"  - MGMT_CIDR={MGMT_CIDR}", f"  - NODE_PORTS={' '.join(ports)}",
             "labels:", "  topiary.module: netlab", f"  topiary.netlab.pod: \"{pod:02d}\"",
             f"  topiary.netlab.branch: {b}", f"  topiary.netlab.role: {role}",
             "cap_drop: [ALL]", f"cap_add: [{', '.join(CAPS)}]", "security_opt: [\"no-new-privileges:true\"]",
             "pids_limit: 64", f"mem_limit: {'48m' if role == 'web' else '32m'}"]
    if role == "pc":
        lines += ["sysctls:", "  net.ipv4.ping_group_range: \"0 0\""]
    if role == "fw":
        lines += ["sysctls:", "  net.ipv4.ip_forward: \"1\""]
    lines += ["networks:", "  - netlab_mgmt"] + [f"  - {k}" for k in net_keys]
    return name, lines


def main():
    try:
        sys.stdout.write(render(os.environ))
    except ConfigError as e:
        print(f"netlab: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
