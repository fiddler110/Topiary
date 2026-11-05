# srx-terraform demo bot steps (see engine/web-terminal/bot-runner.sh's BOT_STEPS_FILE). Replaces the
# git-fundamentals default with Labs 0-9: the bot runs the same Terraform and provider as a student, against
# Dojo WAN, and it follows the LAB TEXT: labtext.py reads each lab page and turns its ```hcl blocks into pastes
# and its ```sh blocks into commands, in page order, so a page that drifts from the provider, the simulator or
# `dojo check` fails here. Nothing is copied from content/stages/ (that is `dojo prep`'s).
#
# A block that exits non-zero is logged as `LABTEXT FAIL: ...` and appended to ~/.dojo-bot-labfails; the round
# carries on (a step that returned 1 would only be retried). Read that file after a run. labtext.py lists the few
# places a person answers a prompt (the apply confirmation, the lock demo's second pane, merging the pull request).
#
# Every round builds the whole estate and ENDS BY DESTROYING IT and resetting the clone and the fork
# (step_srx_cleanup), so round 2 starts from an empty org and a fresh repo. The pull requests the pages open in the
# bot's own fork are merged there, as a student does, and the fork's main is reset at the end.
#
# Round-1 mistakes (every round for the intermediate and novice bots under --fast, see MISTAKE_MOD), each put in
# place with the page's own file blocks before that lab's text runs: a typo in a reference (Lab 1), a claim code
# with 14 characters (Lab 4) and a hub profile without dns_override (Lab 5). Lab 6's plan-before-`moved` and Lab
# 7's refused second run are in the pages themselves.

BOTS=/opt/workshop-content/bots
LABS=/opt/workshop-content/lab
LABFAILS="$HOME/.dojo-bot-labfails"

# -- Dojo WAN login ------------------------------------------------------------
# /usr/local/bin/wan-env asks the root-owned broker for this account's MIST_* and TF_HTTP_* values and prints
# `export` lines, which /etc/zsh/zshenv evals for a student's shell. bot-runner.sh runs under bash, so do it here.
ensure_wan_creds() {
  if [ -z "${MIST_API_TOKEN:-}" ] && [ -x /usr/local/bin/wan-env ]; then
    eval "$(/usr/local/bin/wan-env 2>/dev/null)"
  fi
  if [ -n "${MIST_API_TOKEN:-}" ]; then SRX_HAS_WAN=1; else SRX_HAS_WAN=0; fi
}

srx_api() { curl -s -H "Authorization: Token $MIST_API_TOKEN" -H 'Content-Type: application/json' "$@"; }

srx_fail() { narrate "LABTEXT FAIL: $1"; echo "$1" >> "$LABFAILS"; }

# The pages say "review, then merge in Forgejo": merge this bot's own newest open pull request, in its own fork.
srx_merge_pr() {
  local n code
  n="$(api_curl "$API/repos/$BOT_USER/$FORGEJO_REPO/pulls?state=open" | grep -o '"number":[0-9]*' | head -1 | cut -d: -f2)"
  if [ -z "$n" ]; then  # the page says "open a pull request" in prose (Lab 9): open one for the branch just pushed
    local br title body
    br="$(git branch --show-current)"; title="$(git log -1 --format=%s)"
    body="$(python3 -c 'import json,sys; print(json.dumps({"head": sys.argv[1], "base": "main", "title": sys.argv[2], "body": open("plan.txt").read() if len(sys.argv) > 3 else ""}))' "$br" "$title" x 2>/dev/null)"
    n="$(api_curl -X POST "$API/repos/$BOT_USER/$FORGEJO_REPO/pulls" -H 'Content-Type: application/json' -d "$body" | grep -o '"number":[0-9]*' | head -1 | cut -d: -f2)"
    echo "opened pull request #${n:-none} for $br"
  fi
  [ -n "$n" ] || { echo "no open pull request to merge"; return 1; }
  code="$(api_curl -X POST "$API/repos/$BOT_USER/$FORGEJO_REPO/pulls/$n/merge" -H 'Content-Type: application/json' \
          -d '{"Do":"merge"}' -o /dev/null -w '%{http_code}')"
  echo "merged pull request #$n: HTTP $code"
  [ "$code" = 200 ]
}

