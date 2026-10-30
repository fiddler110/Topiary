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
footer: "[&larr; Hub](index.md) &nbsp;|&nbsp; Ansible on a Small Network | Engineering & IT Operations"
---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: "[&larr; Hub](index.md)" -->

# Ansible on a Small Network

## Do it by hand once. Then say it in a playbook.

Prerequisite: a shell and `ssh`. No Ansible experience needed.

**Talk ~25 min · By hand (M1-M9) ~105 min · Playbooks (A1-A9) ~150 min**
Stretch labs A10 and A11 add ~45 min. About 4.5 hours in all, or two sessions.

<!-- Assumes the room can use a shell and ssh. The firewall is only the thing being configured; the lesson is Ansible. Lab times are the figures on the lab pages (M1-M9 sum to 105 min, A1-A9 to 150 min, A10 and A11 are 25 and 20). The talk time is my estimate from the slide count: about 20 minutes if you skip the secrets slides. For a shorter slot (lunch and learn), see FACILITATOR.md. -->

---

## Today

1. **The problem**: why configuring machines by hand breaks down, and what to do instead
2. **How Ansible works**: control node, inventory, modules, playbooks, a run
3. **Your pod**: a small network you build twice
4. **The labs**: by hand, by playbook, then prove it

> Same result two ways. The second way is the one you can repeat.

<!-- Say the goal: leave knowing what Ansible is for and able to read and write a playbook. Nobody needs to know networking. About 1 minute. -->

---

<!-- _class: section-title -->

# Part 1

## The problem

<!-- Part 1 is the problem. Move fast, the room already knows it. -->

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

<!-- Four boxes, a handful of settings each. This is an ordinary day for an operations team, and nobody thinks it's a problem yet. Ask who has done this for real. Thirty seconds. -->

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

<!-- Let the room answer the three questions out loud. Most people admit they've forgotten a port at least once. The commands ran fine, and that's the point: nothing recorded them. If someone doesn't know iptables, open the popup, but don't linger. It isn't what this workshop is about. About 2 minutes. -->

---

## Where by-hand breaks down

| Problem           | What it looks like                                   |
| ----------------- | ---------------------------------------------------- |
| **Drift**         | Server 2 differs from server 1, and nobody knows why |
| **No record**     | "Who opened port 8080?" has no answer                |
| **No undo**       | Going back means remembering what you changed        |
| **Doesn't scale** | 2 servers is an afternoon, 50 is a month             |
| **Risky**         | One typo in `sshd_config` locks you out of the box   |

> The server remembers what you did. Nobody else does.

<!-- Ask which row has hurt them most. Drift and no record are usually the winners. Keep it short, they've felt all five. About 1 minute. -->

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

<!-- This one is personal for most people. Tell the sshd story if you have one. We come back to it in A7, where validate stops it happening. About 1 minute. -->

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

<!-- This is the first time they see a playbook. Don't explain the syntax yet: say it reads like a to-do list for the firewall. The YAML popup is there for anyone who wants it. We take it apart over the next few slides. About 2 minutes. -->

---

<!-- _class: section-title -->

# Part 2

## How Ansible works

<!-- Part 2 is the longest. Playbooks, idempotency and handlers are the core. The secrets slides at the end are optional. -->

---

## What Ansible is

An **automation tool** that configures machines over **SSH**.

- **Agentless**: nothing to install on the machines you manage
- **Declarative**: you say _what state you want_, not _which commands to type_
- **Idempotent**: running it again changes nothing that is already right
- **Readable**: the playbook is YAML, and is also the documentation

> You describe the end state. Ansible works out what is missing.

<!-- Four words to remember: agentless, declarative, idempotent, readable. Idempotent gets its own slide shortly. Nothing runs on the managed nodes except sshd and Python. About 1 minute. -->

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

<!-- Point at the diagram: everything runs from your terminal and reaches out over SSH. Here the control node is each student's own terminal, and the nodes are their pod. About 1 minute. -->

---

## Where to run Ansible

The control node must be **Linux or macOS**. Ansible does not run natively on Windows.

|              | Your own machine                     | A shared control node                                         |
| ------------ | ------------------------------------ | ------------------------------------------------------------- |
| **What**     | Linux or macOS. On Windows, **WSL2** | One central Linux VM for many teams                           |
| **Access**   | you, with your own SSH keys          | a named account per person, limited to their team's inventory |
| **Best for** | learning, small teams                | many teams, one audited place to run changes                  |

