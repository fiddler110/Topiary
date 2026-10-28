# Netlab: learn Ansible on a small network

Your pod is number **@POD@**. It has two copies of the same network, which start identical:

| Branch | You configure it | Nodes |
|---|---|---|
| **m** (manual) | by hand, over SSH | `pc-m-@POD@` `sw-m-@POD@` `fw-m-@POD@` `web-m-@POD@` |
| **a** (automated) | with playbooks | `pc-a-@POD@` `sw-a-@POD@` `fw-a-@POD@` `web-a-@POD@` |

```text
pc (VLAN 10) -- sw -- web (VLAN 20)          the switch's trunk goes to fw, the only path between the VLANs
```

Each lab: do it **by hand on m**, write the **playbook for a**, then prove both with `probe.yml` and `compare.yml`.

- Log in to a node by hand: `ssh root@fw-m-@POD@`. The password is in `~/.config/dojo/netlab-password`.
- Ansible already knows the login (`group_vars/all.yml`), so playbooks need no password.
- Is everything up? `ansible-playbook verify_topology.yml`
- Stuck, or locked yourself out of the data plane? `ansible-playbook reset_fw.yml -e branch=a`

Start with `labs/0-orientation/README.md`.
