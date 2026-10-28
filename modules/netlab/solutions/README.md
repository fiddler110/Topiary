# Netlab reference solutions (facilitator only)

Never copied to students' homes. One folder per lab, named like the lab folder in `terminal/seed/labs/`
(`S1`-`S3` are the switch labs). Each has the finished `site.yml` and its templates.

To try one on a pod, copy it over the lab folder and put its `group_vars/` where Ansible reads them:

```sh
cd ~/netlab
cp -r /path/to/solutions/2-variables-loops/. labs/2-variables-loops/
mv labs/2-variables-loops/group_vars/*.yml group_vars/      # labs 2, 4, 7, 8 have group_vars; move, don't copy:
                                                            # a copy next to the playbook outranks ~/netlab/group_vars
ansible-playbook labs/2-variables-loops/site.yml
```

Order and end states:

| Lab | Needs | End state |
|---|---|---|
| 1 | | page template on the web nodes |
| 2 | | LAB allows tcp 80, 443 from 10.10.10.0/24 to 10.10.20.10 (`allowed_ports` in `group_vars/fw.yml`) |
| 3 | 2 for the curl test | `/etc/nginx/tls/web.{crt,key}`, `http.d/tls.conf`, HTTPS 200 |
| 4 | | `sshd_config` with MaxAuthTries 3, LoginGraceTime 20, X11Forwarding no (`group_vars/web.yml`) |
| 5 | 2; vault file (see `secrets.yml.example`) | `/admin` behind basic auth; the lab text uses `.vault_pass` |
| 6 | web server running | LAB: 80, 443 allow, ICMP drop, final DROP; tests from the pc; rescue flushes LAB |
| 7 | | `roles/web` + `roles/firewall`, same end state as 1-4 and 6 (not 5) |
| 8 | 1-4, 6 siblings present | `reset_fw.yml -e branch=a`, then `site.yml` twice; second run `changed=0` |

Lab 8's `site.yml` imports its sibling lab folders, so copy all of them, or swap the imports for the lab 7 roles.
