# srx-terraform demo bot steps (see engine/web-terminal/bot-runner.sh's BOT_STEPS_FILE). Replaces the
# git-fundamentals default with Labs 0-9: the bot runs the same Terraform and provider as a student, against
# Dojo WAN, using the end-of-lab files in /opt/workshop-content/stages/ (the same files `dojo prep` uses) in
# place of typing them.
#
# Every round builds the whole estate and ENDS BY DESTROYING IT and resetting the clone (step_srx_cleanup),
# so round 2 starts from an empty org and a fresh repo, and a round that is killed partway leaves little behind
# (the next round's first step cleans up too). Bots never merge anything: the pull requests they open in their
# own fork are closed again at the end of the round.
#
# Round-1 mistakes (every round for the intermediate and novice bots under --fast, see MISTAKE_MOD): a typo in a
# reference (Lab 1), a claim code with 14 characters (Lab 4), a hub profile without dns_override (Lab 5), a refactor
# without `moved` (Lab 6, plan only: it is never applied) and a second run while the state lock is held (Lab 7).

STAGES=/opt/workshop-content/stages

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

# Claim codes in the order the labs use them: SRX300 #1 Ottawa, SRX300 #2 Toronto, SRX345 #1 Montreal, SRX345 #2 Halifax, SRX1500 #1 the dc-01 hub.
srx_code() { # model index (1-based)
  dojo wan delivery | awk -v m="$1" 'NR>1 && $1==m {print $4}' | sed -n "${2}p"
}

# Put the end-of-lab files for lab $1 into the clone, with this bot's claim codes in terraform.tfvars.
srx_stage() {
  local dir="$STAGES/lab$1" f rel ott tor mon hal dc
  ott="$(srx_code SRX300 1)"; tor="$(srx_code SRX300 2)"; mon="$(srx_code SRX345 1)"; hal="$(srx_code SRX345 2)"; dc="$(srx_code SRX1500 1)"
  [ -n "$ott" ] && [ -n "$hal" ] || { narrate "could not read the delivery yet"; return 1; }
  (cd "$dir" && find . -type f | sort) | while read -r f; do
    rel="${f#./}"
    mkdir -p "$(dirname "$rel")"
    case "$rel" in
      *.tmpl) sed -e "s/@OTTAWA@/$ott/" -e "s/@TORONTO@/$tor/" -e "s/@MONTREAL@/$mon/" -e "s/@HALIFAX@/$hal/" -e "s/@DC@/$dc/" \
                "$dir/$rel" > "${rel%.tmpl}" ;;
      *) cp "$dir/$rel" "$rel" ;;
    esac
  done
}

srx_plan_summary() { terraform plan -no-color -input=false "$@" | grep -E '^Plan:|^No changes|^Error' ; return 0; }

# Lab N: install the stage, plan, apply, check.
srx_lab() { # lab number, narration
  narrate "Lab $1 -- $2"
  run_cmd "cd '$REPO_DIR' && srx_stage $1"
  run_cmd "terraform fmt -recursive >/dev/null; terraform validate -no-color"
  run_cmd "terraform plan -no-color -input=false | grep -E '^  # |^Plan:|^No changes'"
  run_cmd "terraform apply -auto-approve -no-color -input=false | tail -3"
  run_cmd "dojo check $1"
  return 0
}

# -- Labs 0-3 ------------------------------------------------------------------
step_srx_creds() {
  ensure_wan_creds
  if [ "$SRX_HAS_WAN" != 1 ]; then
    narrate "no Dojo WAN login for $BOT_USER yet (wan-env/broker not ready)"
    return 1
  fi
  return 0
}

