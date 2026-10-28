# Lab 6: Errors, rollback and tests, lock it down

Goal: only TCP 80 and 443 from the pc to the web server get through. Everything else, **including ping**, is dropped.

## 1. By hand, on branch m

On `fw-m-@POD@`, in the `LAB` chain: keep the two allow rules from lab 2, then drop ICMP, then end the chain with a rule that
drops everything left. Order matters: `LAB` is read top to bottom and the baseline's ICMP allow comes **after** it.
Check from the pc: the page loads, ping and port 8080 fail.

Now do the painful part. Break the page (`> /var/www/html/index.html` on the web node, or stop nginx) and try to remember
the exact rules you typed to undo the lockdown. That scramble is what the playbook replaces.

## 2. With a playbook, on branch a

Fill in `labs/6-lockdown/site.yml`:

```sh
ansible-playbook labs/6-lockdown/site.yml
```

You will use:

- **`block` / `rescue` / `always`**: apply the rules in a block, and on any failure `rescue` flushes `LAB` and **fails loudly**
- tests from the pc: `ansible.builtin.uri` (80 and 443 must return 200, with `retries`/`until`) and `ansible.builtin.command`
  for the things that must fail, both with `delegate_to: pc-a-@POD@`
- **`assert`** on each result
- **`serial: 1`** so a bad change reaches one firewall, not all at once

## 3. Prove it

```sh
ansible-playbook labs/6-lockdown/site.yml                 # changed, then changed=0
ansible-playbook probe.yml -e branch=a -e expect=allowed
ansible-playbook probe.yml -e branch=a -e port=443 -e expect=allowed
ansible-playbook probe.yml -e branch=a -e port=8080 -e expect=blocked
ansible-playbook probe.yml -e branch=a -e proto=icmp -e expect=blocked
ansible-playbook compare.yml                              # same rules as m
```

## The twist

Stop nginx on `web-a` (`ansible 'web:&auto' -m ansible.builtin.command -a "nginx -s stop"`), then rerun the playbook.
The test fails, the rescue flushes `LAB` and the play ends red: the firewall is back to the baseline, not half-locked.
Restart nginx (`nginx`) and run again.

Next lab: `labs/7-roles/README.md` (stretch) or `labs/8-capstone/README.md`.
