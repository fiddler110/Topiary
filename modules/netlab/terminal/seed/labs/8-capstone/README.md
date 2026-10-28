# Lab 8: Capstone, from clean to done

Goal: one command rebuilds branch a from the baseline into the finished state of labs 2, 3, 4 and 6, and a second run changes nothing.

## 1. By hand, on branch m

Your branch m is the reference: by now it has the HTTP and HTTPS rules, the certificate and `tls.conf`, the hardened `sshd_config`
and the lockdown. Write down, in order, how many commands and SSH sessions that took.

## 2. With a playbook, on branch a

Throw branch a away and rebuild it:

```sh
ansible-playbook reset_fw.yml -e branch=a
ansible-playbook labs/8-capstone/site.yml
```

Fill in `labs/8-capstone/site.yml`. Either import your lab playbooks in order (`import_playbook: ../2-variables-loops/site.yml`)
or call your lab 7 roles. Order: page, certificate and sshd on the web server **first**, firewall rules and lockdown **last**.
The lockdown's own tests need the web server up.

## 3. Prove it

```sh
ansible-playbook labs/8-capstone/site.yml                 # changed=0 on the second run
ansible-playbook probe.yml -e branch=a -e expect=allowed
ansible-playbook probe.yml -e branch=a -e port=443 -e expect=allowed
ansible-playbook probe.yml -e branch=a -e port=8080 -e expect=blocked
ansible-playbook probe.yml -e branch=a -e proto=icmp -e expect=blocked
ansible-playbook compare.yml                              # the two branches agree
```

## The twist

Run `reset_fw.yml -e branch=a` and `site.yml` again, then time it against the hours branch m took. Then rebuild
it a third time with `--check --diff` first and read what it would do. That preview is something a hand-built network never gives you.
