#!/bin/sh
# netlab account.d hook (engine/web-terminal/entrypoint.sh, workspace-control.py): the account's pod password and
# ~/netlab, at start and again after a student reset (which removes the home). Student N gets pod N; accounts
# that are not ${STUDENT_PREFIX}N within STUDENT_COUNT (demo bots) get none. Never fails: a failing account.d hook
# stops the container.
set -u
user="$1"
prefix="${STUDENT_PREFIX:-student}"
n="${user#"$prefix"}"
case "$n" in ''|*[!0-9]*) exit 0 ;; esac
# Accounts are zero-padded (student01); strip the zeros so 08 and 09 are not read as bad octal.
num="$(printf '%s' "$n" | sed 's/^0*//')"
[ -n "$num" ] && [ "$num" -le "${STUDENT_COUNT:-30}" ] || exit 0
/usr/local/lib/netlab/seed.sh "$user" "$num" || true
exit 0
