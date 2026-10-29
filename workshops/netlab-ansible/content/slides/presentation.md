---
marp: true
theme: default
paginate: true
size: 16:9
html: true
style: |
    @import url('assets/themes/presentation.css');
    .split { align-items: center; display: flex; gap: 48px; }
    .split > div { flex: 1; min-width: 0; }
    .split-top { align-items: flex-start; }
    .split-40 > div:first-child { flex: 0 0 40%; }
    .split-60 > div:first-child { flex: 0 0 58%; }
    .mermaid { text-align: center; margin: 8px 0; }
    .mermaid:not([data-processed]) { visibility: hidden; }
    .mermaid svg { max-height: 400px; }
    .mermaid.short svg { max-height: 250px; }
    .mermaid foreignObject p, .mermaid foreignObject div { margin: 0 !important; line-height: 1.35 !important; }
    .pop-overlay pre { margin: 0 0 14px; }
    .pop-overlay pre.pop-code { font-size: 14px; line-height: 1.3; padding: 8px 16px; margin: 0 0 10px; }
    .pop-overlay pre.pop-code code { font-size: 14px; }
    .pop-overlay .leak-grid + .leak-grid { margin-top: 14px; }
    .snip-row { gap: 20px; }
    .snip-row > div:first-child { flex: 0 0 46%; }
    .snip-row > div:not(:first-child) { flex: 1 1 0; }
    .snip { font-size: 15px; line-height: 1.35; padding: 8px 14px; margin: 0; }
    .snip code { font-size: 15px; }
    .small { font-size: 0.85em; }
    .lede { color: var(--muted); font-size: 0.9em; }
footer: '[&larr; Hub](index.md) &nbsp;|&nbsp; Ansible on a Small Network | Engineering & IT Operations'
---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: "[&larr; Hub](index.md)" -->

# Ansible on a Small Network

## Do it by hand once. Then say it in a playbook.

**Talk + hands-on lab**

<!-- Assumes the room can use a shell and ssh. No Ansible experience needed. The firewall is only the thing being configured; the lesson is Ansible. About 20 minutes of talk, then labs. -->

---

## Today

1. **The problem**: why configuring machines by hand breaks down
2. **The idea**: describe the state you want, let a tool get there
3. **How Ansible works**: control node, inventory, modules, playbooks, a run
4. **Your pod**: a small network you build twice
5. **The labs**: by hand, by playbook, then prove it

> Same result two ways. The second way is the one you can repeat.

<!-- Say the goal: leave knowing what Ansible is for and able to read and write a playbook. Nobody needs to know networking. -->

---

<!-- _class: section-title -->

# Part 1

## The problem

---

## A small network, set up by hand

<div class="mermaid short">
flowchart TB
  sw["switch<br/>VLANs"]
  sw --- pc["pc<br/>10.10.10.10"]
  sw --- web["web server<br/>nginx + sshd"]
  sw --- fw["firewall<br/>iptables"]
</div>

Everything plugs into the **switch**. The pc and web server sit on different VLANs, so traffic goes up to the firewall and back.

You log in to **each box** and type commands: open ports on the firewall, set up the web server, assign VLANs on the switch.

<!-- Four boxes, a handful of settings each. This is a normal day for an operations team. -->

---

## It works. Once.

```sh
ssh root@fw
iptables -A LAB -p tcp --dport 80 -j ACCEPT
iptables -A LAB -p tcp --dport 443 -j ACCEPT
```

<label for="iptables-help" class="pop-trigger">New to iptables? What these commands mean</label>

Looks fine. Now ask:

- Did you remember **both** ports? Which one did you forget last time?
- Is that the same on the **second** firewall?
- What did it look like **before** you started?

The commands ran. Nothing recorded them.

<div class="pop">
<input type="checkbox" id="iptables-help" class="pop-toggle">
<div class="pop-overlay">
<label for="iptables-help" class="pop-close">close &#10005;</label>
<h3>iptables in two minutes</h3>
<p class="pop-sub">The Linux firewall. You will meet it on the <code>fw</code> node. Skip this if you already know it.</p>
<pre><code>iptables -A LAB -p tcp --dport 80 -j ACCEPT</code></pre>
<div class="leak-grid">
<div class="leak"><i>the tool</i><b>iptables</b>Reads and changes the firewall rules on this machine</div><div class="leak"><i>-A LAB</i><b>append to LAB</b>Add the rule to the end of the chain named <code>LAB</code></div><div class="leak"><i>-p tcp</i><b>protocol</b>Only match TCP traffic (web, ssh). Others: <code>udp</code>, <code>icmp</code> (ping)</div><div class="leak"><i>--dport 80</i><b>destination port</b>Only traffic going to port 80, which is HTTP. HTTPS is 443</div><div class="leak"><i>-j ACCEPT</i><b>jump to target</b>What to do on a match: <code>ACCEPT</code> lets it through, <code>DROP</code> discards it</div>
</div>
<div class="leak-grid cols-3">
<div class="leak"><i>chain</i><b>A list of rules</b><code>LAB</code> is the chain this lab owns. The rules in it form an ordered list</div><div class="leak"><i>order</i><b>First match wins</b>Packets are checked top to bottom. A <code>DROP</code> above an <code>ACCEPT</code> beats it<em>Order matters</em></div><div class="leak"><i>look</i><b>See and undo</b><code>iptables -S LAB</code> lists the rules. <code>iptables -F LAB</code> empties the chain</div>
</div>
</div>
</div>

