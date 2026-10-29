# Lab A6: Idempotency and check mode

HTTPS with a self-signed certificate that is safe to run twice; preview with `--check --diff`.

The full walkthrough, with every command explained, is the lab page **Lab A6** in the lab reader (the lab index
in your portal). This folder is where you do the work.

- You fill in: `labs/3-idempotency/site.yml`, `tls.conf.j2`
- Work from `~/netlab`, on branch **a** (`*-a-@POD@`).
- Check your work: `dojo netlab check A6`
- Stuck or wrecked the firewall or web node? `ansible-playbook reset_fw.yml -e branch=a`