A shared node keeps keys and secrets off laptops. No shared logins; log who ran what.

<!-- Mostly background. If the room is all on Windows, mention WSL2 and move on. Skip this slide if you're short on time. The labs don't depend on it. -->

---

## Four pieces to learn

| Piece         | Answers                                         | Looks like             |
| ------------- | ----------------------------------------------- | ---------------------- |
| **Playbook**  | _Which hosts run which tasks_ (a list of plays) | `site.yml`             |
| **Inventory** | _Which machines?_                               | `hosts.ini`            |
| **Task**      | _Call a module, with arguments_                 | a `- name:` entry      |
| **Module**    | _Do one thing_                                  | `ansible.builtin.copy` |

**How they fit:** a playbook has plays. A play picks hosts **from the inventory** and runs tasks. Each task **calls a module**.

Everything else (variables, templates, handlers, roles) is built from these four.

<!-- Spend time here. If they get playbook, inventory, task and module straight, the rest of the day is detail. Say the sentence at the bottom out loud: a playbook has plays, a play picks hosts, each task calls a module. About 2 minutes. -->

---

## A playbook is plays of tasks

```yaml
- name: Set up the web servers # a play
  hosts: web # who: the group "web"
  tasks: # what: steps, run in order
      - name: Put the home page in place # task 1
        ansible.builtin.copy:
            dest: /var/www/html/index.html
            content: "Hello\n"
      - name: Put a health file in place # task 2
        ansible.builtin.copy:
            dest: /var/www/html/health.txt
            content: "ok\n"
```

- This file is a **playbook**: a list of **plays**. A play = who (`hosts:`) + what (`tasks:`)
- Tasks run top to bottom on **every host** in the group, each calling a **module** (here `copy`)

<!-- Walk the file top to bottom and point at who (hosts) and what (tasks). Both tasks run on every host in the group. About 1 minute. -->

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

<!-- Ansible only touches machines it has a name for. Point out the pod number in the host names, because they'll see it in every lab. About 1 minute. -->

---

## One host, several groups

The same machine can sit in more than one group, so you can aim at it **by job or by branch**.

| Host       | `fw` | `web` | `manual` | `auto` |
| ---------- | :--: | :---: | :------: | :----: |
| `fw-m-07`  | yes  |       |   yes    |        |
| `fw-a-07`  | yes  |       |          |  yes   |
| `web-m-07` |      |  yes  |   yes    |        |
| `web-a-07` |      |  yes  |          |  yes   |

- `hosts: fw` reaches both firewalls. `hosts: auto` reaches every branch-a node
- See it yourself: `ansible-inventory --graph`. Next: combine two groups

<!-- This is what lets a playbook aim at branch a and never touch the hand-built branch m. Suggest they try ansible-inventory --graph in the first lab. About 1 minute. -->

---

## Host patterns: pick the machines

A **pattern** says which hosts to run on. `:&` means **and also in**: the host must be in both groups.

| Pattern       | Selects                                  | Skipped                                  |
| ------------- | ---------------------------------------- | ---------------------------------------- |
| `fw`          | `fw-m-07`, `fw-a-07` (the group `fw`)    | every pc, sw and web node                |
| `auto`        | every branch-a node                      | all of branch m                          |
| `fw:&auto`    | `fw-a-07`: in `fw` **and** in `auto`     | `fw-m-07` (not in `auto`), non-firewalls |
| `web:&manual` | `web-m-07`: in `web` **and** in `manual` | `web-a-07` (not in `manual`), non-web    |

<!-- The :& pattern trips people up, so read one row aloud: in fw and also in auto. You don't need to cover every row. About 1 minute. -->

---

## Where you type a pattern

The same pattern works in three places:

| Where             | Example                                      | What it does                                  |
| ----------------- | -------------------------------------------- | --------------------------------------------- |
| A play            | `hosts: fw:&auto`                            | The play's tasks run on those hosts           |
| An ad-hoc command | `ansible fw:&auto -m ansible.builtin.ping`   | One module, once, on those hosts              |
| `--limit`         | `ansible-playbook site.yml --limit web-a-07` | Run the playbook, but **only** on these hosts |

> The labs use `fw:&auto` so a playbook can never touch your hand-built branch m.

<!-- One idea, three places. The labs use fw:&auto so a mistake on branch a can't touch branch m. Reassure students that this is a safety feature, not extra work. About 1 minute. -->

