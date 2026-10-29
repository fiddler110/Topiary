# Lab M7: Harden SSH

SSH is how you, and Ansible, get into every node, so it is also what an attacker will try first. Hardening means tightening the SSH server's settings so it is harder to abuse. This lab changes three of them, and shows how easy it is to lock yourself out with a one-character typo.

**Part 1: by hand, on branch m.** About 10 min. You will do this again as a playbook in [Lab A7](labA7.md).

Your pod number is the number in your login name (`student07` is pod 07). The page fills it in where you see it below; if you still see `@POD@`, use that number.

---

## In this lab

| Command | What it does |
| ------- | ------------ |
| `sshd -T` | Print the settings the SSH server *actually* uses |
| `sshd -t` | **T**est the config file for errors without applying it |
| `sshd -t -f <file>` | Test a different file |
| `kill -HUP $(cat /run/sshd.pid)` | Tell the running sshd to reload its configuration |
| `grep -Ei 'word1\|word2'` | Show only lines containing either word, ignoring case |

---

## The idea: the three settings

| Setting | Target | Why |
| ------- | ------ | --- |
| `MaxAuthTries 3` | 3 | An attacker guessing passwords gets fewer tries per connection (the default is 6) |
| `LoginGraceTime 20` | 20 seconds | A connection that does not log in quickly is closed, so idle half-open connections cannot pile up (default 120) |
| `X11Forwarding no` | no | Do not let the server forward graphical sessions; nobody here needs it |

You keep everything else so you can still log in: `Port 22`, `PermitRootLogin yes`, `PasswordAuthentication yes` and the `Subsystem sftp` line.

The danger is that **the SSH server is how you manage the machine**. If you load a broken config, you can lose the node.

---

## 1. See what is in force now

```sh
ssh root@web-m-@POD@
sshd -T | grep -Ei 'maxauthtries|logingracetime|x11forwarding'
```

`sshd -T` prints every setting with its **effective** value, including defaults the file does not mention. You should see `maxauthtries 6`, `logingracetime 120` and `x11forwarding no`.

**Your turn:** `X11Forwarding` is already `no` by default here, so why set it? Think before you open the answer.

<!-- dojo-reveal: Why set a value that is already right? -->

Defaults can change between versions, and a config that states what you want is documentation and protection. If the default ever changed, an explicit `no` would still hold. It also means a check can verify the *file*, not just whatever today's default happens to be. Good configuration says what it means.

<!-- /dojo-reveal -->

---

## 2. Edit the file

Remove any old copies of these three settings, then add yours:

```sh
sed -i '/^MaxAuthTries/d;/^LoginGraceTime/d;/^X11Forwarding/d' /etc/ssh/sshd_config
printf 'MaxAuthTries 3\nLoginGraceTime 20\nX11Forwarding no\n' >> /etc/ssh/sshd_config
cat /etc/ssh/sshd_config
```

`sed -i '/^Word/d'` deletes, in place, every line starting with that word (so you do not end up with two conflicting values). `printf ... >>` appends the three new lines. Check the file still has `Port 22`, `PermitRootLogin yes` and `PasswordAuthentication yes`.

---

## 3. Test first, then reload

```sh
sshd -t && echo config ok
```

`sshd -t` reads the file and complains if anything is wrong. If it is fine it prints nothing and exits successfully, so `&& echo config ok` prints `config ok`. Only then:

```sh
kill -HUP $(cat /run/sshd.pid)
sshd -T | grep -Ei 'maxauthtries|logingracetime|x11forwarding'
```

`kill -HUP` does not kill anything: it sends the "hang up" signal, which sshd treats as **reload your configuration**. The new `sshd -T` shows `maxauthtries 3`, `logingracetime 20`, `x11forwarding no`. Your current session stays open: a reload only affects *new* connections. Open a second terminal and run `ssh root@web-m-@POD@` to prove you can still log in before you close the first.

---

## 4. See what a typo does (safely)

Do **not** try this on the live file. Copy it and break the copy:

```sh
cp /etc/ssh/sshd_config /tmp/sshd_test
echo 'MaxAuthTries three' >> /tmp/sshd_test
sshd -t -f /tmp/sshd_test
```

The test refuses it: `MaxAuthTries integer value invalid`. That message is the entire value of `sshd -t`. If you had put the same typo in the real file and sent the reload signal, the next time sshd restarted it would refuse to start, and you would have no way in to fix it.

---

## Check it

Look at the effective values yourself, from the web node:

```sh
sshd -T | grep -Ei 'maxauthtries|logingracetime|x11forwarding'
```

You want `maxauthtries 3`, `logingracetime 20`, `x11forwarding no`. (There is no automatic check for this by-hand lab. The checker for Lab A7 reads the same values.)

---

## Recap

- `sshd -T` shows effective settings; `sshd -t` tests a config file.
- **Test before you reload**, and keep a second session open when you change anything that can lock you out.
- `kill -HUP` reloads without disconnecting current users.
- Setting a value that is already the default is still good practice: say what you mean.
- Lab A7 gives Ansible the same safety net: the new file is tested **before** it replaces the real one.

**Next:** [Lab M8](labM8.md): lock the web server down so only web traffic gets through.
