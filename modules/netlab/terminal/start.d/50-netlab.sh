#!/bin/sh
# netlab start.d hook (root, after every account exists).
#
# 1. The per-uid firewall (netlab_fw.py): student N, and demo bot K (pod STUDENT_COUNT+K), can open connections only to
#    their own pod's management addresses on netlab_mgmt. This container's network namespace is shared by every
#    student, so a source address never says who is asking; the owner uid does.
#    It FAILS CLOSED: if the rules cannot be applied and read back, this exits 1, the engine stops the container
#    (start.d: "a failing hook stops the container") and ./dojo reports it unhealthy. The alternative, starting with
#    every pod open to every student, would only be noticed when someone reads another pod's nodes, and only the
#    derived root password would then be left in the way. A class that does not start is noticed at once.
#    Needs NET_ADMIN on web-terminal, which the engine already grants for DOJO_ISOLATION; there is nothing for the
#    module to add. The rules are lost with the container's network namespace and rebuilt by this hook at every start.
# 2. The facilitator, who is root in the terminal, gets pod 00 (students are seeded by account.d/57-netlab.sh).
set -u
if ! python3 -B /usr/local/lib/netlab/fw.py; then
  echo "netlab: per-pod firewall NOT applied; refusing to start the terminal with every pod open to every student." >&2
  echo "netlab: it needs NET_ADMIN on web-terminal and iptables with the owner match." >&2
  exit 1
fi
/usr/local/lib/netlab/seed.sh root 0 || true
exit 0