---

## A task is a module call

```yaml
- name: Put the page in place # a label for humans
  ansible.builtin.copy: # the module
      dest: /var/www/html/index.html # arguments
      content: "<h1>Hello</h1>\n"
      mode: "0644"
```

- `name` is printed when it runs, so write it as a sentence
- Arguments describe the **result**: this file, with this content
- No `if file exists` logic: the module checks that for you

<!-- Stress that arguments describe the result, not the steps. There's no if-file-exists logic because the module does that check. About 1 minute. -->

---

## Modules: the actual work

A module is a ready-made tool for **one job**. You describe the result; it checks the machine and **changes only what differs**.

| Module                     | Use it to                     | It does nothing if                 |
| -------------------------- | ----------------------------- | ---------------------------------- |
| `ansible.builtin.copy`     | put a file in place           | the file already matches           |
| `ansible.builtin.template` | fill in a file from variables | the result already matches         |
| `ansible.builtin.iptables` | add a firewall rule           | that rule is already there         |
| `ansible.builtin.service`  | start or stop a service       | it is already in that state        |
| `ansible.builtin.command`  | run any command               | Ansible can't tell: **you** decide |

Options and examples: `ansible-doc ansible.builtin.template`

<!-- The last row matters: command is the escape hatch, and Ansible can't tell whether it needs to run, so that's on you. Mention ansible-doc as the first place to look for help. About 1 minute. -->

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

<!-- They'll use this in A1. Show it live in pod 00 if you can: ansible all -m ping is a satisfying thing to watch run across eight nodes. About 1 minute. -->

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

<!-- Walk the diagram once. The detail worth landing: each task finishes on every host before the next task starts. About 1 minute. -->

---

## Reading the output

```text
changed: [web-a-07]
ok: [web-m-07]
```

Each task prints **one line per host**. The first word says what happened there.

| Word      | What happened on that host           | What you do               |
| --------- | ------------------------------------ | ------------------------- |
| `ok`      | Already correct. Nothing was touched | Nothing                   |
| `changed` | Was wrong. Ansible fixed it          | Expected on a first run   |
| `failed`  | The task hit an error and stopped    | Read the message under it |
| `skipped` | A `when:` condition said no          | Nothing                   |

The `PLAY RECAP` at the end totals each word per host.

<!-- They'll read this output all day, so make sure they know what the four words mean. Failed is the only one that needs action. About 1 minute. -->

---

## Idempotent: run it twice

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

<!-- If they only remember one thing from the talk, it's this. Ask them to say what changed=0 means. The echo x >> file comparison usually makes it click. About 2 minutes. -->

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

<!-- Show the check-then-act loop. This is why running it again is safe, even after a half-finished run. About 1 minute. -->

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

<!-- Show the list once, used twice. Change the list, rerun, and only the difference is applied. The popup covers Jinja2 for people who haven't seen it. Remind them the braces must be quoted. About 2 minutes. -->

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

<!-- Walk left to right: template, variables, finished file. The filling happens on the control node, then the file is copied over. About 1 minute. -->

---

## Templates: the playbook that uses them

```yaml
- name: Harden sshd on the web servers
  hosts: web # no variables listed here: see next slide
  tasks:
      - name: Push the sshd settings
        ansible.builtin.template:
            src: sshd_config.j2 # the template, next to the playbook
            dest: /etc/ssh/sshd_config # where the file lands on each web host
            validate: sshd -t -f %s # test it before it is used
```

- **Variables:** not named here. Ansible finds them by **file name**, next slide
- **Changed or ok:** the file is replaced only if the result **differs**
- **`validate`:** runs on a temp copy (`%s`). If it fails, the old file stays and the task **fails**: a typo cannot lock you out

<!-- The variables aren't named in the playbook, which surprises people. That's the next slide. Spend longer on validate: it's the answer to the typo slide. About 1 minute. -->

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

<!-- Ansible matches the group name to a file name in group_vars. Once they see that, a lot of magic goes away. About 1 minute. -->

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
      notify: Reload nginx # 1

handlers:
    - name: Reload nginx # 2
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

<!-- The usual example is reloading nginx only when its config changed. The notify only fires if the task reports changed. About 1 minute. -->

---

## Handlers: two runs of the same playbook

<div class="mermaid">
flowchart LR
  t["template task"] -- "changed: file was different" --> h["handler runs: reload nginx"]
  t -- "ok: file already matched" --> x["handler skipped"]
