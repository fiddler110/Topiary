#!/bin/sh
# netlab: one account's pod password (~/.config/dojo/netlab-password, 0600) and its ~/netlab workspace.
# Usage: seed.sh <user> <pod number>. Called by account.d/57-netlab.sh and start.d/50-netlab.sh.
# The password is generate.py's password(): base32(HMAC-SHA256(STUDENT_PASSWORD_SEED, "netlab:NN"))[:24], lowercase.
# ~/netlab is copied once and never overwritten; the password is rewritten every time (it only depends on the seed).
set -u
user="$1" pod="$(printf '%02d' "$2")"
home="$(getent passwd "$user" | cut -d: -f6)"
[ -n "$home" ] && [ -d "$home" ] || { echo "netlab: no home for $user; skipping" >&2; exit 0; }
group="$(id -gn "$user")" || exit 0
if [ -z "${STUDENT_PASSWORD_SEED:-}" ]; then
  echo "netlab: STUDENT_PASSWORD_SEED is empty; $user gets no pod password" >&2
  exit 0
fi

dir="$home/.config/dojo"
[ -d "$home/.config" ] || install -d -m 0700 -o "$user" -g "$group" "$home/.config" || exit 0
[ -d "$dir" ] || install -d -m 0700 -o "$user" -g "$group" "$dir" || exit 0
(umask 077 && NETLAB_POD="$pod" python3 -c '
import base64, hashlib, hmac, os
mac = hmac.new(os.environ["STUDENT_PASSWORD_SEED"].encode(), ("netlab:" + os.environ["NETLAB_POD"]).encode(),
               hashlib.sha256).digest()
print(base64.b32encode(mac).decode()[:24].lower())' > "$dir/netlab-password.tmp") \
  && chown "$user:$group" "$dir/netlab-password.tmp" && mv "$dir/netlab-password.tmp" "$dir/netlab-password" \
  || echo "netlab: could not write $user's pod password" >&2

# The checker key (netlab-checker/checker.py check_key): same HMAC, label "netlab-check:<checker user name>". The
# facilitator is root here but the checker knows them as FACILITATOR_USERNAME, so the name is stored beside the key.
cuser="$user"; [ "$pod" = 00 ] && cuser="${FACILITATOR_USERNAME:-root}"
(umask 077 && CHECK_USER="$cuser" python3 -c '
import base64, hashlib, hmac, os
mac = hmac.new(os.environ["STUDENT_PASSWORD_SEED"].encode(), ("netlab-check:" + os.environ["CHECK_USER"]).encode(),
               hashlib.sha256).digest()
print(base64.b32encode(mac).decode()[:24].lower())' > "$dir/netlab-check-key.tmp" \
  && printf '%s\n' "$cuser" > "$dir/netlab-check-user.tmp") \
  && chown "$user:$group" "$dir/netlab-check-key.tmp" "$dir/netlab-check-user.tmp" \
  && mv "$dir/netlab-check-key.tmp" "$dir/netlab-check-key" && mv "$dir/netlab-check-user.tmp" "$dir/netlab-check-user" \
  || echo "netlab: could not write $user's check key" >&2

ws="$home/netlab"
[ -e "$ws" ] && exit 0
cp -r /usr/local/share/netlab/seed "$ws" || exit 0
# hosts.ini: the pod's own nodes by name. Branch M and the switch are optional (module.env).
{
  for b in m a; do
    [ "$b" = m ] && [ "${NETLAB_MANUAL_BRANCH:-1}" = 0 ] && continue
    case "$b" in m) g=manual ;; a) g=auto ;; esac
    echo "[$g]"
    for r in pc sw fw web; do
      [ "$r" = sw ] && [ "${NETLAB_SWITCH:-1}" = 0 ] && continue
      echo "$r-$b-$pod"
    done
    echo
  done
  for r in pc sw fw web; do
    [ "$r" = sw ] && [ "${NETLAB_SWITCH:-1}" = 0 ] && continue
    echo "[$r]"
    [ "${NETLAB_MANUAL_BRANCH:-1}" = 0 ] || echo "$r-m-$pod"
    echo "$r-a-$pod"
    echo
  done
} > "$ws/hosts.ini"
sed -i "s/@POD@/$pod/g" "$ws/group_vars/all.yml" "$ws/LAB-README.md" "$ws"/labs/*/README.md
chown -R "$user:$group" "$ws"
exit 0