---

## Where by-hand breaks down

| Problem | What it looks like |
| ------- | ------------------ |
| **Drift** | Server 2 differs from server 1, and nobody knows why |
| **No record** | "Who opened port 8080?" has no answer |
| **No undo** | Going back means remembering what you changed |
| **Doesn't scale** | 2 servers is an afternoon, 50 is a month |
| **Risky** | One typo in `sshd_config` locks you out of the box |

> The server remembers what you did. Nobody else does.

---

## The cost of a typo

You edit `sshd_config` by hand, reload `sshd`, and close your session.

```text
$ ssh root@web
root@web: Permission denied
```

- The change was wrong, and you only learn it **after** it is live
- The only way back in was the connection you just closed
- On a real server this means a console visit or an outage

We want a way to **test a change before it is applied**, and to **undo it**.

---

## Same task, written down

What if the steps were a file, not your memory?

```yaml
- name: Open the web ports
  hosts: fw
  tasks:
    - name: Allow HTTP and HTTPS
      ansible.builtin.iptables:
        chain: LAB
        protocol: tcp
        destination_port: "{{ item }}"
        jump: ACCEPT
      loop: ["80", "443"]
```

Reviewable. Versioned in git. Runs the same on 1 box or 50.

<label for="yaml-help" class="pop-trigger">New to YAML? How to read this</label>

<div class="pop">
<input type="checkbox" id="yaml-help" class="pop-toggle">
<div class="pop-overlay">
<label for="yaml-help" class="pop-close">close &#10005;</label>
<h3>Reading YAML</h3>
<p class="pop-sub">Playbooks are YAML: plain text where <b>indentation is the structure</b>. Match each number to a card. Skip this if it is familiar.</p>
<pre class="pop-code"><code>- name: Open the web ports                    # 1
  hosts: fw                                   # 2
  tasks:                                      # 3
    - name: Allow HTTP and HTTPS
      ansible.builtin.iptables:               # 4
        chain: LAB
        destination_port: "{{ item }}"        # 5
        jump: ACCEPT
      loop: ["80", "443"]                     # 6</code></pre>
<div class="leak-grid cols-3">
<div class="leak"><i>Line 1</i><b>A dash starts an item</b>Each play and each task begins with <code>-</code>. <code>tasks</code> is a list of them</div>
<div class="leak"><i>Line 2</i><b>key: value</b>Name, colon, space, value. Here: run on the group <code>fw</code></div>
<div class="leak"><i>Line 3</i><b>Indent to nest</b>Indented lines belong to the key above. Spaces only, never tabs</div>
<div class="leak"><i>Line 4</i><b>A module and its arguments</b>The module is a key with no value. Its arguments are indented below it</div>
<div class="leak"><i>Line 5</i><b>A variable</b><code>{{ item }}</code> is replaced by a value at run time. Quote it</div>
<div class="leak"><i>Line 6</i><b>A list in brackets</b><code>loop</code> repeats the task once per entry. <code>item</code> is the current one</div>
</div>
</div>
</div>
</div>

---

<!-- _class: section-title -->

# Part 2

## How Ansible works

---

## What Ansible is

An **automation tool** that configures machines over **SSH**.

- **Agentless**: nothing to install on the machines you manage
- **Declarative**: you say *what state you want*, not *which commands to type*
- **Idempotent**: running it again changes nothing that is already right
- **Readable**: the playbook is YAML, and is also the documentation

> You describe the end state. Ansible works out what is missing.

---

## Control node and managed nodes

<div class="mermaid">
flowchart LR
  subgraph cn["Control node: your terminal"]
    inv["inventory<br/>hosts.ini"]
    pb["playbook<br/>site.yml"]
    ans["ansible-playbook"]
  end
  inv --> ans
  pb --> ans
  ans -- "SSH" --> fw["fw"]
  ans -- "SSH" --> web["web"]
  ans -- "SSH" --> sw["sw"]
</div>

Ansible runs **where you are** and reaches out. The managed nodes only need `sshd` and Python.

---

## Four pieces to learn

| Piece | Answers | Looks like |
| ----- | ------- | ---------- |
| **Playbook** | *Which hosts run which tasks* (a list of plays) | `site.yml` |
| **Inventory** | *Which machines?* | `hosts.ini` |
| **Task** | *Call a module, with arguments* | a `- name:` entry |
| **Module** | *Do one thing* | `ansible.builtin.copy` |