</div>

| Run                | Task result | Handler                                |
| ------------------ | ----------- | -------------------------------------- |
| 1st: config edited | `changed`   | **runs**, once, after all tasks finish |
| 2nd: nothing to do | `ok`        | does not run                           |

- Five tasks all notify "Reload nginx"? It still runs **once**, at the end.
- Without a handler you would reload on every run, or forget to reload at all.

<!-- Compare the two runs. A common question is whether five notifying tasks cause five reloads. They don't: the handler runs once, at the end. About 1 minute. -->

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

<!-- You can't get a preview by hand. Run it live if you have a minute: the diff makes the point better than the slide does. About 1 minute. -->

---

## Safety nets: check before you change

<div class="split split-top">
<div>

**`validate:` tests a file before it goes live on the device**

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

<!-- These two stop a bad change before it lands: validate tests the file, assert tests the input. A7 uses validate and A8 uses assert. About 1 minute. -->

---

## Safety nets: undo, and limit the damage

<div class="split split-top">
<div>

**`block / rescue / always`:<br> try it / undo it / report it**

```yaml
- block:
      - ansible.builtin.template: { src: a.j2, dest: /etc/a }
      - ansible.builtin.command: check-a
  rescue:
      - ansible.builtin.copy: { src: a.bak, dest: /etc/a }
  always:
      - ansible.builtin.debug: { msg: "finished" }
```

Tasks in `block` run in order. If one **fails**, `rescue` runs (restore the backup). `always` runs either way.

</div>
<div>

**`serial: 1` sequentially changes one host at a time**

```yaml
- hosts: web
  serial: 1
  tasks:
      - ansible.builtin.template: ...
```

Normally Ansible hits every host at once. With `serial: 1`, a failure on the first host **stops the play** before the other hosts are touched, so one mistake does not become fifty.

</div>
</div>

<!-- Block, rescue and always give you try, undo, report. Serial limits the blast radius. Don't go deep. A8 is where they practise it. About 1 minute. -->

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
2. The **vault password** is the key. Keep it in `.vault_pass`, **never** in git.
3. Anyone with the repo but not the key sees only the scrambled text.

</div>
</div>

<!-- Playbooks live in git, so a password in one stays there. Vault encrypts the file instead. The vault password is the key and never goes in the repo. The next five slides are optional if time is short: A10 covers secrets with OpenBao in the lab, and these slides cover the Azure Key Vault options. About 1 minute. -->

---

## Secrets: using them in a playbook

<div class="split split-top">
<div>

```yaml
- hosts: web
  vars_files:
      - secrets.yml # 1
  tasks:
      - name: htpasswd file
        ansible.builtin.copy:
            content: "admin:{{ hash }}"
            dest: /etc/nginx/.htpasswd
        no_log: true # 2
```

```sh
ansible-playbook site.yml \
  --vault-password-file ./vault-pass.sh   # 3
```

</div>
<div>

1. `vars_files` loads the encrypted file. Its variables (`admin_password`) work like any other.
2. `no_log: true` hides this task's output. Otherwise the password would show in the terminal or logs.
3. Ansible decrypts `secrets.yml` in memory at run time. The password comes from a file or script (next slide).

</div>
</div>

<!-- Three numbered points: load the file, hide the output with no_log, supply the password at run time. Skip if you're cutting the secrets section. -->

---

## Secrets: no plain-text password on your laptop

An **executable** password file is run by Ansible, which reads the password from its output.

<div class="split split-top">
<div>

```sh
#!/bin/sh
# vault-pass.sh: no secret here, safe to commit
gopass show -o ansible/vault
```

```sh
chmod +x vault-pass.sh
ansible-playbook site.yml \
  --vault-password-file ./vault-pass.sh
```

</div>
<div>

1. `gopass` (or `pass`) keeps the password in a GPG-encrypted store.
2. You type your GPG passphrase once; `gpg-agent` caches it. No plain-text file on disk.
3. On Windows, do this inside **WSL2** with `pass` or `gopass`.

</div>
</div>

<!-- A script that prints the password means no secret is saved on disk. Skip if you're cutting the secrets section. -->

---

## Secrets: a shared control node

Many teams, one VM: use **Azure Key Vault**, signed in as **you**.

<div class="split split-top">
<div>