# Put one `hcl` block of lab page $1 (headed `# NAME`) into the clone: what a student pastes. For a demo mistake.
srx_paste() { python3 "$BOTS/labtext.py" file "$LABS/$1" "$2"; }

# Follow lab page $1 (a number) block by block.
srx_run_lab() {
  local num="$1" dir="$HOME/.dojo-bot-lab$1" n kind label rc
  rm -rf "$dir"
  if ! python3 "$BOTS/labtext.py" steps "$LABS/lab$num.md" "$dir"; then
    srx_fail "lab$num: labtext.py could not read the page"; return 0
  fi
  narrate "Lab $num -- following lab$num.md block by block ($(wc -l < "$dir/index.tsv") steps)"
  while IFS=$'\t' read -r n kind label; do
    case "$kind" in
      skip)  narrate "lab$num step $n not run: $label" ;;
      merge) narrate "lab$num step $n: $label"
             run_cmd "srx_merge_pr"; rc=$?
             [ "$rc" -eq 0 ] || srx_fail "lab$num step $n (merge the pull request) exited $rc" ;;
      *)     narrate "lab$num step $n: $label"
             run_cmd "$(cat "$dir/$n.sh")"; rc=$?
             [ "$rc" -eq 0 ] || srx_fail "lab$num step $n ($label) exited $rc" ;;
    esac
  done < "$dir/index.tsv"
  return 0
}

# -- Labs 0-3 ------------------------------------------------------------------
step_srx_creds() {
  ensure_wan_creds
  if [ "$SRX_HAS_WAN" != 1 ]; then
    narrate "no Dojo WAN login for $BOT_USER yet (wan-env/broker not ready)"
    return 1
  fi
  rm -f "$LABFAILS"
  return 0
}

step_srx_basics() {
  cd "$REPO_DIR" || return 1
  [ "$SRX_HAS_WAN" = 1 ] || { narrate "Labs 0-3 -- no Dojo WAN login -- skipping"; return 0; }
  srx_run_lab 0
  orient
  if [ $(( ROUND % MISTAKE_MOD )) -eq "$MISTAKE_REM" ]; then
    narrate "(demo) a typo in a reference"
    run_cmd "srx_paste lab1.md main.tf"
    run_cmd "sed -i 's/vlan_id = \"10\"/vlan_id = \"10\"\n  subnet2 = mist_org_network.cor.name/' main.tf"
    run_cmd "terraform validate -no-color | head -8"
    narrate "right -- an unsupported argument and an undeclared resource. Undoing."
    run_cmd "srx_paste lab1.md main.tf"
  fi
  srx_run_lab 1
  srx_run_lab 2
  srx_run_lab 3
  return 0
}

# -- Labs 4-5 ------------------------------------------------------------------
step_srx_devices() {
  cd "$REPO_DIR" || return 1
  [ "$SRX_HAS_WAN" = 1 ] || { narrate "Labs 4-5 -- no Dojo WAN login -- skipping"; return 0; }
  if [ $(( ROUND % MISTAKE_MOD )) -eq "$MISTAKE_REM" ]; then
    narrate "(demo) a claim code with 14 characters"
    run_cmd "srx_paste lab4.md variables.tf && srx_paste lab4.md terraform.tfvars && srx_paste lab4.md devices.tf"
    run_cmd "sed -i '0,/SRX300[0-9A-Z]\\{9\\}\"/s//SRX300ABC12345\"/' terraform.tfvars"
    run_cmd "terraform plan -no-color -input=false | grep -E -i 'error|claim' | head -5"
    narrate "right -- the provider checks the code's format before any call. Undoing."
  fi
  srx_run_lab 4
  if [ $(( ROUND % MISTAKE_MOD )) -eq "$MISTAKE_REM" ]; then
    narrate "(demo) forgot dns_override on the hub profile: the profile's DNS is ignored"
    run_cmd "for f in hub.tf profile.tf terraform.tfvars devices.tf; do srx_paste lab5.md \$f; done"
    run_cmd "sed -i '/dns_override = true/d' profile.tf"
    run_cmd "terraform apply -auto-approve -no-color -input=false | tail -2"
    run_cmd "dojo check 5 | grep -E 'FAIL|thing' | head -3; true"
    narrate "right -- the hub kept no DNS: without dns_override the profile's dns_servers are not applied. Putting it back."
  fi
  srx_run_lab 5
  return 0
}

