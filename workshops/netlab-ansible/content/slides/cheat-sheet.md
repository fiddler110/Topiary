---
marp: true
theme: default
paginate: true
size: 16:9
html: true
style: |
  @import url('assets/themes/cheat-sheet.css');
footer: '[&larr; Hub](index.md) &nbsp;|&nbsp; Ansible on a Small Network | Cheat Sheet'
---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: "[&larr; Hub](index.md)" -->

# Cheat Sheet

## The commands you will use, in one place

Run them from `~/netlab`. Keep this open in another tab.

---

## Ansible

| Task | Command |
| ---- | ------- |
| Show the inventory | `ansible-inventory --graph` |
| Ping every node | `ansible all -m ansible.builtin.ping` |
| One ad-hoc command | `ansible 'fw:&auto' -m ansible.builtin.command -a "iptables -S"` |
| Module help | `ansible-doc ansible.builtin.template` |
| Run a playbook | `ansible-playbook labs/2-variables-loops/site.yml` |
| Dry run with a diff | `ansible-playbook site.yml --check --diff` |
| One tag or host | `--tags web`, `--limit web-a-07` |

Host patterns: `fw` (a group), `auto` (branch a), `fw:&auto` (both).

---

## Your pod

| Task | Command |
| ---- | ------- |
| Is the pod up? | `ansible-playbook verify_topology.yml` |
| Prove a result | `ansible-playbook probe.yml -e branch=a -e expect=allowed` |
| Do m and a agree? | `ansible-playbook compare.yml` |
| Back to the baseline | `ansible-playbook reset_fw.yml -e branch=a` |
| Log in by hand | `ssh root@fw-m-07` (password: `~/.config/dojo/netlab-password`) |
| Ask the checker | `dojo netlab check 2` |

---

## Hand-built tools on the nodes

```sh
iptables -S LAB                  # the rules you own
bridge vlan show                 # the switch's VLAN table
nginx -t && nginx -s reload      # check, then reload
sshd -t                          # check sshd_config before reloading
```
