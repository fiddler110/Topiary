# Lab 7: Roles and structure (stretch)

Goal: move labs 1 to 6 into two **roles**, `web` and `firewall`, called from one `site.yml`, with nothing changing on the
network: `compare.yml` still shows no difference and a second run is `changed=0`.

## 1. By hand, on branch m

Nothing new to type. Look at the five playbooks you have written and list what repeats (the hosts line, the reload handler,
`pc_net`) and which tasks belong to the web server and which to the firewall. That list is your role layout.

## 2. With a playbook, on branch a

Create the layout in `labs/7-roles/` (the starter has it with `TODO` files):

```text
roles/web/      defaults/main.yml  tasks/{main,page,tls,sshd}.yml  templates/  handlers/main.yml
roles/firewall/ defaults/main.yml  tasks/{main,ports,lockdown}.yml
site.yml        hosts: web:&auto -> role web;  hosts: fw:&auto -> role firewall
```

```sh
ansible-playbook labs/7-roles/site.yml
ansible-playbook labs/7-roles/site.yml --tags tls          # only the certificate and server block
ansible-playbook labs/7-roles/site.yml --list-tags
```

You will use `defaults/main.yml` (the lowest-precedence variables, so `group_vars` still wins), `import_tasks` (decided
when the playbook loads, tags apply) versus `include_tasks` (decided at run time), and `tags:`.
Lint it with `ansible-lint labs/7-roles/site.yml` (works offline; it reads `.ansible-lint` in your workspace).

## 3. Prove it

```sh
ansible-playbook reset_fw.yml -e branch=a && ansible-playbook labs/7-roles/site.yml    # builds the end state
ansible-playbook labs/7-roles/site.yml                    # changed=0
ansible-playbook compare.yml                              # empty: same as m
```

## The twist

Change a default (`sshd_max_auth_tries`) in `roles/web/defaults/main.yml` and then override it for one host in `host_vars`.
You changed behaviour in one place and left the role untouched, which is the reason roles exist.

Next lab: `labs/8-capstone/README.md`.
