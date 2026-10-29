# Lab A10: Secrets with OpenBao (stretch)

Keep each team's Ansible vault password in its own OpenBao vault, so no password sits in a file.

The full walkthrough, with every command explained, is the lab page **Lab A10** in the lab reader (the lab index
in your portal). This folder is where you do the work.

- You fill in: `labs/5-vault/fw-repo/` and `sw-repo/` (`vault-pass.sh`, `secrets.yml`, `site.yml`)
- Work from `~/netlab`, on branch **a** (`*-a-@POD@`).
- Check your work: `dojo netlab check A10`
- Stuck or wrecked the firewall or web node? `ansible-playbook reset_fw.yml -e branch=a`
