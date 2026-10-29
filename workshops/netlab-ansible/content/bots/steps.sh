# netlab-ansible demo bot steps (see engine/web-terminal/bot-runner.sh's BOT_STEPS_FILE): each bot works its own pod
# like a student, the A labs in order (A1 look around; A2-A3 the switch; A4-A9 the firewall and web path; A10-A11 extras), and asks the checker (`dojo netlab check A<n>`) after each.
# Bots are treated like students: testuserK owns the pod after the last student's (modules/netlab/generate.py), and
# the terminal copies the reference solutions into the bot's own ~/.netlab-solutions (account.d/57-netlab.sh).
#
# What is simplified. A student configures branch m by hand over SSH and branch a with their own playbooks. The bot
# applies the reference solution to a, and to m it runs the same playbooks pointed at the `manual` group (a copy under
# ~/netlab/.m with `:&auto` -> `:&manual` and `-a-` -> `-m-`), so both branches end in the same state, which is
# what the checker compares. The bot does not type the hand-built commands.
#
# Personas (engine/README.md): expert = every lab with one deliberate mistake; intermediate = labs A1-A11, a failed
# check before every fix, every round; novice = A1-A5 only, with the most mistakes (wrong directory, typos, a check
# before any work). The checker allows 6 checks a minute per pod, so check_lab spaces them even with --fast.
#
# Every step is safe to re-run from the top (the runner retries a failed step); a step returns the final check's
# exit code. Round 2+ (without --fast) resets both branches first.

NL="$HOME/netlab"
SOL="$HOME/.netlab-solutions"
LAST_CHECK=-100
declare -A NDIR=([A2]=S1-vlans [A3]=S2-trunk [A4]=1-first-playbook [A5]=2-variables-loops [A6]=3-idempotency
  [A7]=4-templates-validate [A8]=6-lockdown [A9]=8-capstone [A10]=5-vault [A11]=7-roles)

# The engine's orient() looks around a git repo; ~/netlab is not one.
orient() {
  [ $(( RANDOM % 100 )) -lt "$ORIENT_FREQ" ] || return 0
  case $(( RANDOM % 3 )) in
    0) run_cmd "pwd" ;;
    1) run_cmd "ls" ;;
    2) run_cmd "ls labs" ;;
  esac
}

# `dojo netlab check LAB`, at most one every 12 s (the limit is 6 a minute), retried while the checker says no (exit 2).
check_lab() {
  local lab=$1 rc tries=0 wait
  while :; do
    wait=$(( LAST_CHECK + 12 - SECONDS ))
    [ "$wait" -gt 0 ] && sleep "$wait"
    run_cmd "dojo netlab check $lab"; rc=$?
    LAST_CHECK=$SECONDS
    if [ "$rc" = 2 ] && [ "$tries" -lt 5 ]; then
      tries=$((tries + 1)); narrate "the checker would not answer (rate limit or a node starting?) -- waiting 20s"
      sleep 20; continue
    fi
    return "$rc"
  done
}

# Who makes a deliberate mistake on lab $1 this round.
wants_mistake() {
  case "$PERSONA" in
    expert) [ "$1" = A4 ] && [ "$ROUND" = 1 ] ;;
    *) return 0 ;;
  esac
}

# A check before any work: it must fail (the lab is not done yet).
check_unsolved() { # lab
  wants_mistake "$1" || return 0
  narrate "(demo) checking lab $1 before doing it, to see what a failing check says"
  check_lab "$1" && narrate "(unexpected) lab $1 already passes" 
  narrate "right -- those are the goals. Doing the lab."
  return 0
}

# Novice and intermediate mistakes that are not a check: the wrong directory, a mistyped command.
wrong_dir() { # lab
  [ "$PERSONA" = novice ] || return 0
  narrate "(demo) running the playbook from the wrong directory"
  run_cmd "cd /tmp && ansible-playbook labs/${NDIR[$1]}/site.yml"
  narrate "right -- ansible.cfg and hosts.ini live in ~/netlab. Going there."
  cd "$NL" || return 1
}

typo() { # the command as typed, the command meant
  [ "$PERSONA" = novice ] || return 0
  run_cmd "$1"
  narrate "typo -- trying again"
  run_cmd "$2"
}

# Copy the reference solution over the lab folder and move its group_vars where Ansible reads them (solutions/README.md).
apply_solution() { # lab
  local d=${NDIR[$1]}
  cd "$NL" || return 1
  [ -d "$SOL/$d" ] || { narrate "no reference solution at $SOL/$d"; return 1; }
  narrate "writing lab $1's playbook (the reference solution)"
  run_cmd "cp -r $SOL/$d/. labs/$d/" || return 1
  if [ -d "labs/$d/group_vars" ]; then
    run_cmd "mv labs/$d/group_vars/*.yml group_vars/ && rmdir labs/$d/group_vars" || return 1
  fi
}

