---
marp: true
theme: default
paginate: true
size: 16:9
html: true
style: |
  @import url('assets/themes/labs.css');
footer: '[&larr; Labs](lab-index.md) &nbsp;|&nbsp; Ansible on a Small Network | Lab Overview'
---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: "[&larr; Labs](lab-index.md)" -->

# Lab Overview

## What each lab covers, before you dive in

Two parts: **by hand on branch m**, then **as playbooks on branch a**.
Nine labs by hand (M1 to M9), nine as playbooks (A1 to A9), and two stretch labs.

<p class="nav">Keep <code>cheat-sheet.md</code> open in another tab while you work.</p>

<!-- Two minutes. The point to land: every A lab repeats the M lab with the same number, so by the time they write the playbook they already know what it has to say. -->

---

## Before you start

```sh
cd ~/netlab
ansible-playbook verify_topology.yml
```

Green for every node means your pod is ready. Your pod number is in your login name: `student07` is pod 07.

> The lab pages are read here. You do the work in `~/netlab` in your terminal.

<!-- Have everyone run this now. If a whole pod shows UNREACHABLE, the pods are probably still starting after a full-class launch. Give it a minute and run it again before you start digging. -->

---

## Part 1: by hand, on branch m

| Lab | Job | Time |
| --- | --- | ---- |
| **M1** | Look around the pod | ~10 min |
| M2 | VLANs and access ports | ~10 min |
| M3 | Trunk and router-on-a-stick | ~10 min |
| M4 | Serve a web page | ~10 min |
| M5 | Open HTTP and HTTPS | ~10 min |
| M6 | HTTPS with a self-signed certificate | ~10 min |
| M7 | Harden SSH | ~10 min |
| M8 | Lock the server down (segmentation policy) | ~15 min |
| M9 | Rebuild from clean | ~20 min |

<!-- About 105 minutes in total. M9 is timed on purpose: write down how long it took and how many commands, because A9 uses those numbers. M labs have no checker. Use probe.yml to prove traffic. -->

---

## Part 2: as playbooks, on branch a

| Lab | Topic | Time |
| --- | ----- | ---- |
| **A1** | Orientation: inventory, ad-hoc commands, facts | ~10 min |
| A2 | VLANs and access ports, build it yourself | ~20 min |
| A3 | Trunk and router-on-a-stick | ~20 min |
| A4 | A first playbook: the web page | ~15 min |
| A5 | Variables, loops, conditionals | ~15 min |
| A6 | Idempotency and check mode: HTTPS | ~15 min |
| A7 | Templates, handlers, validate: harden SSH | ~15 min |
| A8 | Errors, rollback and tests: lock it down | ~20 min |
| A9 | Capstone: from clean to done | ~20 min |

<!-- About 150 minutes in total. Each A lab builds on the one before, so they go in order. dojo netlab check A<n> gives a PASS or FAIL line per assertion. -->

---

## The stretch labs

<div class="cards">
<div>
<h3>Lab A10: Secrets with OpenBao</h3>
<p>Keep passwords out of every file you could commit. About 25 min. Needs only a running pod.</p>
</div>
<div>
<h3>Lab A11: Roles and structure</h3>
<p>Move the playbooks you wrote into roles. About 20 min. Needs A4 to A8 finished.</p>
</div>
</div>

<!-- Skip these if time is short. A11 is not checked by the pod checker beyond a roles/ folder existing, so look at the student's roles yourself. -->

---

## The twist in every lab

<div class="flow">
<span><b>1</b><br>by hand<br><small>branch m</small></span>
<span>→</span>
<span><b>2</b><br>playbook<br><small>branch a</small></span>
<span>→</span>
<span><b>3</b><br>run it twice</span>
<span>→</span>
<span><b>4</b><br>check</span>
</div>

Each lab ends with something you can't do by hand: rerun it, preview it, undo it or change one value. That's where the playbook earns its keep.

<!-- This is the idea to keep repeating out loud. In A9, compare.yml shows whether the two branches ended in the same state. If it says DIFFERENT, one of them is wrong, and finding out which is the lesson. -->

---

## Getting unstuck

- `ansible-playbook verify_topology.yml` tells you whether the pod is healthy. It's safe to run any time.
- `ansible-playbook reset_fw.yml -e branch=a` puts the firewall and web node back to the baseline. Use `ansible-playbook reset_switch.yml -e branch=a` for the switch.
- `dojo netlab check A<n>` shows what's still wrong, line by line.
- You can't break anyone else's pod. Stuck for more than a minute or two? Ask the facilitator.

<!-- Tell the room to read the checker output before rerunning it; it limits runs to about six a minute. -->

---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: "[&larr; Labs](lab-index.md)" -->

# Ready

## Open Lab M1 and start in `~/netlab`

<p class="nav">Next: <a href="cheat-sheet.md">Cheat sheet &rarr;</a> &middot; <a href="lab-index.md">&larr; Back to labs</a></p>
