# Lab A7: Templates, handlers and validate

Harden `sshd` with a template that is tested (`validate:`) before it goes live.

The full walkthrough, with every command explained, is the lab page **Lab A7** in the lab reader (the lab index
in your portal). This folder is where you do the work.

- You fill in: `labs/4-templates-validate/site.yml`, `sshd_config.j2`, `group_vars/web.yml`
- Work from `~/netlab`, on branch **a** (`*-a-@POD@`).
- Check your work: `dojo netlab check A7`
- Stuck or wrecked the firewall or web node? `ansible-playbook reset_fw.yml -e branch=a`
