# Lab M9: Rebuild from clean

You now have a firewall, a web server and an sshd that each took several steps to configure. This lab asks the question that makes the case for automation: **if this were destroyed, how long would it take to rebuild it by hand, and would it be the same?** You will reset branch m to the starting state and rebuild it, timing yourself.

**Part 1: by hand, on branch m.** About 20 min. You will do this again as a playbook in [Lab A9](labA9.md).

Your pod number is the number in your login name (`student07` is pod 07). The page fills it in where you see it below; if you still see `@POD@`, use that number.

> **Starting here?** This lab rebuilds the work of [M4 to M8](labM4.md). If you skipped any, do those first, or you will have nothing to compare.

---

## In this lab

| Command | What it does |
| ------- | ------------ |
| `ansible-playbook reset_fw.yml -e branch=m` | Put branch m's firewall and web server back to the baseline |
| `ansible-playbook probe.yml` | Prove each part of the final state |
| `history` | List the commands you have typed in this shell |
| `date` | Print the time, so you can note when you start and finish |

---

## The idea: a rebuild is a test of your knowledge

A configuration you can't rebuild is a configuration you don't really have. Real outages (a failed disk, a bad change, a new hire's first day) all end in the same question: *what exactly was on that machine?* Today the answer exists only in your head and your terminal history. That is what you are about to measure.

---

## 1. Write down the target

Before you reset, write down what the finished branch m must contain. Each item is something you built:

| From | Must be true |
| ---- | ------------ |
| M4 | the web server serves your page |
| M5 | `LAB` allows TCP 80 and 443 from the pc network to the web server |
| M6 | a certificate in `/etc/nginx/tls` and `tls.conf` in `/etc/nginx/http.d` |
| M7 | `sshd` has `MaxAuthTries 3`, `LoginGraceTime 20`, `X11Forwarding no` |
| M8 | `LAB` also drops ping and everything else |

(The switch from M2 and M3 stays as it is. Only the firewall and web server are reset.)

---

## 2. Reset and start the clock

```sh
cd ~/netlab
ansible-playbook reset_fw.yml -e branch=m
ansible-playbook probe.yml -e branch=m -e expect=blocked
```

`reset_fw.yml` empties `LAB`, restores the baseline `FORWARD` rules, puts back nginx's default site and page, removes the certificate, and restores the original `sshd_config`. The management login is never touched, so a bad rule cannot lock Ansible out. The probe should print `PASS` for "blocked": you are back at the start.

Now rebuild everything from the table above. Use your own notes and the earlier labs, and keep a rough tally as you go. Note the time you start:

```sh
date
```

**Your turn:** as you work, count (a) how many commands you type and (b) how many separate SSH sessions you open. Note any step where you made a mistake and had to repeat it.

---

## 3. Prove the rebuild

When you think it is done, run the same probes you used in M8:

```sh
ansible-playbook probe.yml -e branch=m -e expect=allowed
ansible-playbook probe.yml -e branch=m -e port=443 -e expect=allowed
ansible-playbook probe.yml -e branch=m -e port=8080 -e expect=blocked
ansible-playbook probe.yml -e branch=m -e proto=icmp -e expect=blocked
ssh root@web-m-@POD@ "sshd -T | grep -Ei 'maxauthtries|logingracetime|x11forwarding'"
```

All four probes should print `PASS` and `sshd -T` should show `maxauthtries 3`, `logingracetime 20`, `x11forwarding no`.

---

## 4. Take stock

Fill this in honestly. There is no right answer; the numbers are the point.

| Question | Your answer |
| -------- | ----------- |
| How long did the rebuild take? | |
| How many commands did you type? | |
| How many SSH sessions? | |
| How many mistakes or repeats? | |
| Could a colleague repeat it from your notes alone? | |

<!-- dojo-reveal: What the comparison is for -->

In Lab A9 you will rebuild **branch a** from the same clean start with one `site.yml`, then run it a second time and see `changed=0`. Keep your numbers: you will compare your branch-m rebuild against one command and a few seconds, and against the guarantee that the two branches end identical.

<!-- /dojo-reveal -->

---

## Recap

- A reset-and-rebuild is the honest test of whether you really know how a system is configured.
- By hand, the knowledge lives in your head and shell history; it is slow, order-dependent and hard to repeat exactly.
- `probe.yml` gives you a repeatable, objective test of the *result*, no matter how you got there.

**Next:** [Lab A1](labA1.md). The playbook half of the workshop starts here, and every Part 1 job comes back as code.