**How they fit:** a playbook has plays. A play picks hosts **from the inventory** and runs tasks. Each task **calls a module**.

Everything else (variables, templates, handlers, roles) is built from these four.

---

## A playbook is plays of tasks

```yaml
- name: Set up the web servers        # a play
  hosts: web                          # who: the group "web"
  tasks:                              # what: steps, run in order
    - name: Put the home page in place    # task 1
      ansible.builtin.copy:
        dest: /var/www/html/index.html
        content: "Hello\n"
    - name: Put a health file in place    # task 2
      ansible.builtin.copy:
        dest: /var/www/html/health.txt
        content: "ok\n"
```

- This file is a **playbook**: a list of **plays**. A play = who (`hosts:`) + what (`tasks:`)
- Tasks run top to bottom on **every host** in the group, each calling a **module** (here `copy`)

---

## Inventory: Ansible's address book

Ansible only touches machines it has a name for. The **inventory** is that list.

```ini
# hosts.ini: a [group] header, then one host per line
[fw]
fw-m-07
fw-a-07

[web]
web-m-07
web-a-07
```

- A **host** is one machine Ansible can SSH to: `fw-a-07` (the `07` is your pod)
- A **group** is a label for several hosts: `[fw]` means "the firewalls"
- A play says `hosts: fw`, and Ansible runs on **every host in that group**

---

## One host, several groups

The same machine can sit in more than one group, so you can aim at it **by job or by branch**.

| Host | `fw` | `web` | `manual` | `auto` |
| ---- | :--: | :---: | :------: | :----: |
| `fw-m-07` | yes | | yes | |
| `fw-a-07` | yes | | | yes |
| `web-m-07` | | yes | yes | |
| `web-a-07` | | yes | | yes |

- `hosts: fw` reaches both firewalls. `hosts: auto` reaches every branch-a node
- See it yourself: `ansible-inventory --graph`. Next: combine two groups

---

## Host patterns: pick the machines

A **pattern** says which hosts to run on. `:&` means **and also in**: the host must be in both groups.

| Pattern | Selects | Skipped |
| ------- | ------- | ------- |
| `fw` | `fw-m-07`, `fw-a-07` (the group `fw`) | every pc, sw and web node |
| `auto` | every branch-a node | all of branch m |
| `fw:&auto` | `fw-a-07`: in `fw` **and** in `auto` | `fw-m-07` (not in `auto`), non-firewalls |
| `web:&manual` | `web-m-07`: in `web` **and** in `manual` | `web-a-07` (not in `manual`), non-web |

---

## Where you type a pattern

The same pattern works in three places:

| Where | Example | What it does |
| ----- | ------- | ------------ |
| A play | `hosts: fw:&auto` | The play's tasks run on those hosts |
| An ad-hoc command | `ansible fw:&auto -m ansible.builtin.ping` | One module, once, on those hosts |
| `--limit` | `ansible-playbook site.yml --limit web-a-07` | Run the playbook, but **only** on these hosts |

> The labs use `fw:&auto` so a playbook can never touch your hand-built branch m.

---

## A task is a module call

```yaml
- name: Put the page in place        # a label for humans
  ansible.builtin.copy:              # the module
    dest: /var/www/html/index.html   # arguments
    content: "<h1>Hello</h1>\n"
    mode: "0644"
```

- `name` is printed when it runs, so write it as a sentence
- Arguments describe the **result**: this file, with this content
- No `if file exists` logic: the module checks that for you

---

## Modules: the actual work

A module is a ready-made tool for **one job**. You describe the result; it checks the machine and **changes only what differs**.

| Module | Use it to | It does nothing if |
| ------ | --------- | ------------------ |
| `ansible.builtin.copy` | put a file in place | the file already matches |
| `ansible.builtin.template` | fill in a file from variables | the result already matches |
| `ansible.builtin.iptables` | add a firewall rule | that rule is already there |
| `ansible.builtin.service` | start or stop a service | it is already in that state |
| `ansible.builtin.command` | run any command | Ansible can't tell: **you** decide |

Options and examples: `ansible-doc ansible.builtin.template`

---

## Ad-hoc: one module, once

Before playbooks, you can call a module from the shell.

```sh
ansible all -m ansible.builtin.ping
ansible fw -m ansible.builtin.command -a "iptables -S"
```

- First word: the **host pattern**
- `-m`: the **module**
- `-a`: its **arguments**

Great for asking questions of many nodes at once. For anything you want to repeat, write a playbook.

---

## What happens when you press Enter

<div class="mermaid">
sequenceDiagram
  participant You
  participant A as ansible-playbook
  participant N as managed node
  You->>A: ansible-playbook site.yml
  A->>A: read inventory and playbook
  A->>N: SSH in, send the module
  N->>N: check state, change only if needed
  N-->>A: ok, changed or failed
  A-->>You: summary per host