step_srx_basics() {
  cd "$REPO_DIR" || return 1
  [ "$SRX_HAS_WAN" = 1 ] || { narrate "Labs 0-3 -- no Dojo WAN login -- skipping"; return 0; }
  narrate "Lab 0 -- the tour: login, delivery, init"
  run_cmd "dojo wan whoami"
  run_cmd "dojo wan delivery"
  orient
  run_cmd "terraform version | head -1"
  run_cmd "terraform init -no-color -input=false -reconfigure | tail -2"
  run_cmd "terraform plan -no-color -input=false"
  run_cmd "dojo check 0"

  if [ $(( ROUND % MISTAKE_MOD )) -eq "$MISTAKE_REM" ]; then
    narrate "(demo) a typo in a reference"
    run_cmd "srx_stage 1"
    run_cmd "sed -i 's/vlan_id = \"10\"/vlan_id = \"10\"\n  subnet2 = mist_org_network.cor.name/' main.tf"
    run_cmd "terraform validate -no-color | head -8"
    narrate "right -- an unsupported argument and an undeclared resource. Undoing."
    run_cmd "srx_stage 1"
  fi
  srx_lab 1 "first objects: a network and two services"
  run_cmd "terraform plan -no-color -input=false | grep -E '^Plan:|^No changes'"
  narrate "right -- a second plan is empty: idempotent"
  srx_lab 2 "the gateway template"
  srx_lab 3 "three sites and their variables"
  return 0
}

# -- Labs 4-5 ------------------------------------------------------------------
step_srx_devices() {
  cd "$REPO_DIR" || return 1
  [ "$SRX_HAS_WAN" = 1 ] || { narrate "Labs 4-5 -- no Dojo WAN login -- skipping"; return 0; }
  if [ $(( ROUND % MISTAKE_MOD )) -eq "$MISTAKE_REM" ]; then
    narrate "(demo) a claim code with 14 characters"
    run_cmd "srx_stage 4"
    run_cmd "sed -i '0,/SRX300[0-9A-Z]\\{9\\}\"/s//SRX300ABC12345\"/' terraform.tfvars"
    run_cmd "terraform plan -no-color -input=false | grep -E -i 'error|claim' | head -5"
    narrate "right -- the provider checks the code's format before any call. Undoing."
  fi
  srx_lab 4 "claim the delivery and assign the gateways to their sites"
  run_cmd "dojo wan config \"\$(dojo wan delivery | awk 'NR==2{print \$3}')\" | grep -E 'host-name|name-server|ntp|address'"

  if [ $(( ROUND % MISTAKE_MOD )) -eq "$MISTAKE_REM" ]; then
    narrate "(demo) forgot dns_override on the hub profile: the profile's DNS is ignored"
    run_cmd "srx_stage 5"
    run_cmd "sed -i '/dns_override = true/d' profile.tf"
    run_cmd "terraform apply -auto-approve -no-color -input=false | tail -2"
    run_cmd "dojo check 5 | grep -E 'FAIL|thing' | head -3; true"
    narrate "right -- the hub kept no DNS: without dns_override the profile's dns_servers are not applied. Putting it back."
  fi
  srx_lab 5 "roles: a hub profile on dc-01 and a device override"
  run_cmd "dojo wan config ottawa-01-gw | grep -E 'host-name|name-server|ntp'"
  run_cmd "dojo wan config \"\$(dojo wan delivery | awk '\$1==\"SRX1500\"{print \$3}')\" | grep -E 'host-name|name-server'; true"
  return 0
}

# -- Lab 6 ---------------------------------------------------------------------
step_srx_refactor() {
  cd "$REPO_DIR" || return 1
  [ "$SRX_HAS_WAN" = 1 ] || { narrate "Lab 6 -- no Dojo WAN login -- skipping"; return 0; }
  narrate "Lab 6 -- write down the site ids, then refactor into modules"
  run_cmd "srx_api https://api.mist.com/api/v1/orgs/$MIST_ORG_ID/sites | python3 -c 'import json,sys; [print(s[\"name\"], s[\"id\"]) for s in json.load(sys.stdin)]' | tee ~/lab/site-ids.before"
  if [ $(( ROUND % MISTAKE_MOD )) -eq "$MISTAKE_REM" ]; then
    narrate "(demo) the refactor WITHOUT moved blocks: read the destroy count, do not apply"
    run_cmd "srx_stage 6 && rm -f moved.tf"
    run_cmd "terraform init -no-color -input=false | tail -1"
    run_cmd "terraform plan -no-color -input=false | grep -E '^Plan:'"
    narrate "right -- seven destroys. Adding the moved blocks."
  fi
  run_cmd "srx_stage 6"
  run_cmd "terraform init -no-color -input=false | tail -1"
  run_cmd "terraform validate -no-color"
  run_cmd "terraform plan -no-color -input=false | grep -E 'has moved|^Plan:'"
  run_cmd "terraform apply -auto-approve -no-color -input=false | tail -2"
  run_cmd "terraform state list | head -12"
  run_cmd "dojo check 6"
  return 0
}

