# Lab S1: VLANs and access ports

Labs 0 to 8 ran with the switch already working. This lab and the next two are different: **there is no Ansible module
for this switch and no starter playbook.** `site.yml` here is an empty file. You design the data model, the template and
the idempotency check yourself.

Start by breaking it. This puts the switch of branch m and a into a blank state (every port in VLAN 1, no VLAN 10 or 20),
so `pc` can no longer reach `web`. (The `reset_fw.yml` first clears the lockdown from lab 6, which would block ping and
HTTP for a different reason and hide what the switch is doing; it also undoes your firewall work from labs 1-8.)

```sh
cd ~/netlab
ansible-playbook reset_fw.yml                           # firewalls and web servers back to the baseline (ping allowed, LAB empty)
ansible-playbook reset_switch.yml                       # both branches
ansible-playbook probe.yml -e branch=a -e proto=icmp -e expect=blocked    # PASS: the switch is blank
```

(`reset_switch.yml -e restore=true` puts the working configuration back if you want to start over.)

## Goal and target state

Access ports: `to-pc` is VLAN **10**, `to-web` is VLAN **20**, untagged, and VLAN 1 is gone from them. The `to-fw` trunk is
lab S2, leave it alone for now. The switch has a bridge `br0` with VLAN filtering; each port is a bridge port.

## Command reference (iproute2, runs on the switch as root)

```sh
bridge vlan show                          # the VLAN table, one block per port
bridge -j vlan show                       # the same as JSON: [{"ifname":"to-pc","vlans":[{"vlan":10,"flags":["PVID","Egress Untagged"]}]}]
bridge vlan add dev to-pc vid 10 pvid untagged   # access port: frames leave untagged, untagged frames enter VLAN 10
bridge vlan del dev to-pc vid 1
ip -br link                               # the ports are named to-pc, to-web, to-fw
```

## 1. By hand, on branch m

```sh
ssh root@sw-m-@POD@
bridge vlan show
# make to-pc an access port in VLAN 10 and to-web one in VLAN 20; remove VLAN 1 from both
```

Nothing reaches the other side yet: the trunk is not done. Notice what you typed twice, and what happens if you type it a
second time (`bridge vlan add` of an existing VLAN is fine; `bridge vlan del` of a missing one is an error).

## 2. With a playbook, on branch a

Write `labs/S1-vlans/site.yml` yourself, for `hosts: sw:&auto`. Things you will need to decide:

- **Data model.** Put the ports and VLANs in a variable (for example a list in `group_vars/sw.yml`), not in the tasks.
- **Template.** Render a small script, or a list of commands, from that variable with `ansible.builtin.template`.
- **Guard.** Run `bridge -j vlan show`, parse it with `from_json`, and only apply when the table differs from what you want.
- **Apply.** `ansible.builtin.command` (or `shell`) with `changed_when` so a rerun says `changed=0`.

## HINTS

1. The shape of `bridge -j vlan show` is a list of ports, each with a `vlans` list of `{vlan, flags}`. Register it with
   `register: bvlan` and read it with `bvlan.stdout | from_json`. Compare **the same shape** on both sides: build the wanted
   list of `{name, vids, pvid}` from your variable and the current one from the JSON, then compare with `==`.
2. A rerun-safe apply: template a script that, per port, deletes VLAN 1 and the VLANs you manage (`|| true` so a missing
   one is not an error) and then adds the wanted ones; run it only `when:` the comparison says they differ.

## 3. Prove it

```sh
ansible-playbook labs/S1-vlans/site.yml                 # changed
ansible-playbook labs/S1-vlans/site.yml                 # changed=0
ansible 'sw:&auto' -m ansible.builtin.command -a "bridge vlan show"
ansible-playbook probe.yml -e branch=a -e proto=icmp -e expect=blocked    # still blocked: no trunk yet (S2)
```

Done when `to-pc` has VLAN 10 as PVID (untagged), `to-web` has VLAN 20 as PVID (untagged), and neither has VLAN 1.

## The twist

Change one value (a VLAN id) in your variable and rerun: only the affected commands change, and nothing else. Then add a
fourth port to the list. By hand that is one more session; here it is one more line. Facilitators have a reference in
`solutions/S1-vlans`.

Next lab: the trunk.
