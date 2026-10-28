#!/bin/sh
# netlab start.d hook (root, after every account exists): the facilitator, who is root in the terminal, gets
# pod 00. Students are seeded by account.d/57-netlab.sh.
set -u
/usr/local/lib/netlab/seed.sh root 0 || true
exit 0
