#!/bin/sh
# netlab account.d hook (engine/web-terminal/entrypoint.sh, workspace-control.py): the account's pod password and
# ~/netlab, at start and again after a student reset (which removes the home). Student N gets pod N; demo bot
# ${BOT_PREFIX}K (./dojo --test) is treated like a student and gets pod STUDENT_COUNT+K, as modules/netlab/generate.py
# and netlab-checker's Config.pod_of work out. Any other account gets none. Never fails: a failing account.d hook
# stops the container.
set -u
user="$1"
prefix="${STUDENT_PREFIX:-student}"
bprefix="${BOT_PREFIX:-testuser}"
students="${STUDENT_COUNT:-30}"
bots="${BOT_COUNT:-0}"
# A digits-only suffix, zero-stripped so 08 and 09 are not read as bad octal; empty means not this prefix.
suffix() { n="${user#"$1"}"; case "$n" in ''|*[!0-9]*) return 1 ;; esac; printf '%s' "$n" | sed 's/^0*//'; }
bot=0
if [ "${user#"$bprefix"}" != "$user" ] && num="$(suffix "$bprefix")"; then
  [ -n "$num" ] && [ "$num" -le "$bots" ] || exit 0
  num=$((students + num)); bot=1
elif num="$(suffix "$prefix")"; then
  [ -n "$num" ] && [ "$num" -le "$students" ] || exit 0
else
  exit 0
fi
/usr/local/lib/netlab/seed.sh "$user" "$num" || true
# A demo bot has no one to work the labs out, so it gets the reference solutions in its own (0700) home. They are
# mounted where only root can reach them (compose.yml), never anywhere a student can read.
if [ "$bot" = 1 ] && [ -d /opt/netlab-private/solutions ]; then
  home="$(getent passwd "$user" | cut -d: -f6)"
  if [ -n "$home" ] && [ -d "$home" ] && [ ! -e "$home/.netlab-solutions" ]; then
    cp -r /opt/netlab-private/solutions "$home/.netlab-solutions" \
      && chown -R "$user:$(id -gn "$user")" "$home/.netlab-solutions" || true
  fi
fi
exit 0