# Branch m: the same lab tree aimed at the manual group's nodes.
m_copy() {
  rm -rf "$NL/.m"
  cp -r "$NL/labs" "$NL/.m" || return 1
  find "$NL/.m" \( -name '*.yml' -o -name '*.j2' \) -exec sed -i -e 's/:&auto/:\&manual/' -e 's/-a-{{/-m-{{/g' {} +
}
run_m() { # path under labs/ then extra ansible-playbook args
  local play=$1; shift
  narrate "branch m: the same lab, aimed at the manual branch"
  m_copy || return 1
  cd "$NL" || return 1
  run_cmd "ansible-playbook .m/$play $*"
}

# Apply a lab's playbook to branch a (twice, to show changed=0) and to branch m.
do_lab() { # lab, extra ansible-playbook args
  local lab=$1 d=${NDIR[$1]}; shift
  cd "$NL" || return 1
  run_cmd "ansible-playbook labs/$d/site.yml $*" || return 1
  run_cmd "ansible-playbook labs/$d/site.yml $* 2>&1 | tail -n 4"
  run_m "$d/site.yml" "$@" || return 1
}

lab_start() { # lab, title
  cd "$NL" || return 1
  narrate "Lab $1 -- $2"
  [ "$PERSONA" = novice ] && [ -f "labs/${NDIR[$1]}/README.md" ] && run_cmd "head -n 12 labs/${NDIR[$1]}/README.md"
  orient
  return 0
}

step_n0_orient() {
  cd "$NL" || return 1
  if [ "$ROUND" -gt 1 ]; then
    narrate "round $ROUND: both branches back to the baseline first"
    run_cmd "ansible-playbook reset_fw.yml" || return 1
    run_cmd "ansible-playbook reset_switch.yml -e restore=true" || return 1
  fi
  narrate "Lab A1 -- orientation: what Ansible knows about the pod, then ask every node"
  if [ "$PERSONA" = novice ]; then
    narrate "(demo) asking Ansible from the wrong directory"
    run_cmd "cd /tmp && ansible-inventory --graph"
    narrate "right -- no inventory here. Heading into ~/netlab."
    cd "$NL" || return 1
    run_cmd "ls"
  fi
  run_cmd "ansible-inventory --graph" || return 1
  run_cmd "ansible all -m ansible.builtin.ping | tail -n 12"
  run_cmd "ansible fw -m ansible.builtin.command -a 'iptables -S'"
  run_cmd "ansible-playbook probe.yml -e branch=a -e proto=icmp -e expect=allowed"
  run_cmd "ansible-playbook probe.yml -e branch=a -e expect=blocked"
  check_lab A1
}

step_nA4() {
  lab_start A4 "a first playbook: the web page" || return 1
  check_unsolved A4
  wrong_dir A4
  apply_solution A4 || return 1
  typo "ansible-playbok labs/1-first-playbook/site.yml" "echo 'ansible-playbook it is'"
  do_lab A4 || return 1
  run_cmd "ansible 'web:&auto' -m ansible.builtin.command -a 'curl -s http://127.0.0.1/'"
  run_cmd "ansible-playbook compare.yml"
  check_lab A4
}

step_nA5() {
  lab_start A5 "variables and loops: open HTTP and HTTPS" || return 1
  check_unsolved A5
  wrong_dir A5
  apply_solution A5 || return 1
  do_lab A5 || return 1
  run_cmd "ansible-playbook probe.yml -e branch=a -e expect=allowed"
  check_lab A5
}

step_nA6() {
  lab_start A6 "idempotency: a certificate and HTTPS" || return 1
  check_unsolved A6
  wrong_dir A6
  apply_solution A6 || return 1
  do_lab A6 || return 1
  run_cmd "ansible-playbook probe.yml -e branch=a -e port=443 -e expect=allowed"
  check_lab A6
}

step_nA7() {
  lab_start A7 "templates and validate: a hardened sshd_config" || return 1
  check_unsolved A7
  apply_solution A7 || return 1
  do_lab A7 || return 1
  check_lab A7
}

