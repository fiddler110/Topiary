# Lab 0: Orientation

Goal: find out what is on each node by hand, then learn the same things with Ansible.

## 1. By hand, on branch m

```sh
cat ~/.config/dojo/netlab-password
ssh root@fw-m-@POD@
```

On the firewall, answer: what addresses does it have (`ip addr`), what are its firewall rules (`iptables -S`),
and is it forwarding (`cat /proc/sys/net/ipv4/ip_forward`)? Do the same on `web-m-@POD@` (`nginx -v`, `ss -ltn`).

That is one question on one node. You have eight nodes and two branches.

## 2. With Ansible, on branch a

Look at what Ansible knows, then ask every node at once:

```sh
cd ~/netlab
ansible-inventory --graph
ansible all -m ansible.builtin.ping
ansible fw -m ansible.builtin.command -a "iptables -S"
ansible auto -m ansible.builtin.setup -a "filter=ansible_default_ipv4"
ansible-doc ansible.builtin.ping
```

- `hosts.ini` groups the nodes by branch (`manual`, `auto`) and by job (`pc`, `sw`, `fw`, `web`).
- `-m` picks a module, `-a` gives it arguments, and the first word is a **host pattern**: `fw`, `auto`, `fw:&auto`.

## 3. Prove it

1. `ansible fw:&auto -m ansible.builtin.command -a "ip addr"` shows the same addresses you found on `fw-m-@POD@` by hand.
2. `ansible-playbook probe.yml -e branch=a -e proto=icmp -e expect=allowed` should print PASS: pings are allowed at the start.
3. `ansible-playbook probe.yml -e branch=a -e expect=blocked` should print PASS too: HTTP is blocked at the start.

## The twist

Which ad-hoc command lists the nginx version on **both** web servers in one go? (`web` is a group, and `-m command`
takes `nginx -v`.) Notice it prints to stderr: look at the `stderr` line of the result.

Next: `labs/1-first-playbook/README.md`.
