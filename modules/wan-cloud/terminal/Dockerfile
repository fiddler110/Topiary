# wan-cloud's link in the terminal build chain (dojo sets BASE to the image
# below this one).
#
# HashiCorp Terraform (pinned, sha256-verified per architecture), an offline
# mirror of the Juniper/mist provider, and Dojo WAN's client side: a root-owned
# credential broker (SO_PEERCRED tells it which student is asking), the
# `wan-env` client, a start.d hook that trusts the simulated Mist API's CA and
# starts the broker, and the `dojo wan` command. Without a running wan-api the
# credential parts quietly do nothing, so the rest of the lab still works.
# Terraform, not OpenTofu: there is no tofu and no terraform->tofu link here.
ARG BASE=topiary/web-terminal:base
FROM ${BASE}
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG TERRAFORM_VERSION=1.17.1
# TARGETARCH is set by BuildKit (amd64/arm64). Checksums from
# https://releases.hashicorp.com/terraform/1.17.1/terraform_1.17.1_SHA256SUMS.
ARG TARGETARCH=amd64
RUN set -eux; \
    case "${TARGETARCH}" in \
    amd64) tf_arch="amd64"; tf_sha256="4638628058e71a55212b1c563712eac03b902128f40740f3dc8174df12135061" ;; \
    arm64) tf_arch="arm64"; tf_sha256="988e950a1c23058093b0e66ab2d5fb53fc18345ecfbd5871acf51dbac9325edd" ;; \
    *) echo "Unsupported architecture for Terraform: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    wget -O /tmp/terraform.zip \
      "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_${tf_arch}.zip"; \
    echo "${tf_sha256}  /tmp/terraform.zip" | sha256sum -c -; \
    python3 -c "import zipfile; zipfile.ZipFile('/tmp/terraform.zip').extract('terraform', '/tmp')"; \
    install -m 0755 /tmp/terraform /usr/local/bin/terraform; \
    rm -f /tmp/terraform.zip /tmp/terraform; \
    terraform version

# Offline provider mirror (same method as tofu-basics): downloaded once at
# build time, verified by Terraform against the registry's signed hashes, then
# unpacked so `terraform init` symlinks the 96 MB provider into each student's
# folder instead of copying it per student.
COPY mirror.tf /tmp/mirror/mirror.tf
COPY unpack-mirror.py /tmp/unpack-mirror.py
RUN set -eux; \
    cd /tmp/mirror; \
    terraform providers mirror -platform="linux_${TARGETARCH}" /tmp/mirror/packed; \
    python3 /tmp/unpack-mirror.py /tmp/mirror/packed /opt/terraform-providers; \
    rm -rf /tmp/mirror /tmp/unpack-mirror.py; \
    chmod -R a+rX /opt/terraform-providers

COPY terraformrc /etc/terraform/terraformrc
# Students run `su - <name>` (a login shell that drops the container's ENV), so
# the CLI-config variable is exported from /etc/zsh/zshenv: zsh reads it for
# every shell. Root-owned, so students cannot repoint or edit it.
RUN set -eux; \
    chmod 0644 /etc/terraform/terraformrc; \
    printf '\n# wan-cloud: use the offline provider mirror (see /etc/terraform/terraformrc)\nexport TF_CLI_CONFIG_FILE=/etc/terraform/terraformrc\n' >> /etc/zsh/zshenv; \
    printf 'export TF_CLI_CONFIG_FILE=/etc/terraform/terraformrc\n' > /etc/profile.d/terraform.sh
ENV TF_CLI_CONFIG_FILE=/etc/terraform/terraformrc

# HCL syntax highlighting for .tf / .tfvars in code-server: the same pinned,
# sha256-verified OpenTofu extension tofu-basics uses (it highlights Terraform
# files too), with its language server switched off by default. Skipped on the
# Zellij flavor, which has no code-server.
ARG OPENTOFU_VSCODE_VERSION=0.6.3
COPY disable-tofu-ls.py /tmp/disable-tofu-ls.py
RUN set -eux; \
    if command -v code-server >/dev/null 2>&1; then \
      case "${TARGETARCH}" in \
      amd64) ext_target="linux-x64"; ext_sha256="ed0cbd5b8869b7adcc5f1d8fcec5ce573b9e46f4e57ecc66c3d535763a3a85fd" ;; \
      arm64) ext_target="linux-arm64"; ext_sha256="94755ee6cd3bd4e90c6c05768f952ed272152e4eb4f836d37d97a612a68045d2" ;; \
      *) echo "Unsupported architecture for the OpenTofu extension: ${TARGETARCH}" >&2; exit 1 ;; \
      esac; \
      wget -O /tmp/opentofu.vsix \
        "https://open-vsx.org/api/OpenTofu/vscode-opentofu/${ext_target}/${OPENTOFU_VSCODE_VERSION}/file/OpenTofu.vscode-opentofu-${OPENTOFU_VSCODE_VERSION}@${ext_target}.vsix"; \
      echo "${ext_sha256}  /tmp/opentofu.vsix" | sha256sum -c -; \
      code-server --extensions-dir /opt/code-server-extensions --install-extension /tmp/opentofu.vsix --force; \
      rm -f /tmp/opentofu.vsix; \
      python3 /tmp/disable-tofu-ls.py /opt/code-server-extensions; \
      chown -R root:root /opt/code-server-extensions; \
      chmod -R a+rX /opt/code-server-extensions; \
    fi; \
    rm -f /tmp/disable-tofu-ls.py

# Dojo WAN client side.
COPY wan_ids.py wan-broker.py /usr/local/lib/wan/
COPY wan-env /usr/local/bin/wan-env
COPY start.d/50-wan-cloud.sh /etc/dojo/start.d/50-wan-cloud.sh
COPY cmd.d/wan /usr/local/share/dojo/cmd.d/wan
RUN set -eux; \
    chmod 0644 /usr/local/lib/wan/wan_ids.py; \
    chmod 0755 /usr/local/lib/wan/wan-broker.py /usr/local/bin/wan-env /usr/local/share/dojo/cmd.d/wan; \
    printf '\n# wan-cloud: Dojo WAN credentials for this user (from the broker)\nif [ -z "${MIST_API_TOKEN:-}" ] && [ -x /usr/local/bin/wan-env ]; then eval "$(/usr/local/bin/wan-env 2>/dev/null)"; fi\n' >> /etc/zsh/zshenv

# ENTRYPOINT and HEALTHCHECK are inherited from the base image; the
# HEALTHCHECK is restated so a static scan of this file alone doesn't flag it missing.
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD web-terminal-healthcheck
