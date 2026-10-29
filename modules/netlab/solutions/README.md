# Netlab reference solutions (facilitator only)

Never copied to students' homes. One folder per lab, named like the lab folder in `terminal/seed/labs/`
(`S1` and `S2` are the switch labs A2 and A3; the folder names keep the old numbers, so lab folder `2-variables-loops` is lab A5). Each has the finished `site.yml` and its templates.

To try one on a pod, copy it over the lab folder and put its `group_vars/` where Ansible reads them:

```sh
cd ~/netlab
cp -r /path/to/solutions/2-variables-loops/. labs/2-variables-loops/
mv labs/2-variables-loops/group_vars/*.yml group_vars/      # labs 2, 4, 7, 8 have group_vars; move, don't copy:
                                                            # a copy next to the playbook outranks ~/netlab/group_vars
ansible-playbook labs/2-variables-loops/site.yml
```

Order and end states:

| Folder (lab) | Needs | End state |
|---|---|---|
| 1-first-playbook (A4) | | page template on the web nodes |
| 2-variables-loops (A5) | | LAB allows tcp 80, 443 from 10.10.10.0/24 to 10.10.20.10 (`allowed_ports` in `group_vars/fw.yml`) |
| 3-idempotency (A6) | 2 for the curl test | `/etc/nginx/tls/web.{crt,key}`, `http.d/tls.conf`, HTTPS 200 |
| 4-templates-validate (A7) | | `sshd_config` with MaxAuthTries 3, LoginGraceTime 20, X11Forwarding no (`group_vars/web.yml`) |
| 5-vault (A10) | 2; the openbao module | `fw-repo/` and `sw-repo/`, each with `vault-pass.sh` (reads its OpenBao vault), an encrypted `secrets.yml` (see `secrets.yml.example`) and a `site.yml` that puts the secret on its node |
| 6-lockdown (A8) | web server running | LAB: 80, 443 allow, ICMP drop, final DROP; tests from the pc; rescue flushes LAB |
| 7-roles (A11) | | `roles/web` + `roles/firewall`, same end state as 1-4 and 6 (not 5) |
| 8-capstone (A9) | 1-4, 6 siblings present | `reset_fw.yml -e branch=a`, then `site.yml` twice; second run `changed=0` |

Lab 8's `site.yml` imports its sibling lab folders, so copy all of them, or swap the imports for the lab 7 roles.