```sh
#!/bin/sh
# vault-pass.sh: no secret here, safe to commit
az keyvault secret show \
  --vault-name team-a-kv \
  --name ansible-vault \
  --query value -o tsv
```

<label for="kv-help" class="pop-trigger">How it works with several teams</label>

</div>
<div>

1. `az login` as yourself, not as the VM: every user on it could borrow the VM's identity.
2. **One vault per team**. Only that team's group can read it, and every read is logged.
3. Each team's repo names its own vault. Another team's vault says "denied".

</div>
</div>

<div class="pop">
<input type="checkbox" id="kv-help" class="pop-toggle">
<div class="pop-overlay">
<label for="kv-help" class="pop-close">close &#10005;</label>
<h3>Several teams, one control node, one vault each</h3>
<p class="pop-sub">An admin sets it up once. After that, every run is checked against <b>who you are</b>. Follow the numbers.</p>
<pre class="pop-code"><code>az keyvault create -n team-a-kv -g rg --enable-rbac-authorization true   # 1
az keyvault secret set --vault-name team-a-kv -n ansible-vault --value "$PW"
az role assignment create --assignee-object-id $TEAM_A_GROUP_ID \
  --role "Key Vault Secrets User" --scope $TEAM_A_KV_ID                  # 1
az login                                                                 # 3</code></pre>
<div class="leak-grid cols-3">
<div class="leak"><i># 1 &middot; once per team</i><b>A vault and a group each</b><code>team-a-kv</code> holds the vault password. Only Team A's Entra group can read it</div>
<div class="leak"><i># 2 &middot; once per team</i><b>The repo names its vault</b>A Linux group owns the team's repo. Its <code>vault-pass.sh</code> names that team's vault. Nothing secret is in it</div>
<div class="leak"><i># 3 &middot; each session</i><b>Sign in as you</b><code>az login</code> proves who you are to Azure. The VM's own identity is not used<em>Everyone on the VM could borrow it</em></div>
<div class="leak"><i># 4 &middot; each run</i><b>Run it from the repo</b>The script asks Key Vault for the password. Azure checks your group, then returns it. It stays in memory</div>
<div class="leak"><i># 5 &middot; in two teams?</i><b>The repo picks the vault</b>You can read both vaults, but each repo's script names only its own. Run from Team A's repo, you unlock Team A's secrets</div>
<div class="leak"><i># 6 &middot; wrong team</i><b>Denied, and logged</b>Team B running team A's script gets <code>Forbidden</code>. Key Vault logs every read and every refusal</div>
</div>
</div>
</div>
</div>

<!-- For teams on a shared VM. The point is that access is checked against who you are, not who the VM is. The popup has the setup steps. I haven't run the Azure Key Vault part in this workshop's pods, so treat it as an example of the pattern. Skip if you're short on time. -->

---

## Secrets: how a team does it

The encrypted `secrets.yml` is in git in all three. Only the **vault password** differs.

|                    | One person                        | Team on a shared VM                      | Pipeline runs it                              |
| ------------------ | --------------------------------- | ---------------------------------------- | --------------------------------------------- |
| **Vault password** | `pass`/`gopass`, read by a script | **Key Vault**, one per team, read as you | **Key Vault**, read by the runner's identity  |
| **Who holds it**   | you                               | no one: your team group is checked       | no one: the pipeline fetches it               |
| **Best for**       | learning, small setups            | many teams, one audited node             | `--check --diff` on the PR, real run on merge |

<!-- Compare the three columns. Only the vault password changes, and the encrypted file is the same everywhere. Skip if you're cutting the secrets section. -->

---

## Secrets: rules for every team

1. **Never commit** the password or leave it in a plain file.
    - Read it with a script: `pass`/`gopass` on a laptop
    - Key Vault on a shared server or pipeline.
2. **`no_log: true`** on every task that touches a secret.
3. **One vault password per environment**, so a leaked dev key cannot open production (vault IDs).
4. **Rotate** the key when someone leaves: `ansible-vault rekey secrets.yml`.
5. **Review changes by pull request**, so a secret never changes unseen.

<!-- Five rules, read them quickly. This is a good place to stop and take questions before the pod. About 1 minute. -->

---

<!-- _class: section-title -->

# Part 3

## Your pod

<!-- Part 3 is the pod itself. Keep it short and get them to a terminal. -->

---

## One pod per student

<div class="mermaid short">
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
  sw -- "trunk: VLANs 10 + 20 tagged" --- fw["fw<br/>firewall"]
</div>