# -- Lab 7 ---------------------------------------------------------------------
step_srx_team() {
  cd "$REPO_DIR" || return 1
  [ "$SRX_HAS_WAN" = 1 ] || { narrate "Lab 7 -- no Dojo WAN login -- skipping"; return 0; }
  narrate "Lab 7 -- shared state with a lock"
  run_cmd "srx_stage 7"
  run_cmd "terraform init -no-color -input=false -migrate-state -force-copy | tail -3"
  run_cmd "terraform plan -no-color -input=false | grep -E '^Plan:|^No changes'"
  if [ $(( ROUND % MISTAKE_MOD )) -eq "$MISTAKE_REM" ]; then
    narrate "(demo) a second run while the lock is held (terraform console holds it)"
    run_cmd "(sleep 25 | terraform console >/dev/null 2>&1 &) ; sleep 5"
    run_cmd "terraform plan -no-color -input=false -lock-timeout=0s 2>&1 | grep -E -i 'lock' | head -3"
    narrate "right -- Error acquiring the state lock. Waiting for the console to let go."
    run_cmd "sleep 22"
  fi
  # The change: the ntp service (main.tf in stage 7), reviewed in a pull request in the bot's own fork.
  local branch; branch="$(branch_name "srx-ntp")"
  run_cmd "git checkout -B '$branch'"
  run_cmd "terraform plan -no-color -input=false | tee plan.txt | grep -E '^Plan:'"
  run_cmd "git add -A"
  run_cmd "git commit -q -m 'Add an ntp service (round $ROUND)' && git push -q -f -u origin '$branch'"
  local body pr
  body="$(python3 -c '
import json, sys
f = chr(96) * 3
plan = open("plan.txt").read()
print(json.dumps({"head": sys.argv[1], "base": "main", "title": "[%s] Add an ntp service (round %s)" % (sys.argv[2], sys.argv[3]),
  "body": "Demo bot. Plan:\n\n" + f + "text\n" + plan + "\n" + f + "\n\nSafe to close."}))' "$branch" "$BOT_USER" "$ROUND")"
  pr="$(api_curl -X POST "$API/repos/$BOT_USER/$FORGEJO_REPO/pulls" -H 'Content-Type: application/json' -d "$body" \
        | grep -o '"number":[0-9]*' | head -1 | cut -d: -f2)"
  SRX_PR="$pr"
  narrate "opened PR #${pr:-none} in my own fork; the bot never merges, it closes it at the end of the round"
  run_cmd "terraform apply -auto-approve -no-color -input=false | tail -2"
  run_cmd "curl -s -u \"\$TF_HTTP_USERNAME:\$TF_HTTP_PASSWORD\" https://api.mist.com/dojo-state/srx-estate | python3 -c 'import json,sys; s=json.load(sys.stdin); print(\"serial\", s[\"serial\"], \"resources\", len(s[\"resources\"]))'"
  run_cmd "dojo check 7"
  return 0
}

