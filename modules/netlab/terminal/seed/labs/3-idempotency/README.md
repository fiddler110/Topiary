# Lab 3: Idempotency and check mode, HTTPS on the web server

Goal: the web server answers HTTPS on 443 with a self-signed certificate. Needs lab 2 (port 443 open).

## 1. By hand, on branch m

On `web-m-@POD@`: make a directory `/etc/nginx/tls` and create a self-signed certificate and key there, `web.crt` and `web.key`
(`openssl req -x509 ...`, one year, subject `/CN=web`, no passphrase). Then add `/etc/nginx/http.d/tls.conf` with one `server`
block: `listen 443 ssl;`, `ssl_certificate`, `ssl_certificate_key`, `root /var/www/html;`. Check it with `nginx -t`, then `nginx -s reload`.
From the pc: `curl -k https://10.10.20.10/` should return the page.

## 2. With a playbook, on branch a

Fill in `labs/3-idempotency/site.yml`:

```sh
ansible-playbook labs/3-idempotency/site.yml
```

You will use:

- `ansible.builtin.file` for the directory (and key mode `0600`)
- `ansible.builtin.command` with **`creates:`**, so the certificate is made once and never replaced
- `ansible.builtin.template` for `tls.conf`, a handler for the reload
- `changed_when` and `failed_when` to say what "changed" means for a command

## 3. Prove it

```sh
ansible-playbook labs/3-idempotency/site.yml              # changed
ansible-playbook labs/3-idempotency/site.yml              # changed=0
ansible-playbook probe.yml -e branch=a -e port=443 -e expect=allowed
ansible-playbook compare.yml                              # tls.conf matches m (write it with the same lines)
```

## The twist

Check mode shows what **would** change without touching anything. Edit `tls.conf.j2` (say, add `server_tokens off;`), then:

```sh
ansible-playbook labs/3-idempotency/site.yml --check --diff
```

You get a diff and no change. Note the `command` task is skipped in check mode: why is `creates:` the only reason it is safe to run twice?
Then run it for real and compare against m, where you would be hand-editing a file with no preview.

Next lab: `labs/4-templates-validate/README.md`.
