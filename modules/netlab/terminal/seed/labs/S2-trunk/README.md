# Lab S2: Trunk and router-on-a-stick

Goal: make `pc` reach `web` again. After S1 the access ports are right but the switch's `to-fw` port carries nothing, so
nothing leaves the switch. The firewall already has its **802.1Q subinterfaces** (`10.10.10.1/24` for VLAN 10 and
`10.10.20.1/24` for VLAN 20); it is the router between the VLANs. You only have to carry both VLANs to it, tagged.

The starter `site.yml` is blank again.

## Target state

`to-fw` is a trunk carrying VLAN **10** and **20** tagged, and **no VLAN 1**. After S1 and S2, `pc` pings `web` again.

## Command reference

```sh
bridge vlan add dev to-fw vid 10           # no pvid, no untagged: frames keep their 802.1Q tag
bridge vlan add dev to-fw vid 20
bridge vlan del dev to-fw vid 1
ip -d link show                            # on fw: the 802.1Q subinterfaces ("vlan protocol 802.1Q id 10")
ip -o -4 addr show                         # on fw: 10.10.10.1/24 and 10.10.20.1/24
```

## 1. By hand, on branch m

```sh
ssh root@sw-m-@POD@        # make to-fw a trunk for 10 and 20
ssh root@fw-m-@POD@        # look at the subinterfaces; they should already be there
ssh root@pc-m-@POD@ ping -c 1 10.10.20.10
```

## 2. With a playbook, on branch a

Extend your S1 playbook (or copy it to `labs/S2-trunk/site.yml`). **One VLAN data structure drives both devices**: keep
the VLAN ids and gateway addresses in a single variable and use it in two plays, `sw:&auto` and `fw:&auto`.

- Switch: add `to-fw` to your port list with both VLANs and no PVID.
- Firewall: check from the same variable that each VLAN's gateway address is configured (`ip -o -4 addr show`), with an
  `assert` and a loop. If you would have to create one, the command is `ip link add link <parent> name <parent>.<vid> type vlan id <vid>`.
- Use `serial: 1` so a mistake stops on the first host, not all of them.

## HINTS

1. Your S1 guard compares a list of `{name, vids, pvid}`. A trunk is just an entry with `vids: [10, 20]` and `pvid: 0`;
   make the template add VLANs without `pvid untagged` when the VLAN is not the port's PVID.
2. For the firewall, a `loop` over the VLAN list with `ansible.builtin.assert` and `that: item.gateway in addrs.stdout`
   (where `addrs` is the registered output of `ip -o -4 addr show`) is enough. Do not match on interface names; they
   differ between container runtimes.

## 3. Prove it

```sh
ansible-playbook labs/S2-trunk/site.yml                              # changed on the switch
ansible-playbook labs/S2-trunk/site.yml                              # changed=0
ansible 'sw:&auto' -m ansible.builtin.command -a "bridge -j vlan show"
ansible-playbook probe.yml -e branch=a -e proto=icmp -e expect=allowed
ansible-playbook probe.yml -e branch=a -e expect=allowed             # HTTP also, if you opened it in lab 2
```

Done when `bridge -j vlan show` on `sw` has `to-fw` tagged for 10 and 20, no VLAN 1, and ping `pc` to `web` works.

## The twist

Add a third VLAN to the one variable (a new `vlans` entry and a new switch port or trunk member) and rerun: both the
switch and the firewall check follow it. A mistake on the first switch stops the run (`serial: 1`) before the rest.

Next lab: segmentation policy.
