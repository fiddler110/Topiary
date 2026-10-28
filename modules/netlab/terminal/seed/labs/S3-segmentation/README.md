# Lab S3: Segmentation policy

Goal: the firewall is now the only path between the VLANs, so it can decide who talks to whom. VLAN 10 (`pc`) may reach the
web server in VLAN 20 **only on tcp 80 and 443**. Everything else from VLAN 10 to VLAN 20, including ping, is dropped.
S1 and S2 must be done first. The starter `site.yml` is blank.

## Target state

On `fw`, in the `LAB` chain: accept tcp 80 and 443 from `10.10.10.0/24` to `10.10.20.10`, then drop all other traffic from
`10.10.10.0/24` to `10.10.20.0/24`. Match by **address**, not by interface name. (The baseline's ICMP allow sits *after* the
`LAB` chain in `FORWARD`, so your drop wins and ping stops working. That is the point.)

## Command reference

```sh
iptables -S LAB                                            # your rules
iptables -A LAB -p tcp -s 10.10.10.0/24 -d 10.10.20.10 --dport 80 -j ACCEPT
iptables -A LAB -s 10.10.10.0/24 -d 10.10.20.0/24 -j DROP  # last: rules are checked in order
curl -s -m 3 -o /dev/null -w '%{http_code}\n' http://10.10.20.10:8080/   # a drop times out (curl exit 28)
```

## 1. By hand, on branch m

```sh
ssh root@fw-m-@POD@        # add the rules, in the right order
ssh root@pc-m-@POD@        # test 80, 443, another port, and ping
```

## 2. With a playbook, on branch a

Write `labs/S3-segmentation/site.yml` yourself for `hosts: fw:&auto`, with the policy in a variable (source net,
destination, allowed ports). It should:

- **assert** first that the trunk is in place (read the switch's table with `bridge -j vlan show`, **`delegate_to`** the
  switch, `run_once: true`), because there is no point filtering a path that does not exist;
- apply the rules inside a **`block`**, using `ansible.builtin.iptables` (a `loop` over the allowed ports, then the drop);
- test from the `pc` (`delegate_to`, `run_once`): an allowed port works, another port and ping do not;
- in **`rescue`**, flush the `LAB` chain again and `fail` with a clear message, so a wrong policy is never left in place.

## HINTS

1. Order matters: the ACCEPT rules go in first and the DROP last. `ansible.builtin.iptables` with `action: append` is
   idempotent per rule, so a rerun changes nothing. Add a `comment:` to each rule so `iptables -S` reads well.
2. Tests are tasks with `changed_when: false`. For "must be blocked", make the task fail when curl **succeeds**, and
   check the exit code is 28 (a timeout, so a drop) rather than 7 (refused, so not filtered at all).

## 3. Prove it

```sh
ansible-playbook labs/S3-segmentation/site.yml                       # changed
ansible-playbook labs/S3-segmentation/site.yml                       # changed=0
ansible-playbook probe.yml -e branch=a -e expect=allowed             # 80
ansible-playbook probe.yml -e branch=a -e proto=icmp -e expect=blocked
ansible-playbook compare.yml                                         # m and a agree
```

## The twist

Break S2 on purpose (`reset_switch.yml -e branch=a`) and rerun this playbook: the assert stops it before touching the
firewall. Then restore (`-e restore=true`) and rerun. Make the allowed port list one entry longer and watch only one rule
change. Facilitators have a reference in `solutions/S3-segmentation`.
