---
marp: true
theme: default
paginate: true
size: 16:9
html: true
style: |
  @import url('assets/themes/presentation.css');
footer: '[&larr; Hub](index.md) &nbsp;|&nbsp; Ansible on a Small Network | Engineering & IT Operations'
---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: "[&larr; Hub](index.md)" -->

# Ansible on a Small Network

## Do it by hand once. Then say it in a playbook.

**Talk + hands-on lab**

<!-- Assumes the room can use a shell and ssh. No Ansible experience needed. The firewall is only the thing being configured; the lesson is Ansible. -->

---

## Today

1. Why configuration by hand does not scale
2. What Ansible is: inventory, modules, playbooks
3. Your pod: a pc, a switch, a firewall, a web server, twice
4. Each lab: by hand on branch m, by playbook on branch a, then prove it
5. Hands-on practice

> Same result two ways. The second way is the one you can repeat.

---

<!-- _class: section-title -->

# Part 1

## Why automate

---

## By hand, it works once

- You type the right commands on one box
- Next week, on a second box, you forget one
- Nobody can say what changed, or undo it
- A typo in `sshd_config` locks you out

> The server remembers what you did. Nobody else does.

---

## What Ansible gives you

- **Describe the state you want**, not the steps
- **Idempotent**: run it twice, the second run changes nothing
- **Check first**: `--check --diff` shows what would change
- **Many hosts at once**, over plain SSH, nothing to install on them
- **Readable**: the playbook is the documentation

---

## Three words to know

```yaml
# inventory: who
[fw]
fw-a-07

# play: which hosts, which tasks
- hosts: fw
  tasks:
    # task: one module call, with arguments
    - name: Allow HTTPS
      ansible.builtin.iptables:
        chain: LAB
        protocol: tcp
        destination_port: "443"
        jump: ACCEPT
```

---

<!-- _class: section-title -->

# Part 2

## Your pod

---

## One pod per student

```text
pc (VLAN 10) -- sw -- web (VLAN 20)
                 |
               trunk
                 |
                fw   the only path between the VLANs
```

- Four nodes, **twice**: branch **m** (by hand) and branch **a** (playbooks)
- Internal networks only: no internet, and you cannot reach anyone else's pod
- Log in with `ssh root@fw-m-07`; Ansible already knows the password

---

## Manual branch, automated branch

| | Branch m | Branch a |
| --- | --- | --- |
| You use | `ssh` and a shell | `ansible-playbook` |
| Starts | closed: ping only | closed: ping only |
| Proof | `probe.yml` | `probe.yml` |
| End | `compare.yml` shows no difference | `dojo netlab check` passes |

Both start identical. A correct playbook ends where your hand-built branch ended.

---

## Every lab has the same four parts

1. **By hand on m**: the README states the goal, not the commands
2. **By playbook on a**: write the same thing as tasks
3. **Prove it**: `probe.yml` for traffic, `compare.yml` for "m equals a"
4. **The twist**: run it again, undo it, change one value, and see the playbook win

```sh
ansible-playbook compare.yml
dojo netlab check 2
```

---

## The path

| Core path | Stretch |
| --------- | ------- |
| 0 Orientation | 5 Secrets with Vault |
| 1 A first playbook | 7 Roles |
| 2 Variables and loops | S1 VLANs, build it yourself |
| 3 Idempotency | S2 Trunk |
| 4 Templates and validate | S3 Segmentation |
| 6 Errors and rollback | |
| 8 Capstone | |

---

## Labs 1 to 4: guided

- **1** `template` and a handler: a page with your name
- **2** `loop` and a variable: open 80 and 443 with the `iptables` module
- **3** `--check --diff`, `creates:`, `changed_when`: HTTPS, and `changed=0` on the rerun
- **4** `template` with `validate:`: harden `sshd` without locking yourself out

Tip: run every playbook twice. The second run should say `changed=0`.

---

## Labs 6 and 8: safe and repeatable

- **6** `block / rescue / always`, `assert`, `retries`: lock the server down, test it, roll back on failure
- **8** `reset_fw.yml`, then one `site.yml`: rebuild branch a from the baseline, then run it again

> A lockdown that tests itself and undoes itself is the point.

---

## Stretch: no module for that

- **5** `ansible-vault`: a password in git, encrypted, never in the output
- **7** Roles: the same behaviour, better structure
- **S1 to S3** The switch: no module and no starter file. You design the data model, the template and the idempotency guard.

Different problem, same skills.

---

## If you get stuck

- `ansible-playbook verify_topology.yml`: is the pod healthy?
- `ansible-playbook reset_fw.yml -e branch=a`: back to the baseline
- `dojo netlab check N`: what is still wrong, line by line
- Put your hand up: the facilitator has a pod of their own

---

## Let's go

1. Open `lab-index.md` and the Lab 0 page
2. Work in `~/netlab` in your terminal
3. Core path first. Stretch labs only after lab 8

<!-- Suggested timing is in FACILITATOR.md. -->