step_nA10() {
  lab_start A10 "secrets with OpenBao: two repos, two vaults" || return 1
  check_unsolved A10
  local ns="students/$BOT_USER" t
  narrate "as the admin: one vault per team, a generated vault password in each, and a policy to read just that"
  for t in fw sw; do
    run_cmd "bao namespace create -namespace=$ns $t >/dev/null 2>&1 || true; bao secrets enable -namespace=$ns/$t -path=secret kv-v2 >/dev/null 2>&1 || true" || return 1
    # the first write to a new KV v2 engine can fail for a moment
    run_cmd "for try in 1 2 3 4 5 6 7 8; do bao kv put -namespace=$ns/$t secret/ansible password=\"\$(openssl rand -base64 18)\" >/dev/null 2>&1 && break; sleep 3; done; bao kv metadata get -namespace=$ns/$t secret/ansible >/dev/null && echo stored" || return 1
    run_cmd "printf 'path \"secret/data/ansible\" { capabilities = [\"read\"] }\n' | bao policy write -namespace=$ns/$t $t-team -" || return 1
  done
  apply_solution A10 || return 1
  for t in fw sw; do
    cd "$NL/labs/5-vault/$t-repo" || return 1
    run_cmd "chmod +x vault-pass.sh && ./vault-pass.sh | wc -c" || return 1
    local var=${t}_admin_password; [ "$t" = sw ] && var=sw_mgmt_password
    run_cmd "printf '%s: \"%s-secret\"\n' $var $BOT_USER > secrets.yml && ansible-vault encrypt secrets.yml --vault-password-file ./vault-pass.sh" || return 1
    run_cmd "head -1 secrets.yml"
    run_cmd "ansible-playbook site.yml --vault-password-file ./vault-pass.sh" || return 1
    run_cmd "ansible-playbook site.yml --vault-password-file ./vault-pass.sh 2>&1 | tail -n 4"
  done
  narrate "the twist: the firewall team's token is refused by the switch vault"
  run_cmd "tok=\$(bao token create -namespace=$ns/fw -policy=fw-team -ttl=10m -field=token); cd $NL/labs/5-vault/sw-repo; BAO_TOKEN=\$tok ./vault-pass.sh; echo exit=\$?"
  # branch m: the same secrets, put on the manual nodes (the playbooks aimed at the manual group)
  narrate "branch m: the same repos, aimed at the manual branch"
  for t in fw sw; do
    run_cmd "rm -rf $NL/.m5-$t && cp -r $NL/labs/5-vault/$t-repo $NL/.m5-$t && sed -i 's/:&auto/:\&manual/' $NL/.m5-$t/site.yml && sed -i 's#^inventory = .*#inventory = ../hosts.ini#' $NL/.m5-$t/ansible.cfg" || return 1
    run_cmd "cd $NL/.m5-$t && ansible-playbook site.yml --vault-password-file ./vault-pass.sh" || return 1
  done
  cd "$NL" || return 1
  run_cmd "rm -rf $NL/.m5-fw $NL/.m5-sw"
  check_lab A10
}

step_nA8() {
  lab_start A8 "lockdown: block/rescue and a default drop" || return 1
  check_unsolved A8
  apply_solution A8 || return 1
  do_lab A8 || return 1
  check_lab A8
}

step_nA11() {
  lab_start A11 "roles: the same end state, organised" || return 1
  apply_solution A11 || return 1
  run_cmd "ansible-playbook labs/7-roles/site.yml" || return 1
  run_cmd "ansible-playbook labs/7-roles/site.yml 2>&1 | tail -n 4"
  command -v ansible-lint >/dev/null 2>&1 && run_cmd "ansible-lint labs/7-roles/site.yml 2>&1 | tail -n 5"
  check_lab A11
}

step_nA9() {
  lab_start A9 "capstone: rebuild branch a from the baseline with one command" || return 1
  apply_solution A9 || return 1
  narrate "lab A10's /admin is not part of the capstone: both branches back to the baseline, m rebuilt as the reference"
  run_cmd "ansible-playbook reset_fw.yml" || return 1
  run_m 8-capstone/site.yml || return 1
  cd "$NL" || return 1
  check_unsolved A9
  run_cmd "ansible-playbook labs/8-capstone/site.yml" || return 1
  run_cmd "ansible-playbook labs/8-capstone/site.yml 2>&1 | tail -n 4"
  run_cmd "ansible-playbook probe.yml -e branch=a -e port=8080 -e expect=blocked"
  run_cmd "ansible-playbook compare.yml"
  check_lab A9
}

step_nA2() {
  lab_start A2 "VLANs and access ports (switch)" || return 1
  narrate "starting from a blank switch: baseline firewalls, both switches blanked"
  run_cmd "ansible-playbook reset_fw.yml" || return 1
  run_cmd "ansible-playbook reset_switch.yml" || return 1
  run_cmd "ansible-playbook probe.yml -e branch=a -e proto=icmp -e expect=blocked"
  check_unsolved A2
  apply_solution A2 || return 1
  do_lab A2 || return 1
  check_lab A2
}

step_nA3() {
  lab_start A3 "the trunk and router-on-a-stick" || return 1
  check_unsolved A3
  apply_solution A3 || return 1
  do_lab A3 || return 1
  check_lab A3
}

# The runner's step_wrap_round needs the git-fundamentals clone; this pack has none.
step_nwrap() {
  cd "$NL" || return 1
  run_cmd "ansible-playbook compare.yml"
  narrate "round $ROUND done -- taking a short break before round $((ROUND + 1))"
  sleep "$(rand_between "$BOT_ROUND_BREAK_MIN" "$BOT_ROUND_BREAK_MAX")"
}

case "$PERSONA" in
  expert)
    STEPS=(step_n0_orient step_nA2 step_nA3 step_nA4 step_nA5 step_nA6 step_nA7 step_nA8 step_nA9 step_nA10 step_nA11 step_nwrap)
    ;;
  intermediate)
    STEPS=(step_n0_orient step_nA2 step_nA3 step_nA4 step_nA5 step_nA6 step_nA7 step_nA8 step_nA9 step_nA10 step_nA11 step_nwrap)
    ;;
  novice)
    STEPS=(step_n0_orient step_nA2 step_nA3 step_nA4 step_nA5 step_nwrap)
    ;;
esac