- **pc** is a student's computer, **web** is a web server, **fw** is the firewall between them
- `pc` and `web` are on separate networks (VLANs), so they cannot talk directly
- Everything between them goes through `fw`, which checks its rules first

<label for="vlan-help" class="pop-trigger">New to VLANs? What the trunk is</label>

<div class="pop">
<input type="checkbox" id="vlan-help" class="pop-toggle">
<div class="pop-overlay">
<label for="vlan-help" class="pop-close">close &#10005;</label>
<h3>VLANs and the trunk</h3>
<p class="pop-sub">Why the pc cannot talk straight to the web server. Skip this if you know networking.</p>
<div class="leak-grid cols-4">
<div class="leak"><i>1 VLAN</i><b>one switch, two networks</b>A label on switch ports. Same label: same network. Different label: walled off, as if on separate switches</div><div class="leak"><i>2 access port</i><b>plain frames, one VLAN</b>Where <code>pc</code> and <code>web</code> plug in. They know nothing about VLANs; the switch adds the port's VLAN on entry and removes it on exit</div><div class="leak"><i>3 trunk</i><b>both VLANs, one cable</b>The <code>sw</code> to <code>fw</code> link. Each frame carries a tag (802.1Q) with its VLAN number, so the far end can tell them apart</div><div class="leak"><i>4 router</i><b>the only way across</b>VLAN 10 is <code>10.10.10.0/24</code>, VLAN 20 is <code>10.10.20.0/24</code>. Only a router, here <code>fw</code>, moves traffic between subnets</div>
</div>
<div class="mermaid short">
flowchart LR
  pc["pc<br/>VLAN 10"] -- "access: plain" --- sw["sw"]
  web["web<br/>VLAN 20"] -- "access: plain" --- sw
  sw == "trunk: tag 10 and tag 20" === fw["fw<br/>router"]
</div>
<p class="pop-src">A frame from <code>pc</code> to <code>web</code> goes up the trunk tagged 10, <code>fw</code> checks its rules, and it comes back tagged 20. See it with <code>bridge vlan show</code> on <code>sw</code> and <code>ip addr</code> on <code>fw</code>. Labs M2, M3, A2 and A3 build this.</p>
</div>
</div>

<!-- Start with the picture, not the networking. The point is that pc and web are on separate networks and everything crosses the firewall. Nobody needs to know VLANs: open the popup only if someone asks. About 2 minutes. -->

---

## Follow one request

Say `pc` wants the web page that `web` serves. Follow that request:

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
  pc -- "1. pc asks web for its page" --> sw
  sw -- "2. trunk, tagged VLAN 10" --> fw
  fw -- "3. rules ok? back tagged VLAN 20" --> sw
  sw -- "4. page request delivered to web" --> web
</div>

The switch is used **twice**. The firewall is the only place the request can cross, so it is where the rules live.

<!-- Trace the numbers on the diagram. The switch is used twice and the firewall is the only place the request can cross, so that's where the rules live. About 1 minute. -->

---

## Why a network?

You do not need to know networking. It gives us:

- **Real services** with real failure modes: a firewall that blocks, a server that will not reload
- **Something you can test**: "can the pc reach the web server?" is a yes or no
- **Several kinds of machine** to show one tool managing them all

The firewall is only the thing being configured. **The lesson is Ansible.**

<!-- Say it plainly: the network is a prop. It gives us real failures and a yes or no test. The lesson is Ansible. About 30 seconds. -->

---

## Twice: branch m and branch a

<div class="mermaid">
flowchart LR
  subgraph m["Branch m: by hand"]
    mpc["pc"] --- msw["sw"] --- mfw["fw"] --- mweb["web"]
  end
  subgraph a["Branch a: by playbook"]
    apc["pc"] --- asw["sw"] --- afw["fw"] --- aweb["web"]
  end
  you["You"] -- "ssh + shell" --> mpc
  you -- "ansible-playbook" --> apc
</div>

Eight nodes per student. Both branches **start identical** and are isolated from each other.

<!-- Each student has eight nodes, two copies of the same four. Both branches start identical and they're isolated, so a mistake on one can't hurt the other. About 1 minute. -->

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

<!-- Pod number comes from the login name. Node names are role-branch-pod. Ansible already has the password, so playbooks won't ask. You're root on the nodes, so there's no sudo. About 1 minute. -->

---

## Branch m is the by-hand run, branch a is the playbook

