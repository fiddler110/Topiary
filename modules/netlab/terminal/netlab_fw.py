#!/usr/bin/env python3
"""netlab per-uid firewall for the shared terminal (run by start.d/50-netlab.sh as root).

All students share this container's network namespace, and every pod's nodes sit on netlab_mgmt, so without this
student N's shell could open TCP to pod M's nodes. The rules go on the OUTPUT chain, matched by the sending uid:

  uid 0                      -> RETURN (the facilitator and the container's own services)
  uid of pod N's account     -> RETURN for pod N's management block only
  anyone else, to netlab_mgmt -> DROP (the connection never opens; the sender sees a timeout)

Traffic to anywhere else (the gateway, DNS, Forgejo, the checker on workshop_lab) never matches `-d MGMT_CIDR`.
build_rules() is pure (tests: modules/netlab/test_fw.py); main() resolves uids and loads the result with
iptables-restore --noflush, which replaces the chain in one step (no open window on a re-run).
Pod addressing must match generate.py (mgmt_ip); test_fw.py checks the two agree.
"""
import os
import pwd
import subprocess
import sys

CHAIN = "NETLAB_ISOLATION"
MGMT_CIDR = "10.80.0.0/22"          # generate.py MGMT_CIDR
POD_BASE = (10, 80, 1, 0)           # generate.py MGMT_POD_BASE
POD_SIZE = 8                        # addresses per pod: two branches of pc, sw, fw, web


def pod_block(pod):
    """CIDR of pod N's management addresses (generate.py mgmt_ip puts every node of the pod inside it)."""
    if not 0 <= pod < 32:
        raise ValueError(f"pod {pod} is outside the management layout")
    a, b, c, d = POD_BASE
    return f"{a}.{b}.{c}.{d + pod * POD_SIZE}/29"


def roster(env):
    """[(username, pod)]: studentNN is pod NN, demo bot testuserK is pod STUDENT_COUNT+K (account.d/57-netlab.sh)."""
    students = int(env.get("STUDENT_COUNT") or 30)
    bots = int(env.get("BOT_COUNT") or 0)
    prefix = env.get("STUDENT_PREFIX") or "student"
    bprefix = env.get("BOT_PREFIX") or "testuser"
    out = [(f"{prefix}{n:02d}", n) for n in range(1, students + 1)]
    return out + [(f"{bprefix}{k}", students + k) for k in range(1, bots + 1)]


def build_rules(uid_pods, mgmt=MGMT_CIDR, chain=CHAIN):
    """iptables-restore text for the filter table. uid_pods: {uid: pod}. Uid 0 is always left alone."""
    lines = ["*filter", f":{chain} - [0:0]", f"-A {chain} -m owner --uid-owner 0 -j RETURN"]
    for uid, pod in sorted(uid_pods.items()):
        if uid != 0:
            lines.append(f"-A {chain} -d {pod_block(pod)} -m owner --uid-owner {uid} -j RETURN")
    # DROP, not REJECT: measured here (iptables-nft in the rootless netns), REJECT in OUTPUT never reaches the local
    # socket in any of its variants (tcp-reset, icmp-port-unreachable, ...), so it behaves like DROP and needs a module.
    lines += [f"-A {chain} -d {mgmt} -j DROP", "COMMIT", ""]
    return "\n".join(lines)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def main(env=os.environ):
    uid_pods = {}
    for name, pod in roster(env):
        try:
            uid_pods[pwd.getpwnam(name).pw_uid] = pod
        except KeyError:
            # No account, nobody to allow; the catch-all DROP still covers the uid if it ever appears.
            print(f"netlab firewall: no account {name}; pod {pod:02d} has no one allowed", file=sys.stderr)
    rules = build_rules(uid_pods)
    r = run(["iptables-restore", "--noflush"], input=rules)
    if r.returncode != 0:
        print(f"netlab firewall: iptables-restore failed: {r.stderr.strip()}", file=sys.stderr)
        return 1
    if run(["iptables", "-C", "OUTPUT", "-j", CHAIN]).returncode != 0:
        # First in OUTPUT, so another chain's early ACCEPT cannot let a student past it.
        r = run(["iptables", "-I", "OUTPUT", "1", "-j", CHAIN])
        if r.returncode != 0:
            print(f"netlab firewall: cannot jump to {CHAIN}: {r.stderr.strip()}", file=sys.stderr)
            return 1
    # Read it back: the hook only reports success if the kernel really holds one RETURN per account, and the catch-all DROP.
    shown = run(["iptables", "-S", CHAIN]).stdout
    want = len(uid_pods) + 1
    if shown.count("-j RETURN") != want or shown.count("-j DROP") != 1:
        print(f"netlab firewall: {CHAIN} does not hold the rules just written:\n{shown}", file=sys.stderr)
        return 1
    print(f"netlab firewall: {len(uid_pods)} account(s) limited to their own pod on netlab_mgmt", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