# -- Lab 6 ---------------------------------------------------------------------
step_srx_refactor() {
  cd "$REPO_DIR" || return 1
  [ "$SRX_HAS_WAN" = 1 ] || { narrate "Lab 6 -- no Dojo WAN login -- skipping"; return 0; }
  srx_run_lab 6
  return 0
}

# -- Lab 7 ---------------------------------------------------------------------
step_srx_team() {
  cd "$REPO_DIR" || return 1
  [ "$SRX_HAS_WAN" = 1 ] || { narrate "Lab 7 -- no Dojo WAN login -- skipping"; return 0; }
  srx_run_lab 7
  return 0
}

# -- Labs 8-9 ------------------------------------------------------------------
step_srx_drift() {
  cd "$REPO_DIR" || return 1
  [ "$SRX_HAS_WAN" = 1 ] || { narrate "Lab 8 -- no Dojo WAN login -- skipping"; return 0; }
  srx_run_lab 8
  return 0
}

step_srx_capstone() {
  cd "$REPO_DIR" || return 1
  [ "$SRX_HAS_WAN" = 1 ] || { narrate "Lab 9 -- no Dojo WAN login -- skipping"; return 0; }
  srx_run_lab 9
  return 0
}

# -- End of every round: destroy what this round built and reset the clone and the fork -----
step_srx_cleanup() {
  cd "$REPO_DIR" || return 1
  [ "$SRX_HAS_WAN" = 1 ] || return 0
  if [ -s "$LABFAILS" ]; then
    narrate "LABTEXT: $(wc -l < "$LABFAILS") block(s) failed this round -- see ~/.dojo-bot-labfails"
  else
    narrate "LABTEXT: every lab block ran clean this round"
  fi
  narrate "clean up: destroy what this round built, close the demo pull requests, reset the clone and the fork"
  if [ -d .terraform ]; then
    run_cmd "terraform destroy -auto-approve -no-color -input=false | tail -2"
  fi
  # an object made by hand and never imported (a round that stopped in Lab 8)
  run_cmd "for n in \$(srx_api https://api.mist.com/api/v1/orgs/$MIST_ORG_ID/networks | python3 -c 'import json,sys; [print(n[\"id\"]) for n in json.load(sys.stdin) if n[\"name\"]==\"guest\"]'); do srx_api -X DELETE https://api.mist.com/api/v1/orgs/$MIST_ORG_ID/networks/\$n; done; true"
  local n
  for n in $(api_curl "$API/repos/$BOT_USER/$FORGEJO_REPO/pulls?state=open" | grep -o '"number":[0-9]*' | cut -d: -f2); do
    run_cmd "api_curl -X PATCH -H 'Content-Type: application/json' -d '{\"state\":\"closed\"}' $API/repos/$BOT_USER/$FORGEJO_REPO/pulls/$n -o /dev/null"
  done
  run_cmd "git fetch -q upstream main && git checkout -q -B main upstream/main && git clean -fdxq"
  run_cmd "git push -q -f origin main; for b in \$(git branch --format='%(refname:short)' | grep -v '^main\$'); do git branch -q -D \$b; git push -q origin --delete \$b 2>/dev/null; done; true"
  run_cmd "rm -f ~/lab/site-ids.before"
  return 0
}

case "$PERSONA" in
  expert)
    STEPS=(
      step_ensure_clone
      step_sync_main
      step_srx_creds
      step_srx_basics
      step_srx_devices
      step_srx_refactor
      step_srx_team
      step_srx_drift
      step_srx_capstone
      step_srx_cleanup
      step_wrap_round
    )
    ;;
  intermediate)
    STEPS=(
      step_ensure_clone
      step_sync_main
      step_srx_creds
      step_srx_basics
      step_srx_devices
      step_srx_refactor
      step_srx_cleanup
      step_wrap_round
    )
    ;;
  novice)
    STEPS=(
      step_ensure_clone
      step_sync_main
      step_srx_creds
      step_srx_basics
      step_srx_cleanup
      step_wrap_round
    )
    ;;
esac
