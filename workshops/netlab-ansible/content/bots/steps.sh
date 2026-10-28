# netlab-ansible demo bot steps (see engine/web-terminal/bot-runner.sh's BOT_STEPS_FILE): each bot works its own pod
# like a student, labs 0-8 then the switch labs S1-S3, and asks the checker (`dojo netlab check N`) after each.
# Bots are treated like students: testuserK owns the pod after the last student's (modules/netlab/generate.py), and
# the terminal copies the reference solutions into the bot's own ~/.netlab-solutions (account.d/57-netlab.sh).
#
# What is simplified. A student configures branch m by hand over SSH and branch a with their own playbooks. The bot
# applies the reference solution to a, and to m it runs the same playbooks pointed at the `manual` group (a copy under
# ~/netlab/.m with `:&auto` -> `:&manual` and `-a-` -> `-m-`), so both branches end in the same state, which is
# what the checker compares. The bot does not type the hand-built commands.
#
# Personas (engine/README.md): expert = every lab with one deliberate mistake; intermediate = labs 0-8, a failed
# check before every fix, every round; novice = labs 0-3 only, with the most mistakes (wrong directory, typos, a check
# before any work). The checker allows 6 checks a minute per pod, so check_lab spaces them even with --fast.
#
# Every step is safe to re-run from the top (the runner retries a failed step); a step returns the final check's
# exit code. Round 2+ (without --fast) resets both branches first.

NL="$HOME/netlab"
SOL="$HOME/.netlab-solutions"
LAST_CHECK=-100
declare -A NDIR=([1]=1-first-playbook [2]=2-variables-loops [3]=3-idempotency [4]=4-templates-validate
  [5]=5-vault [6]=6-lockdown [7]=7-roles [8]=8-capstone [S1]=S1-vlans [S2]=S2-trunk [S3]=S3-segmentation)

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
    expert) [ "$1" = 1 ] && [ "$ROUND" = 1 ] ;;
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
  narrate "Lab 0 -- orientation: what Ansible knows about the pod, then ask every node"
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
  check_lab 0
}

step_n1() {
  lab_start 1 "a first playbook: the web page" || return 1
  check_unsolved 1
  wrong_dir 1
  apply_solution 1 || return 1
  typo "ansible-playbok labs/1-first-playbook/site.yml" "echo 'ansible-playbook it is'"
  do_lab 1 || return 1
  run_cmd "ansible 'web:&auto' -m ansible.builtin.command -a 'curl -s http://127.0.0.1/'"
  run_cmd "ansible-playbook compare.yml"
  check_lab 1
}

step_n2() {
  lab_start 2 "variables and loops: open HTTP and HTTPS" || return 1
  check_unsolved 2
  wrong_dir 2
  apply_solution 2 || return 1
  do_lab 2 || return 1
  run_cmd "ansible-playbook probe.yml -e branch=a -e expect=allowed"
  check_lab 2
}

step_n3() {
  lab_start 3 "idempotency: a certificate and HTTPS" || return 1
  check_unsolved 3
  wrong_dir 3
  apply_solution 3 || return 1
  do_lab 3 || return 1
  run_cmd "ansible-playbook probe.yml -e branch=a -e port=443 -e expect=allowed"
  check_lab 3
}

step_n4() {
  lab_start 4 "templates and validate: a hardened sshd_config" || return 1
  check_unsolved 4
  apply_solution 4 || return 1
  do_lab 4 || return 1
  check_lab 4
}

step_n5() {
  lab_start 5 "secrets with Vault: /admin behind a password" || return 1
  check_unsolved 5
  apply_solution 5 || return 1
  run_cmd "echo 'bot-vault-pass' > .vault_pass && chmod 600 .vault_pass"
  run_cmd "cp $SOL/5-vault/secrets.yml.example labs/5-vault/secrets.yml && sed -i 's/change-me/$BOT_USER-secret/' labs/5-vault/secrets.yml && ansible-vault encrypt labs/5-vault/secrets.yml --vault-password-file .vault_pass" || return 1
  run_cmd "head -1 labs/5-vault/secrets.yml"
  do_lab 5 --vault-password-file .vault_pass || return 1
  check_lab 5
}

step_n6() {
  lab_start 6 "lockdown: block/rescue and a default drop" || return 1
  check_unsolved 6
  apply_solution 6 || return 1
  do_lab 6 || return 1
  check_lab 6
}

step_n7() {
  lab_start 7 "roles: the same end state, organised" || return 1
  apply_solution 7 || return 1
  run_cmd "ansible-playbook labs/7-roles/site.yml" || return 1
  run_cmd "ansible-playbook labs/7-roles/site.yml 2>&1 | tail -n 4"
  command -v ansible-lint >/dev/null 2>&1 && run_cmd "ansible-lint labs/7-roles/site.yml 2>&1 | tail -n 5"
  check_lab 7
}

step_n8() {
  lab_start 8 "capstone: rebuild branch a from the baseline with one command" || return 1
  apply_solution 8 || return 1
  narrate "lab 5's /admin is not part of the capstone: both branches back to the baseline, m rebuilt as the reference"
  run_cmd "ansible-playbook reset_fw.yml" || return 1
  run_m 8-capstone/site.yml || return 1
  cd "$NL" || return 1
  check_unsolved 8
  run_cmd "ansible-playbook labs/8-capstone/site.yml" || return 1
  run_cmd "ansible-playbook labs/8-capstone/site.yml 2>&1 | tail -n 4"
  run_cmd "ansible-playbook probe.yml -e branch=a -e port=8080 -e expect=blocked"
  run_cmd "ansible-playbook compare.yml"
  check_lab 8
}

step_nS1() {
  lab_start S1 "VLANs and access ports (switch)" || return 1
  narrate "starting from a blank switch: baseline firewalls, both switches blanked"
  run_cmd "ansible-playbook reset_fw.yml" || return 1
  run_cmd "ansible-playbook reset_switch.yml" || return 1
  run_cmd "ansible-playbook probe.yml -e branch=a -e proto=icmp -e expect=blocked"
  check_unsolved S1
  apply_solution S1 || return 1
  do_lab S1 || return 1
  check_lab S1
}

step_nS2() {
  lab_start S2 "the trunk and router-on-a-stick" || return 1
  check_unsolved S2
  apply_solution S2 || return 1
  do_lab S2 || return 1
  check_lab S2
}

step_nS3() {
  lab_start S3 "segmentation policy" || return 1
  check_unsolved S3
  apply_solution S3 || return 1
  do_lab S3 || return 1
  check_lab S3
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
    STEPS=(step_n0_orient step_n1 step_n2 step_n3 step_n4 step_n5 step_n6 step_n7 step_n8 step_nS1 step_nS2 step_nS3 step_nwrap)
    ;;
  intermediate)
    STEPS=(step_n0_orient step_n1 step_n2 step_n3 step_n4 step_n5 step_n6 step_n7 step_n8 step_nwrap)
    ;;
  novice)
    STEPS=(step_n0_orient step_n1 step_n2 step_n3 step_nwrap)
    ;;
esac