# -- Lab 8 ---------------------------------------------------------------------
step_srx_drift() {
  cd "$REPO_DIR" || return 1
  [ "$SRX_HAS_WAN" = 1 ] || { narrate "Lab 8 -- no Dojo WAN login -- skipping"; return 0; }
  narrate "Lab 8 -- drift: a portal-style edit of the corp VLAN"
  local net
  net="$(srx_api https://api.mist.com/api/v1/orgs/$MIST_ORG_ID/networks | python3 -c 'import json,sys; print([n["id"] for n in json.load(sys.stdin) if n["name"]=="corp"][0])')"
  run_cmd "srx_api -X PUT -d '{\"vlan_id\": \"99\"}' https://api.mist.com/api/v1/orgs/$MIST_ORG_ID/networks/$net | python3 -m json.tool | grep vlan"
  run_cmd "dojo wan events | tail -3"
  run_cmd "terraform plan -no-color -input=false | grep -E 'vlan_id|^Plan:'"
  narrate "revert: the code wins"
  run_cmd "terraform apply -auto-approve -no-color -input=false | tail -2"
  run_cmd "terraform plan -no-color -input=false | grep -E '^Plan:|^No changes'"

  narrate "Lab 8 -- a network made by hand, then imported"
  run_cmd "srx_api -X POST -d '{\"name\": \"guest\", \"vlan_id\": \"20\", \"subnet\": \"172.16.20.0/24\"}' https://api.mist.com/api/v1/orgs/$MIST_ORG_ID/networks | python3 -m json.tool | grep '\"id\"'"
  run_cmd "srx_stage 8"
  run_cmd "terraform plan -no-color -input=false | grep -E '^Plan:'"
  narrate "right -- Terraform would create a second guest. Importing instead."
  local guest
  guest="$(srx_api https://api.mist.com/api/v1/orgs/$MIST_ORG_ID/networks | python3 -c 'import json,sys; print([n["id"] for n in json.load(sys.stdin) if n["name"]=="guest"][0])')"
  run_cmd "terraform import -no-color -input=false mist_org_network.guest \"$MIST_ORG_ID.$guest\" | tail -2"
  run_cmd "terraform plan -no-color -input=false | grep -E '^Plan:|^No changes'"

  narrate "Lab 8 -- import a device override: state rm, then import"
  local site dev
  site="$(terraform state show 'module.site["toronto-01"].mist_site.this' | awk '/^ *id /{print $3}' | tr -d '"')"
  dev="$(terraform state show 'module.gateway["toronto-01"].mist_device_gateway.this' | awk '/^ *device_id /{print $3}' | tr -d '"')"
  run_cmd "terraform state rm 'module.gateway[\"toronto-01\"].mist_device_gateway.this'"
  run_cmd "terraform plan -no-color -input=false | grep -E '^Plan:'"
  run_cmd "terraform import -no-color -input=false 'module.gateway[\"toronto-01\"].mist_device_gateway.this' \"$site.$dev\" | tail -2"
  run_cmd "terraform plan -no-color -input=false | grep -E '^Plan:|^No changes'"
  run_cmd "dojo check 8"
  return 0
}

# -- Lab 9 ---------------------------------------------------------------------
step_srx_capstone() {
  cd "$REPO_DIR" || return 1
  [ "$SRX_HAS_WAN" = 1 ] || { narrate "Lab 9 -- no Dojo WAN login -- skipping"; return 0; }
  narrate "Lab 9 -- ticket NET-142: open halifax-01 with one map entry"
  local hal branch
  hal="$(srx_code SRX345 2)"
  branch="$(branch_name "halifax")"
  run_cmd "git checkout -B '$branch'"
  run_cmd "python3 - <<PY
p = 'terraform.tfvars'
s = open(p).read().rstrip()
assert s.endswith('}')
entry = '''  \"halifax-01\" = {
    address      = \"Halifax, NS, Canada\"
    country_code = \"CA\"
    timezone     = \"America/Halifax\"
    claim_code   = \"$hal\"
    wan_ip       = \"198.51.100.10\"
    wan_gw       = \"198.51.100.9\"
    lan_subnet   = \"10.40.0.0/24\"
    lan_ip       = \"10.40.0.1\"
  }
'''
open(p, 'w').write(s[:-1] + entry + '}\\n')
PY"
  run_cmd "terraform fmt && terraform validate -no-color"
  run_cmd "terraform plan -no-color -input=false | tee plan.txt | grep -E '^Plan:'"
  run_cmd "git add terraform.tfvars && git commit -q -m 'Open halifax-01 (NET-142)' && git push -q -f -u origin '$branch'"
  run_cmd "terraform apply -auto-approve -no-color -input=false | tail -2"
  run_cmd "dojo wan config halifax-01-gw | grep -E 'host-name|name-server|ntp|address'"
  run_cmd "terraform plan -no-color -input=false | grep -E '^Plan:|^No changes'"
  run_cmd "dojo check 9"
  return 0
}

# -- End of every round: destroy what this round built and reset the clone --------
step_srx_cleanup() {
  cd "$REPO_DIR" || return 1
  [ "$SRX_HAS_WAN" = 1 ] || return 0
  narrate "clean up: destroy what this round built, close the demo pull requests, reset the clone"
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
