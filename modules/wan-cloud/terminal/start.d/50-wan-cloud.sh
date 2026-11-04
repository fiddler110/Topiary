#!/bin/sh
# wan-cloud start.d hook, run by the base web-terminal entrypoint as root after
# every account exists. It never waits for wan-api: the terminal starts at once.
# It
#   1. starts a background loop that waits, with no time limit, for wan-api's CA
#      certificate and signing key (created when wan-api starts, which can be after
#      this container), adds the CA to the system trust store, then marks it done;
#   2. starts the credential broker, restarted if it dies (it waits for the key too).
# A shell captures its MIST_* values when it starts, so a shell opened before
# Dojo WAN was ready needs a new terminal tab.
set -eu

# The environment overrides exist only so the loop can be tested in a scratch directory.
CA=${WAN_HOOK_CA:-/run/wan-pki/ca.crt}
KEY=${WAN_HOOK_KEY:-/run/wan-secrets/signing.key}
MARK=${WAN_HOOK_MARK:-/run/wan-broker/ca-installed}
TRUST_DIR=${WAN_HOOK_TRUST_DIR:-/usr/local/share/ca-certificates}
NOTICE_AFTER=${WAN_HOOK_NOTICE_AFTER:-60}  # seconds
POLL=${WAN_HOOK_POLL:-1}                   # seconds

# A CA that is only half copied must not be installed, hence the END line.
wan_files_ready() {
  [ -s "$KEY" ] && [ -s "$CA" ] && grep -q -- '-----END CERTIFICATE-----' "$CA"
}

install_ca() {
  mkdir -p "$TRUST_DIR" "$(dirname "$MARK")" &&
    cp "$CA" "$TRUST_DIR/dojo-wan-ca.crt" &&
    chmod 0644 "$TRUST_DIR/dojo-wan-ca.crt" &&
    { [ -n "${WAN_HOOK_TRUST_DIR:-}" ] || update-ca-certificates >/dev/null; } &&
    : > "$MARK"
}

(
  waited=0
  until wan_files_ready; do
    waited=$((waited + 1))
    if [ "$waited" -eq "$NOTICE_AFTER" ]; then
      echo "wan-cloud: Dojo WAN not available yet; still waiting for it in the background." >&2
    fi
    sleep "$POLL"
  done
  install_ca || echo "wan-cloud: could not trust Dojo WAN's certificate; Terraform will not reach it." >&2
) &

# Restarted if it ever dies; a child of PID 1, reaped by workspace-control.py.
(
  while true; do
    /usr/bin/python3 /usr/local/lib/wan/wan-broker.py || true
    sleep 2
  done
) &
