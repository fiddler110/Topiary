# netlab module's link in the terminal build chain (dojo sets BASE to the image below this one).
# Adds Ansible, pinned and hash-verified (requirements.txt, amd64 and arm64 wheels): student terminals have no
# internet. The seed hook writes each account's pod password and ~/netlab.
ARG BASE=gitopsdojo/web-terminal:base
FROM ${BASE}
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

COPY requirements.txt /tmp/netlab-requirements.txt
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends python3-pip python3-venv sshpass openssh-client; \
    rm -rf /var/lib/apt/lists/*; \
    python3 -m venv /opt/ansible; \
    /opt/ansible/bin/pip install --no-cache-dir --require-hashes -r /tmp/netlab-requirements.txt; \
    for t in ansible ansible-playbook ansible-inventory ansible-doc ansible-vault ansible-config; do \
      ln -s "/opt/ansible/bin/$t" "/usr/local/bin/$t"; done; \
    printf '#!/bin/sh\nPATH=/opt/ansible/bin:$PATH\nexport PATH\nexec /opt/ansible/bin/ansible-lint "$@"\n' > /usr/local/bin/ansible-lint; \
    chmod 0755 /usr/local/bin/ansible-lint; \
    rm -f /tmp/netlab-requirements.txt

COPY seed/ /usr/local/share/netlab/seed/
COPY netlab-seed.sh /usr/local/lib/netlab/seed.sh
COPY start.d/50-netlab.sh /etc/dojo/start.d/50-netlab.sh
COPY account.d/57-netlab.sh /etc/dojo/account.d/57-netlab.sh
COPY cmd.d/netlab /usr/local/share/dojo/cmd.d/netlab
RUN chmod 0755 /usr/local/share/dojo/cmd.d/netlab /usr/local/lib/netlab/seed.sh /etc/dojo/start.d/50-netlab.sh /etc/dojo/account.d/57-netlab.sh
