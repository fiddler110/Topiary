# Ansible on a Small Network

You have a private practice network, your **pod**, with two identical copies:

- **Branch m (manual)**: you configure it by hand over SSH.
- **Branch a (automated)**: you write playbooks that must produce the same result.

Each pod is a pc, a VLAN switch, a Linux firewall and an nginx web server. Doing it by hand first shows what the playbook
has to say; `dojo netlab check A<n>` tells you whether each playbook lab met its goal, and the capstone's `compare.yml` shows whether the two branches agree.

Your workspace is `~/netlab` (start with `LAB-README.md` there). Each page in this reader is the whole lab: the steps, the
check and the usual traps.

**Part 1: by hand, on branch m.** Do each job yourself over SSH, so you know what it takes.

| Lab | Job | Time |
| --- | --- | ---- |
| [M1](labM1.md) | Look around the pod | ~10 min |
| [M2](labM2.md) | VLANs and access ports | ~10 min |
| [M3](labM3.md) | Trunk and router-on-a-stick | ~10 min |
| [M4](labM4.md) | Serve a web page | ~10 min |
| [M5](labM5.md) | Open HTTP and HTTPS | ~10 min |
| [M6](labM6.md) | HTTPS with a self-signed certificate | ~10 min |
| [M7](labM7.md) | Harden SSH | ~10 min |
| [M8](labM8.md) | Lock the server down (segmentation policy) | ~15 min |
| [M9](labM9.md) | Rebuild from clean | ~20 min |

**Part 2: as playbooks, on branch a.** Say the same jobs as desired state, run them, run them again, and check it.

| Lab | Topic | Time |
| --- | ----- | ---- |
| [A1](labA1.md) | Orientation: inventory, ad-hoc commands, facts | ~10 min |
| [A2](labA2.md) | VLANs and access ports, build it yourself | ~20 min |
| [A3](labA3.md) | Trunk and router-on-a-stick | ~20 min |
| [A4](labA4.md) | A first playbook: the web page | ~15 min |
| [A5](labA5.md) | Variables, loops, conditionals | ~15 min |
| [A6](labA6.md) | Idempotency and check mode: HTTPS | ~15 min |
| [A7](labA7.md) | Templates, handlers, validate: harden SSH | ~15 min |
| [A8](labA8.md) | Errors, rollback and tests: lock it down | ~20 min |
| [A9](labA9.md) | Capstone: from clean to done | ~20 min |
| [A10](labA10.md) | Secrets with OpenBao (stretch) | ~25 min |
| [A11](labA11.md) | Roles and structure (stretch) | ~20 min |

Do Part 1 first, then Part 2: lab A*n* repeats lab M*n* as a playbook (the stretch labs A10 and A11 have no by-hand twin). Start the switch labs with a working pod: they break the switch on purpose.

Handy commands, all from `~/netlab`:

```sh
ansible-playbook verify_topology.yml                 # is every node up and at baseline?
ansible-playbook probe.yml -e branch=a -e expect=blocked
ansible-playbook compare.yml                         # m and a agree (use it in the capstone, A9)
ansible-playbook reset_fw.yml -e branch=a            # back to the baseline
dojo netlab check A5                                 # the checker's verdict for lab A5
```
