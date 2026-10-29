# netlab-ansible setup hook, sourced by the openbao module's setup.sh on every start with the provisioner token
# (BAO_TOKEN, `log`, `retry`, `class_users` (students, then demo bots) and `par_each` are set). Safe to re-run. It makes:
#   - the `student` policy (student.hcl), which the module attaches to every student's entity;
#   - the namespace students/<name> for each account. Lab 5 has each student make their own fw and sw team vaults
#     inside it, so the lab is the admin's job as well as the team member's.

# One-user mode (a facilitator's student reset; setup.sh reset_one, with the reset token and DOJO_ONE_USER set): only
# that student's part. Teardown deletes their lab 5 team namespaces, then students/<name> (which revokes every token
# made in them); provision makes students/<name> again.

here=/etc/openbao-setup.d

if [ -z "${DOJO_ONE_USER:-}" ]; then
  retry 30 bao policy write student "$here/student.hcl" >/dev/null
  bao namespace lookup students >/dev/null 2>&1 || retry 30 bao namespace create students >/dev/null
fi

tenancy_one() {
  s="$1"
  BAO_NAMESPACE=students bao namespace lookup "$s" >/dev/null 2>&1 \
    || BAO_NAMESPACE=students retry 10 bao namespace create "$s" >/dev/null \
    || { log "tenancy: could not create students/$s"; exit 1; }
}

# wait_gone NS: OpenBao deletes a namespace in the background; wait until it is gone.
wait_gone() {
  _wg_i=0
  while BAO_NAMESPACE="$1" bao namespace lookup "$2" >/dev/null 2>&1; do
    _wg_i=$((_wg_i + 1))
    [ "$_wg_i" -lt 90 ] || { log "tenancy: $1/$2 is still being deleted after 90s"; return 1; }
    sleep 1
  done
}

# tenancy_teardown NAME: the student's team namespaces (any the lab made), then their own.
tenancy_teardown() {
  s="$1"
  BAO_NAMESPACE=students bao namespace lookup "$s" >/dev/null 2>&1 || return 0
  for _tt_c in $(BAO_NAMESPACE="students/$s" bao namespace list -format=json 2>/dev/null \
                   | sed -n 's/^ *"\([^"/]*\)\/*",* *$/\1/p'); do
    BAO_NAMESPACE="students/$s" retry 10 bao namespace delete "$_tt_c" >/dev/null \
      || { log "tenancy: could not delete students/$s/$_tt_c"; exit 1; }
    wait_gone "students/$s" "$_tt_c" || exit 1
  done
  BAO_NAMESPACE=students retry 10 bao namespace delete "$s" >/dev/null \
    || { log "tenancy: could not delete students/$s"; exit 1; }
  wait_gone students "$s" || exit 1
}

if [ "${DOJO_RESET_PHASE:-}" = teardown ]; then
  par_each tenancy_teardown || exit 1
  log "tenancy: deleted students/$DOJO_ONE_USER"
  return 0
fi
par_each tenancy_one || exit 1
log "tenancy: the student policy and $(class_users | wc -l) namespaces under students/"