</div>

Each task runs on **every** selected host before the next task starts.

---

## Reading the output

```text
changed: [web-a-07]
ok: [web-m-07]
```

Each task prints **one line per host**. The first word says what happened there.

| Word | What happened on that host | What you do |
| ---- | -------------------------- | ----------- |
| `ok` | Already correct. Nothing was touched | Nothing |
| `changed` | Was wrong. Ansible fixed it | Expected on a first run |
| `failed` | The task hit an error and stopped | Read the message under it |
| `skipped` | A `when:` condition said no | Nothing |

The `PLAY RECAP` at the end totals each word per host.

---

## Idempotent: the key idea

Run the playbook twice.

<div class="split split-top">
<div>

```text
# first run
changed=3  failed=0
```

Three things were wrong. Ansible fixed them.

</div>
<div>

```text
# second run
changed=0  failed=0
```

Nothing was wrong. Ansible did nothing.

</div>
</div>

**`changed=0` is how you know the playbook describes the state, not a script of actions.**

Compare: `echo x >> file` adds a line **every** time you run it. That is a script, not a state.

---

## Idempotency, step by step

<div class="mermaid">
flowchart LR
  s["Task: file has this content"] --> c{"Is it already<br/>like that?"}
  c -- "yes" --> ok["ok: do nothing"]
  c -- "no" --> ch["change it<br/>report changed"]
  ch --> h["notify a handler?"]
</div>

A module **looks first**, then acts. That check is why it is safe to run again, on a schedule, or after a half-finished run.

---

## Variables: write it once

```yaml
# group_vars/fw.yml
allowed_ports: [80, 443]
```

```yaml
# in a task
destination_port: "{{ item | string }}"
loop: "{{ allowed_ports }}"
```

- `{{ ... }}` is **Jinja2**: Ansible swaps in the value
- `loop:` repeats a task for each item
- Change the list, rerun: only the **difference** is applied

<label for="jinja-help" class="pop-trigger">New to templates? What the braces mean</label>

<div class="pop">
<input type="checkbox" id="jinja-help" class="pop-toggle">
<div class="pop-overlay">
<label for="jinja-help" class="pop-close">close &#10005;</label>
<h3>Variables and Jinja2</h3>
<p class="pop-sub">Ansible fills in <code>{{ }}</code> blanks before it runs a task. Match each number to a card. Skip this if you have used templates before.</p>
<pre class="pop-code"><code># group_vars/fw.yml  (the data)
allowed_ports: [80, 443]                      # 1
# site.yml  (the task)
- ansible.builtin.iptables:
    chain: LAB
    destination_port: "{{ item | string }}"   # 2, 3
    jump: ACCEPT
  loop: "{{ allowed_ports }}"                 # 4
