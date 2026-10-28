# Lab 2: Variables, loops and conditionals, open HTTP and HTTPS

Goal: let the pc reach the web server on TCP 80 and 443, and nothing else new. Pings stay allowed; every other port stays blocked.

## 1. By hand, on branch m

On `fw-m-@POD@`, add rules to the **`LAB`** chain (the baseline sends every forwarded packet through it before the ICMP rule).
Allow TCP 80 and 443 from the pc network `10.10.10.0/24` to the web server `10.10.20.10`.
Match by **address**, never by interface name: the names differ between nodes. Look at your work with `iptables -S LAB`.

## 2. With a playbook, on branch a

Fill in `labs/2-variables-loops/site.yml`, then run it from `~/netlab`:

```sh
ansible-playbook labs/2-variables-loops/site.yml
```

You will use:

- a **list variable** `allowed_ports`, moved from the play into `group_vars/fw.yml` once it works
- `loop:` to make one rule per port, and `when:` to skip the task if the list is empty
- `ansible.builtin.iptables`, which checks before it adds, so a rerun does nothing
- **precedence**: `-e allowed_ports='[80]'` on the command line beats `group_vars`

## 3. Prove it

```sh
ansible-playbook labs/2-variables-loops/site.yml          # changed=2
ansible-playbook labs/2-variables-loops/site.yml          # changed=0
ansible-playbook probe.yml -e branch=a -e expect=allowed                 # port 80
ansible-playbook probe.yml -e branch=a -e port=443 -e expect=allowed
ansible-playbook probe.yml -e branch=a -e port=8080 -e expect=blocked
ansible-playbook compare.yml                              # firewall rules match m
```

Port 443 has no listener yet (lab 3 adds one), so use the rule listing to check it: `ansible 'fw:&auto' -m ansible.builtin.command -a "iptables -S LAB"`.

## The twist

Add a third port to `allowed_ports` (say 8080), rerun: only one task item reports `changed`. Remove it from the list and
rerun: nothing is removed, because the module only adds. Open question for the class: how would you make the list the
whole truth? (Lab 6 flushes first.)

Next lab: `labs/3-idempotency/README.md`.
