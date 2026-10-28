# Lab 1: A first playbook, the web page

Goal: serve a page that says your name on both web servers. HTTP is still blocked by the firewall; fixing that is lab 2.

## 1. By hand, on branch m

```sh
ssh root@web-m-@POD@
echo '<h1>Hello from m</h1>' > /var/www/html/index.html
curl -s http://127.0.0.1/
```

It works on the server itself. From the pc, `curl http://10.10.20.10/` still times out: the firewall drops it.

## 2. With a playbook, on branch a

Fill in `labs/1-first-playbook/site.yml` (it has `TODO` markers), then run it from `~/netlab`:

```sh
ansible-playbook labs/1-first-playbook/site.yml
```

You will use:

- a **play** (`hosts:`) with **tasks**, each a module call
- `ansible.builtin.copy` to put a file in place, then `ansible.builtin.template` to fill in a Jinja2 variable
- a **handler**, run only when a task reports `changed`, to reload nginx
- no `become:` — the nodes log you in as root already, and `sudo` does not work in these containers

## 3. Prove it

```sh
ansible-playbook labs/1-first-playbook/site.yml          # changed
ansible-playbook labs/1-first-playbook/site.yml          # changed=0: idempotent
ansible web:&auto -m ansible.builtin.command -a "curl -s http://127.0.0.1/"
ansible-playbook probe.yml -e branch=a -e expect=blocked  # still blocked from the pc
ansible-playbook compare.yml                              # the nginx config matches m
```

`compare.yml` compares nginx **config files**, not pages: the page text is allowed to differ.

## The twist

Change the name in one place (the `page_title` variable) and rerun: only the template task reports `changed`, and
nginx reloads once. Doing that by hand on two servers means two SSH sessions and no record of what you did.

Next lab: `labs/2-variables-loops/README.md` (open HTTP and HTTPS through the firewall).