# sshd_config.j2  (a template file)
{% for p in allowed_ports %}                  # 5
Port {{ p }}
{% endfor %}</code></pre>
<div class="leak-grid cols-3">
<div class="leak"><i># 1</i><b>A variable is data</b>A name and a value, kept in <code>group_vars/fw.yml</code>. It applies to every host in group <code>fw</code></div>
<div class="leak"><i># 2</i><b>{{ }} inserts a value</b>Replaced by the variable's value when the task runs. Here <code>item</code> is the current loop entry</div>
<div class="leak"><i># 3</i><b>A filter after |</b>The pipe changes the value. <code>string</code> makes text, <code>length</code> counts a list</div>
<div class="leak"><i># 4</i><b>loop repeats a task</b>Once per entry in <code>allowed_ports</code>. Change the list, tasks stay the same</div>
<div class="leak"><i># 5</i><b>{% for %} is logic</b>Only in template files: repeats the lines inside, once per item</div>
<div class="leak"><i>trap</i><b>Quote the braces</b><code>port: {{ p }}</code> fails. Write <code>port: "{{ p }}"</code><em>YAML reads { as a map</em></div>
</div>
</div>
</div>
</div>
</div>

---

## Templates: a file with blanks

A **template** is a normal config file with `{{ }}` blanks. Ansible fills the blanks in **on the control node**, then copies the finished file to the host.

<div class="mermaid short">
flowchart LR
  t["template<br/>sshd_config.j2<br/>(has blanks)"] --> m(["template module<br/>fills the blanks"])
  v["variables<br/>group_vars/web.yml<br/>(has values)"] --> m
  m -- "finished file<br/>copied over SSH" --> h["web-a-07<br/>/etc/ssh/sshd_config"]
</div>

<div class="split split-top snip-row">
<div>
<pre class="snip"><code># the template
MaxAuthTries {{ sshd_max_auth_tries }}
LoginGraceTime {{ sshd_login_grace_time }}</code></pre>
</div>
<div>
<pre class="snip"><code># the variables
sshd_max_auth_tries: 3
sshd_login_grace_time: 20</code></pre>
</div>
<div>
<pre class="snip"><code># the file on the host
MaxAuthTries 3
LoginGraceTime 20</code></pre>
</div>
</div>

---

## Templates: the playbook that uses them

```yaml
- name: Harden sshd on the web servers
  hosts: web                         # no variables listed here: see next slide
  tasks:
    - name: Push the sshd settings
      ansible.builtin.template:
        src: sshd_config.j2          # the template, next to the playbook
        dest: /etc/ssh/sshd_config   # where the file lands on each web host
        validate: sshd -t -f %s      # test it before it is used
```

- **Variables:** not named here. Ansible finds them by **file name**, next slide
- **Changed or ok:** the file is replaced only if the result **differs**
- **`validate`:** runs on a temp copy (`%s`). If it fails, the old file stays and the task **fails**: a typo cannot lock you out

---

## Where the variables come from

The playbook never says "use `web.yml`". Ansible **matches the group name to a file name**.

<div class="split split-top">
<div>

```text
netlab-ansible/
├── hosts.ini          [web] web-a-07
├── site.yml           hosts: web
├── sshd_config.j2     {{ sshd_max_auth_tries }}
└── group_vars/
    └── web.yml        sshd_max_auth_tries: 3
```

`group_vars/fw.yml` would apply only to `fw`.

</div>
<div>

**For `web-a-07`, Ansible:**

1. `hosts.ini`: it is in group **web**
2. Loads `group_vars/web.yml`: same name
3. Fills the blank with **3**
4. Writes the file to `dest`

</div>
</div>

---

## Handlers: react to change

Some jobs should run **only if something changed**, like reloading nginx after its config was rewritten.

<div class="split split-top">
<div>

```yaml
tasks:
  - name: Push the nginx config
    ansible.builtin.template:
      src: site.conf.j2
      dest: /etc/nginx/http.d/site.conf
    notify: Reload nginx      # 1

handlers:
  - name: Reload nginx        # 2
    ansible.builtin.service:
      name: nginx
      state: reloaded
```

</div>
<div>

1. `notify` is a note on the task: "if **you** report `changed`, run the handler with this name."
2. A **handler** is a task in its own `handlers:` list. It sits idle until something notifies it.

If it reports `ok`, the handler never runs.

</div>
</div>

---

## Handlers: two runs of the same playbook

<div class="mermaid">
flowchart LR
  t["template task"] -- "changed: file was different" --> h["handler runs: reload nginx"]
  t -- "ok: file already matched" --> x["handler skipped"]
</div>

| Run | Task result | Handler |
|---|---|---|
| 1st: config edited | `changed` | **runs**, once, after all tasks finish |
| 2nd: nothing to do | `ok` | does not run |

- Five tasks all notify "Reload nginx"? It still runs **once**, at the end.
- Without a handler you would reload on every run, or forget to reload at all.

---

## Check mode: look before you leap

```sh
ansible-playbook site.yml --check --diff
```

- `--check`: change nothing, report what **would** change
- `--diff`: show the lines that would be added or removed

```text
--- before: /etc/ssh/sshd_config
+++ after:  /etc/ssh/sshd_config
-MaxAuthTries 6
+MaxAuthTries 3
```

By hand you never get a preview. With Ansible you do, every time.

---

## Safety nets: check before you change

<div class="split split-top">
<div>

**`validate:` tests a file before it goes live**

<pre class="snip"><code>- ansible.builtin.template:
    src: sshd_config.j2
    dest: /etc/ssh/sshd_config
    validate: sshd -t -f %s</code></pre>

Ansible writes the result to a temp file (`%s`) and runs `sshd -t` on it. A bad file fails the task and the **old file stays**. A typo can't lock you out.

</div>
<div>

**`assert` stops the play unless a test is true**

<pre class="snip"><code>- ansible.builtin.assert:
    that: sshd_max_auth_tries | int <= 6
    fail_msg: "MaxAuthTries is too high"
    success_msg: "MaxAuthTries is OK"</code></pre>

It fails early, before anything changes.

</div>
</div>

---

## Safety nets: undo, and limit the damage

<div class="split split-top">
<div>

**`block / rescue / always`: try, undo, report**

```yaml
- block:
    - ansible.builtin.template: {src: a.j2, dest: /etc/a}
    - ansible.builtin.command: check-a
  rescue:
    - ansible.builtin.copy: {src: a.bak, dest: /etc/a}
  always:
    - ansible.builtin.debug: {msg: "finished"}
```

Tasks in `block` run in order. If one **fails**, `rescue` runs (restore the backup). `always` runs either way.

</div>
<div>

**`serial: 1` changes one host at a time**

```yaml
- hosts: web
  serial: 1
  tasks:
    - ansible.builtin.template: ...
```

Normally Ansible hits every host at once. With `serial: 1`, a failure on the first host **stops the play** before the other hosts are touched, so one mistake does not become fifty.

</div>
</div>

---

## Secrets: keep them out of git

Playbooks live in git, so a plain-text password in one is visible to everyone, forever. **Ansible Vault** encrypts the file that holds it.

<div class="split split-top">
<div>

**Before: plain text (never commit this)**

<pre class="snip"><code># secrets.yml
admin_password: "change-me"</code></pre>

**After encrypting: safe to commit**

<pre class="snip"><code>$ANSIBLE_VAULT;1.1;AES256
36383435663261336431623532
66353837376664316239366335
...</code></pre>

</div>
<div>

1. `ansible-vault create secrets.yml` opens an editor and saves the file **encrypted**.
2. The **vault password** is the key. Keep it in `.vault_pass`, which is **not** in git.
3. Anyone with the repo but not the key sees only the scrambled text.

</div>
</div>

---

## Secrets: using them in a playbook

<div class="split split-top">
<div>

```yaml
- hosts: web
  vars_files:
    - secrets.yml          # 1
  tasks:
    - name: htpasswd file
      ansible.builtin.copy:
        content: "admin:{{ hash }}"
        dest: /etc/nginx/.htpasswd
      no_log: true         # 2
```

```sh
ansible-playbook site.yml \
  --vault-password-file .vault_pass   # 3
```

</div>
<div>

1. `vars_files` loads the encrypted file. Its variables (`admin_password`) work like any other.
2. `no_log: true` hides this task's output. Otherwise the password would show in the terminal or logs.
3. The password file lets Ansible decrypt `secrets.yml` in memory at run time. Nothing plain is written to disk.

</div>
</div>

---

## Secrets: how a team does it

| | Small team / lab | Pipeline runs it | Secrets manager |
|---|---|---|---|
| **Secrets live** | encrypted `secrets.yml` in git | encrypted `secrets.yml` in git | outside git; fetched at run time |
| **Vault password** | each person's git-ignored `.vault_pass` | one masked CI secret | none needed |
| **Best for** | simple setups | most teams | strict rules, rotation, audit |

- **Pipeline:** CI runs `--check --diff` on the pull request and the real run on merge. No one holds the key.
- **Manager:** OpenBao, HashiCorp Vault or a cloud key store.

---

## Secrets: rules for every team

1. **Never commit** `.vault_pass`. Add it to `.gitignore`.
2. **`no_log: true`** on every task that touches a secret.
3. **One vault password per environment**, so a leaked dev key cannot open production (vault IDs).
4. **Rotate** the key when someone leaves: `ansible-vault rekey secrets.yml`.
5. **Review changes by pull request**, so a secret never changes unseen.

---

<!-- _class: section-title -->

# Part 3

## Your pod

---

## One pod per student

<div class="mermaid">
flowchart TB
  sw["sw<br/>switch"]
  subgraph v10["VLAN 10"]
    pc["pc<br/>10.10.10.10"]
  end
  subgraph v20["VLAN 20"]
    web["web<br/>10.10.20.10"]
  end
  sw --- pc
  sw --- web
  sw -- "trunk" --- fw["fw<br/>firewall"]
</div>

- **pc** asks for pages. **web** serves them. **fw** decides what may pass
- The switch keeps the VLANs apart, so `pc` cannot reach `web` without `fw`

<label for="vlan-help" class="pop-trigger">New to VLANs? What the trunk is</label>

<div class="pop">
<input type="checkbox" id="vlan-help" class="pop-toggle">
<div class="pop-overlay">
<label for="vlan-help" class="pop-close">close &#10005;</label>
<h3>VLANs and the trunk</h3>
<p class="pop-sub">Why the pc cannot talk straight to the web server. Skip this if you know networking.</p>
<div class="leak-grid cols-4">
<div class="leak"><i>VLAN</i><b>a virtual LAN</b>One physical switch acts as several separate networks. VLAN 10 and VLAN 20 cannot see each other</div><div class="leak"><i>access port</i><b>one VLAN</b>The switch port a <code>pc</code> or <code>web</code> plugs into. Traffic belongs to that port's VLAN</div><div class="leak"><i>trunk</i><b>many VLANs, one cable</b>The <code>sw</code> to <code>fw</code> link. Each frame carries a VLAN tag (802.1Q) so the firewall knows which side it came from</div><div class="leak"><i>router</i><b>crossing VLANs</b>Different VLANs are different subnets: <code>10.10.10.0/24</code> and <code>10.10.20.0/24</code>. Only a router, here <code>fw</code>, passes traffic between them</div>
</div>
<div class="leak-grid cols-3">
<div class="leak"><i>why</i><b>One choke point</b>Every pc to web request crosses <code>fw</code>, so the firewall rules decide what is allowed</div><div class="leak"><i>names</i><b>Router on a stick</b>One cable carries both VLANs to the router. Labs S1 to S3 build this part yourself</div><div class="leak"><i>look</i><b>On the nodes</b><code>bridge vlan show</code> on <code>sw</code>; <code>ip addr</code> on <code>fw</code></div>
</div>
</div>
</div>

---

## Follow one request

<div class="mermaid">
flowchart LR
  subgraph v10["VLAN 10"]
    pc["pc"]
  end
  sw["sw<br/>switch"]
  fw["fw<br/>firewall"]
  subgraph v20["VLAN 20"]
    web["web"]
  end
  pc -- "1. request" --> sw
  sw -- "2. trunk: VLAN 10" --> fw
  fw -- "3. allowed? VLAN 20" --> sw
  sw -- "4. delivered" --> web
</div>

The switch is used **twice**. The firewall is the only place the request can cross, so it is where the rules live.

---

## Why a network?

You do not need to know networking. It gives us:

- **Real services** with real failure modes: a firewall that blocks, a server that will not reload
- **Something you can test**: "can the pc reach the web server?" is a yes or no
- **Several kinds of machine** to show one tool managing them all

The firewall is only the thing being configured. **The lesson is Ansible.**

---

## Twice: branch m and branch a

<div class="mermaid">
flowchart LR
  subgraph m["Branch m: by hand"]
    mpc["pc"] --- mfw["fw"] --- mweb["web"]
  end
  subgraph a["Branch a: by playbook"]
    apc["pc"] --- afw["fw"] --- aweb["web"]
  end
  you["You"] -- "ssh + shell" --> m
  you -- "ansible-playbook" --> a
</div>

Eight nodes per student. Both branches **start identical** and are isolated from each other.

---

## Your login and your nodes

```sh
cd ~/netlab
ansible-inventory --graph        # what Ansible knows
ssh root@fw-m-07                 # by hand (pod 07)
```

- Your pod number is in your user name: `student07` is pod `07`
- Node names are `role-branch-pod`: `fw-m-07`, `web-a-07`
- Ansible already has the password (`group_vars/all.yml`), so playbooks never ask
- You are `root` on the nodes: no `become`, no `sudo`

---

## Branch m is the answer key

| | Branch m | Branch a |
| --- | --- | --- |
| You use | `ssh` and a shell | `ansible-playbook` |
| Starts | closed: ping only | closed: ping only |
| Prove traffic | `probe.yml` | `probe.yml` |
| Finish | `compare.yml` shows no difference | `dojo netlab check N` passes |

A correct playbook ends in the **same state** your hands produced.

> If `compare.yml` says DIFFERENT, one of the two branches is wrong. Find out which.

---

## The tools that check you

```sh
ansible-playbook probe.yml -e branch=a -e expect=allowed
ansible-playbook compare.yml
dojo netlab check 2
```

| Tool | Question it answers |
| ---- | ------------------- |
| `probe.yml` | Does traffic get through? **PASS** if it matches `expect` |
| `compare.yml` | Do the firewall rules and nginx config on m and a match? |
| `dojo netlab check N` | Does the whole lab pass, from outside your pod? |

---

<!-- _class: section-title -->

# Part 4

## The labs

---

## Every lab has the same four parts

<div class="mermaid">
flowchart LR
  h["1. By hand<br/>on branch m"] --> p["2. By playbook<br/>on branch a"]
  p --> v["3. Prove it<br/>probe, compare, check"]
  v --> t["4. The twist<br/>rerun, undo, change one value"]
</div>

The README states the **goal**, not the commands. You work out the commands by hand first, then say them as tasks.

---

## The path

| Core path | Stretch |
| --------- | ------- |
| 0 Orientation | 5 Secrets with Vault |
| 1 A first playbook | 7 Roles |
| 2 Variables and loops | S1 VLANs, build it yourself |
| 3 Idempotency | S2 Trunk |
| 4 Templates and validate | S3 Segmentation |
| 6 Errors and rollback | |
| 8 Capstone | |

Core first. Stretch labs only after lab 8.

---

## Lab 0: orientation

**By hand:** `ssh` to the firewall, read its addresses, rules and forwarding flag. One question, one box.

**With Ansible:**

```sh
ansible-inventory --graph
ansible all -m ansible.builtin.ping
ansible fw -m ansible.builtin.command -a "iptables -S"
```

**Twist:** get the nginx version from **both** web servers in one command.

*Learn: inventory, host patterns, ad-hoc modules.*

---

## Lab 1: a first playbook

**By hand:** write `index.html` on the web server. It works locally; from the pc it still times out (the firewall).

**With Ansible:** `copy`, then `template`, then a **handler** to reload nginx.

**Twist:** change `page_title` in one place, rerun. Only the template task says `changed`, and nginx reloads once.

*Learn: play, task, template, handler, `changed=0`.*

---

## Lab 2: variables and loops

**Goal:** the pc reaches the web server on TCP 80 and 443. Nothing else new.

```yaml
loop: "{{ allowed_ports }}"      # group_vars/fw.yml
```

**Twist:** add 8080 to the list and rerun. Exactly one item reports `changed`. Now remove it. Nothing is removed: the module only **adds**.

*Learn: variables, loops, `when`, and a module's limits.*

---

## Lab 3: idempotency and check mode

**Goal:** HTTPS with a self-signed certificate.

- `creates:` stops a `command` from running again once the file exists
- `changed_when` tells Ansible what "changed" means for a command
- `--check --diff` previews the change

**Twist:** edit the template, run with `--check --diff`: a diff and no change. Then run it for real.

*Learn: making commands idempotent, previewing.*

---

## Lab 4: templates and validate

**Goal:** harden `sshd` (`MaxAuthTries 3`, `LoginGraceTime 20`, no X11) and still be able to log in.

```yaml
validate: sshd -t -f %s
```

**Twist:** put `sshd_max_auth_tries: three` in `group_vars/web.yml`. `validate` fails the task, the live file is untouched, `sshd` keeps running. The same typo by hand costs you the node.

*Learn: templates, handlers, `validate`.*

---

## Lab 6: errors and rollback

**Goal:** only 80 and 443 pass. Everything else, including ping, is dropped.

<div class="mermaid">
flowchart LR
  b["block: apply rules"] --> t["test from the pc"]
  t -- "pass" --> al["always: print rules"]
  t -- "fail" --> r["rescue: flush LAB<br/>and fail loudly"]
  r --> al
</div>

**Twist:** stop nginx, rerun. The test fails, the rescue undoes the lockdown.

---

## Lab 8: the capstone

**Goal:** rebuild branch a from the baseline in **one command**, then run it again for `changed=0`.

```sh
ansible-playbook reset_fw.yml -e branch=a
ansible-playbook labs/8-capstone/site.yml
ansible-playbook labs/8-capstone/site.yml    # changed=0
```

**Twist:** time it against the hours branch m took, then rebuild once more with `--check --diff` first.

---

## Stretch: when there is no module

- **5 Vault**: a password in git, encrypted, never in the output
- **7 Roles**: the same behaviour, in a better structure
- **S1 to S3 The switch**: no module and no starter file. You design the data model, the template and the idempotency guard.

Different problem, same skills.

---

## The habits to take away

1. **Describe the end state**, not the steps
2. **Run it twice**: the second run must say `changed=0`
3. **Preview first** with `--check --diff`
4. **Validate before you apply** anything that can lock you out
5. **Test, and roll back** on failure
6. **Keep it in git**: the playbook is the record

---

## If you get stuck

- `ansible-playbook verify_topology.yml`: is the pod healthy?
- `ansible-playbook reset_fw.yml -e branch=a`: back to the baseline
- `dojo netlab check N`: what is still wrong, line by line
- Read the error: Ansible says which task, which host, and why
- Put your hand up: the facilitator has a pod of their own

---

## Let's go

1. Open `lab-index.md` and the Lab 0 page
2. Work in `~/netlab` in your terminal
3. Core path first. Stretch labs only after lab 8

<!-- Suggested timing is in FACILITATOR.md. -->

<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs"
  mermaid.initialize({
    startOnLoad: false,
    theme: "dark",
    fontFamily: "Manrope, sans-serif",
    flowchart: { htmlLabels: true, curve: "basis" },
    sequence: { mirrorActors: false, actorFontSize: 18, messageFontSize: 18, noteFontSize: 18, boxMargin: 8 },
    themeVariables: {
      fontSize: "18px",
      background: "#18242e",
      primaryColor: "#21313c",
      primaryTextColor: "#e8f0f2",
      primaryBorderColor: "#3dd6c3",
      secondaryColor: "#18242e",
      tertiaryColor: "#18242e",
      lineColor: "#a9bac2",
      edgeLabelBackground: "#18242e",
      clusterBkg: "#18242e",
      actorBkg: "#21313c",
      actorBorder: "#3dd6c3",
      actorTextColor: "#e8f0f2",
      signalColor: "#a9bac2",
      signalTextColor: "#e8f0f2",
      noteBkgColor: "#137f7a",
      noteTextColor: "#e8f0f2",
      noteBorderColor: "#3dd6c3",
    },
  })
  // Draw in a scratch element on <body> (see dojo-introduction): Marp scales the slide, which would shrink the boxes.
  async function draw() {
    const decode = document.createElement("textarea")
    let n = 0
    for (const el of document.querySelectorAll(".mermaid:not([data-processed])")) {
      decode.innerHTML = el.innerHTML
      const src = decode.value.replace(/<br\s*\/?>/gi, "<br/>").trim()
      const { svg, bindFunctions } = await mermaid.render(`mermaid-${n++}`, src)
      el.innerHTML = svg
      bindFunctions?.(el)
      el.setAttribute("data-processed", "true")
    }
  }
  document.fonts.load('18px Manrope').catch(() => {}).then(() => document.fonts.ready).then(draw)
</script>
