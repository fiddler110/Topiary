# srx-terraform's own layer on the terminal image chain (:base -> lab-prep -> wan-cloud -> sensei -> this).
# Terraform, the provider mirror and the Dojo WAN login come from the wan-cloud module. This adds
#   dojo prep   catch up to a lab (lab-prep, sourcing the lab-prep module's library)
#   dojo check  per-lab checks against the Dojo WAN API (srx-check)
# ENTRYPOINT is inherited unchanged. No new tools.
ARG BASE=topiary/web-terminal:base
FROM ${BASE}

COPY lab-prep /usr/local/bin/lab-prep
COPY srx-check /usr/local/bin/srx-check
RUN set -eux; \
    chmod 0755 /usr/local/bin/lab-prep /usr/local/bin/srx-check; \
    mkdir -p /usr/local/share/dojo/cmd.d; \
    ln -sf /usr/local/bin/srx-check /usr/local/share/dojo/cmd.d/check

# Base image's HEALTHCHECK is inherited; restated so a static scan of this file alone doesn't flag it.
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD web-terminal-healthcheck
