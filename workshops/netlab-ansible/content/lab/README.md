# Ansible on a Small Network

You have a private practice network, your **pod**, with two identical copies:

- **Branch m (manual)**: you configure it by hand over SSH.
- **Branch a (automated)**: you write playbooks that must produce the same result.

Each pod is a pc, a VLAN switch, a Linux firewall and an nginx web server. Doing it by hand first shows what the playbook
has to say; `compare.yml` and `dojo netlab check` then tell you whether the two branches agree and the goal is met.

Your workspace is `~/netlab` (start with `LAB-README.md` there). Each lab's full text is `~/netlab/labs/<lab>/README.md`;
the pages in this reader give the goal, the check command and the usual traps.

| Lab | Topic | Time | Path |
| --- | ----- | ---- | ---- |
| [0](lab0.md) | Orientation: inventory, ad-hoc commands, facts | ~10 min | core |
| [1](lab1.md) | A first playbook: the web page | ~15 min | core |
| [2](lab2.md) | Variables, loops, conditionals: open HTTP and HTTPS | ~20 min | core |
| [3](lab3.md) | Idempotency and check mode: HTTPS | ~20 min | core |
| [4](lab4.md) | Templates, handlers, validate: harden SSH | ~20 min | core |
| [5](lab5.md) | Secrets with Vault | ~15 min | stretch |
| [6](lab6.md) | Errors, rollback and tests: lock it down | ~20 min | core |
| [7](lab7.md) | Roles and structure | ~15 min | stretch |
| [8](lab8.md) | Capstone: from clean to done | ~15 min | core |
| [S1](labS1.md) | VLANs and access ports (build it yourself) | ~25 min | stretch |
| [S2](labS2.md) | Trunk and router-on-a-stick | ~25 min | stretch |
| [S3](labS3.md) | Segmentation policy | ~20 min | stretch |

Do the core labs in order. Start the S labs only after lab 8 (they break the switch on purpose and undo your firewall work).

Handy commands, all from `~/netlab`:

```sh
ansible-playbook verify_topology.yml                 # is every node up and at baseline?
ansible-playbook probe.yml -e branch=a -e expect=blocked
ansible-playbook compare.yml                         # empty diff: m and a agree
ansible-playbook reset_fw.yml -e branch=a            # back to the baseline
dojo netlab check 2                                  # the checker's verdict for lab 2
```
