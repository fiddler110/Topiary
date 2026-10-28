# Lab 4: Templates, handlers and validate, harden SSH safely

Goal: the web servers' `sshd` allows only 3 authentication tries (`MaxAuthTries 3`), gives 20 seconds to log in
(`LoginGraceTime 20`) and refuses X11 forwarding (`X11Forwarding no`) while still taking a root password login.

## 1. By hand, on branch m

On `web-m-@POD@` edit `/etc/ssh/sshd_config` to set those three values. Keep `Port 22`, `PermitRootLogin yes`,
`PasswordAuthentication yes` and `Subsystem sftp internal-sftp`. Check with `sshd -T | grep -Ei 'maxauthtries|logingracetime|x11forwarding'`.

The twist waits here: run `sshd -t` **before** you reload. A typo (try `MaxAuthTries three`) that you load anyway
makes `sshd` die on the next SIGHUP, and you lose the node until it restarts at baseline. Do not skip `sshd -t`.

## 2. With a playbook, on branch a

Fill in `labs/4-templates-validate/site.yml` and `sshd_config.j2`, and create `group_vars/web.yml` holding the three values:

```sh
ansible-playbook labs/4-templates-validate/site.yml
```

You will use:

- `ansible.builtin.template` with **`validate: 'sshd -t -f %s'`**: Ansible checks the new file before it replaces the real one
- a **handler** that reloads `sshd` only when the file changed
- **group variables** (`group_vars/web.yml`), so the numbers live apart from the template

## 3. Prove it

```sh
ansible-playbook labs/4-templates-validate/site.yml       # changed
ansible-playbook labs/4-templates-validate/site.yml       # changed=0
ansible 'web:&auto' -m ansible.builtin.command -a "sshd -T"   # the three values
ansible all -m ansible.builtin.ping                       # you can still log in
```

## The twist

Put a typo in `group_vars/web.yml` (`sshd_max_auth_tries: three`) and rerun. `validate` fails the task, the real
`sshd_config` is untouched and `sshd` keeps running. Fix the value and rerun. That same typo by hand, loaded, costs you the node.

Next lab: `labs/5-vault/README.md` (stretch) or skip to `labs/6-lockdown/README.md`.
