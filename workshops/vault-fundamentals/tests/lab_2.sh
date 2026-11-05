#!/bin/sh
# vault-fundamentals lab 2 (pass, S37), with the stack up: runs lab2.md's
# shell blocks as one student, as written, except where a person types
# (the passphrase box, `pass insert -m` and `pass edit`), which it feeds
# instead. It first removes what an earlier run left (~/.gnupg,
# ~/.password-store), so it can run again. Exits 1 on any failure.
#   sh workshops/vault-fundamentals/tests/lab_2.sh [student03]
# TERMINAL=<container> points it at another terminal container.
s="${1:-student03}"; DOJO_TERMINAL="${TERMINAL:-workshop_terminal}"
labs="$(dirname "$0")/../content/lab"
. "$(dirname "$0")/../../assets/test-lib.sh"   # as, has/lacks, finish, md_blocks
block() { _lab="$1"; shift; md_blocks "$labs/$_lab" "$s" "$@"; }
pw="--batch --pinentry-mode loopback --passphrase 'three words 42'"

"$DOJO_CLI" exec "$DOJO_TERMINAL" id "$s" >/dev/null 2>&1 \
  || { echo "FAIL: no account $s in $DOJO_TERMINAL (pass a student who has signed in, e.g. student01)"; exit 1; }

echo "== reset $s"
as 'gpgconf --kill gpg-agent; rm -rf ~/.gnupg ~/.password-store' >/dev/null 2>&1
as 'git config --global user.name "$USER"; git config --global user.email "$USER@dojo.test"' >/dev/null

echo "== lab 2: pass"
# Block 1 opens the passphrase box; the same key, with the passphrase given here.
has   "a key that expires in a year (block 1)" "$(block lab2.md 1 | sed "s/^gpg --quick-gen-key/gpg $pw --quick-gen-key/")" "[expires:"
# The test's gpg-agent needs the passphrase once, as a person's would after typing it.
as "echo allow-loopback-pinentry > ~/.gnupg/gpg-agent.conf; gpgconf --reload gpg-agent" >/dev/null
# Block 2 ends in `pass insert -m`, which waits for typed lines; feed them.
has   "a store, with git history (block 2)" "$(block lab2.md 2 | sed "s|^pass insert -m|printf 'first-password\\\\nusername: app\\\\nhost: db.internal\\\\n' \| pass insert -m|")" "Password store initialized for $s@dojo.test"
has   "insert -m stored dojo/db" "pass ls dojo" "db"
has   "generate (block 3)" "$(block lab2.md 3)" "dojo/api-token"
has   "folders of .gpg files, encrypted for my key (block 4)" "$(block lab2.md 4)" "db.gpg"
has   "encrypted for my key only" "$(block lab2.md 4)" "$s <$s@dojo.test>"
lacks "the file on disk is not plain text" "cat ~/.password-store/dojo/db.gpg" "first-password"
# gpg-agent caches the passphrase after the first use; give it once here.
as "gpg $pw -d ~/.password-store/dojo/db.gpg" >/dev/null 2>&1
has   "show, first line, one key (block 5)" "$(block lab2.md 5)" "app"
# Block 6 edits in nano; sed makes the same edit.
has   "edit, history shows both versions (block 6)" "$(block lab2.md 6 | sed "s/EDITOR=nano/EDITOR='sed -i s\/first-password\/second-password\/'/")" "-first-password"
has   "the edit was saved" "pass show dojo/db | head -1" "second-password"
has   "a teammate's key (block 7)" "$(block lab2.md 7)
gpg --list-keys teammate@dojo.test" "teammate"
has   "shared: encrypted for two (block 8)" "$(block lab2.md 8)" "teammate <teammate@dojo.test>"
lacks "taken back: the new file is mine only (block 9)" "$(block lab2.md 9 | sed -n 1,2p)" "teammate <teammate@dojo.test>"
has   "but the old copy still opens for them" "$(block lab2.md 9 | sed -n 3p)" "teammate <teammate@dojo.test>"

finish "lab 2"