|               | Branch m (Part 1)                 | Branch a (Part 2)            |
| ------------- | --------------------------------- | ---------------------------- |
| You use       | `ssh` and a shell                 | `ansible-playbook`           |
| Starts        | closed: ping only                 | closed: ping only            |
| Prove traffic | `probe.yml`                       | `probe.yml`                  |
| Finish        | you stop when it works            | `dojo netlab check A<n>` passes |

You build the result by hand first. Then you write the playbook that says the same thing, and branch a must end in the **same state** as branch m.

> If `compare.yml` says DIFFERENT, one of the two branches is wrong. Find out which.

<!-- Branch m is the reference. The question is whether the playbook ends where your hands ended. Compare.yml answers that in A9. About 1 minute. -->

---

## The tools that check you

```sh
ansible-playbook probe.yml -e branch=a -e expect=allowed
ansible-playbook compare.yml
dojo netlab check A5
```

| Tool                  | Question it answers                                       |
| --------------------- | --------------------------------------------------------- |
| `probe.yml`           | Does traffic get through? **PASS** if it matches `expect` |
| `compare.yml`         | Do the firewall rules and nginx config on m and a match?  |
| `dojo netlab check A<n>` | Does the whole lab pass, from outside your pod?           |

<!-- Three tools, three questions. Probe checks traffic, compare checks the two branches, the checker looks at the whole lab from outside the pod. The checker allows about six runs a minute per student, so tell them to read the output before rerunning. About 1 minute. -->

---

<!-- _class: section-title -->

# Part 4

## The labs

<!-- Part 4 is the lab path and where to get help. -->

---

## Every lab comes in two passes

<div class="mermaid">
flowchart LR
  h["Part 1: M lab<br/>by hand on branch m"] --> p["Part 2: A lab<br/>playbook on branch a"]
  p --> v["Prove it<br/>probe, compare, check"]
  v --> t["The twist<br/>rerun, undo, change one value"]
</div>

Each lab page states the **goal** and the steps. You do the job by hand first, then say it as a playbook and compare the results.

<!-- Hands first, then playbook, then proof, then the twist. The twist is where the playbook wins: rerun it, undo it, change one value. About 1 minute. -->

---

## The path

| Part 1: by hand (branch m) | Part 2: as playbooks (branch a) |
| -------------------------- | ------------------------------- |
| M1 Look around the pod     | A1 Orientation                  |
| M2 to M3 VLANs and trunk   | A2 to A3 The switch             |
| M4 Serve a web page        | A4 A first playbook             |
| M5 Open HTTP and HTTPS     | A5 Variables and loops          |
| M6 HTTPS certificate       | A6 Idempotency                  |
| M7 Harden SSH              | A7 Templates and validate       |
| M8 Lock the server down    | A8 Errors and rollback          |
| M9 Rebuild from clean      | A9 Capstone (A10, A11 optional) |

<!-- Each A lab repeats the M lab with the same number. A10 and A11 are stretch and have no by-hand twin. About 1 minute. Time check: the M labs take about 105 minutes and the A labs about 150. -->

---

## Habits worth keeping

1. **Describe the end state**, not the steps
2. **Run it twice**: the second run must say `changed=0`
3. **Preview first** with `--check --diff`
4. **Validate before you apply** anything that can lock you out
5. **Test, and roll back** on failure
6. **Keep it in git**: the playbook is the record

<!-- A recap of what the labs practise. Don't read the list: ask which ones they expect to use first. About 1 minute. -->

---

## If you get stuck

- `ansible-playbook verify_topology.yml`: is the pod healthy?
- `ansible-playbook reset_fw.yml -e branch=a`: back to the baseline
- `dojo netlab check A<n>`: what is still wrong, line by line
- Read the error: Ansible says which task, which host, and why
- Put your hand up: the facilitator has a pod of their own

<!-- Tell them you have a pod of your own and can reproduce their problem without touching theirs. The first command to run is verify_topology.yml. About 1 minute. -->

---
<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: "[&larr; Hub](index.md)" -->

# Let's go

## Next: [labs.md](labs.md) for what each lab covers, then your terminal

Keep [cheat-sheet.md](cheat-sheet.md) open in another tab. Ask for help any time. This is a lab, not a test.

<!-- Send them to labs.md for a two-minute overview, then to the Lab M1 page and their terminal in ~/netlab. Suggested timing for the whole session is in FACILITATOR.md. -->

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
