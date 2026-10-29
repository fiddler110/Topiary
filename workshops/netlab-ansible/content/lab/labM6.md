# Lab M6: HTTPS with a self-signed certificate

Port 443 is open on the firewall but the web server is not listening on it. In this lab you turn on HTTPS: you create a certificate and key, tell nginx to use them, and check that it works. It is a good lab for seeing **why configuration changes are done in a careful order**: create files, test the config, then reload.

**Part 1: by hand, on branch m.** About 10 min. You will do this again as a playbook in [Lab A6](labA6.md).

Your pod number is the number in your login name (`student07` is pod 07). The page fills it in where you see it below; if you still see `@POD@`, use that number.

> **Starting here?** You need port 443 open from [Lab M5](labM5.md).

---

## In this lab

| Command | What it does |
| ------- | ------------ |
| `openssl req -x509 ...` | Create a self-signed certificate and its private key |
| `chmod 600 <file>` | Make a file readable by its owner only |
| `nginx -t` | **T**est the nginx configuration without applying it |
| `nginx -s reload` | Tell the running nginx to re-read its configuration |
| `ss -ltn` | Check which TCP ports are being listened on |
| `curl -k https://...` | Fetch an HTTPS page, ignoring certificate trust problems |

---

## The idea: certificates and trust

HTTPS does two jobs. It **encrypts** the traffic, and it lets the client check **who it is talking to** using a certificate. A certificate normally comes from a public authority that browsers already trust. For a lab we make our own, a **self-signed** certificate: it encrypts perfectly well, but nothing vouches for it, so browsers and `curl` warn about it.

Two files are involved:

- the **certificate** (`web.crt`) is public and is handed to every client;
- the **private key** (`web.key`) must stay secret on the server. Anyone who has it can impersonate the server, so only root should be able to read it.

---

## 1. Create the certificate and key

```sh
ssh root@web-m-@POD@
mkdir -p /etc/nginx/tls
openssl req -x509 -newkey rsa:2048 -nodes -days 365 -subj /CN=web \
  -keyout /etc/nginx/tls/web.key -out /etc/nginx/tls/web.crt
chmod 600 /etc/nginx/tls/web.key
ls -l /etc/nginx/tls
```

What each part of the `openssl` command says:

| Part | Meaning |
| ---- | ------- |
| `req -x509` | make a self-signed certificate directly (not a request for someone else to sign) |
| `-newkey rsa:2048` | also generate a new 2048-bit RSA key |
| `-nodes` | do not protect the key with a passphrase, so nginx can start unattended |
| `-days 365` | valid for one year |
| `-subj /CN=web` | the certificate's name, so it does not stop to ask you questions |
| `-keyout`, `-out` | where to write the key and the certificate |

`openssl` prints a row of dots and plus signs while it searches for random numbers; that is progress output, not an error. `ls -l` should show `web.key` as `-rw-------` (owner only) and `web.crt` as `-rw-r--r--`.

---

## 2. Tell nginx to use them

nginx reads every `*.conf` file in `/etc/nginx/http.d/`. Add one for HTTPS:

```sh
cat > /etc/nginx/http.d/tls.conf <<'CONF'
server {
  listen 443 ssl;
  ssl_certificate /etc/nginx/tls/web.crt;
  ssl_certificate_key /etc/nginx/tls/web.key;
  root /var/www/html;
}
CONF
```

A `server` block describes one site: `listen 443 ssl` means "answer on port 443 using TLS", the two `ssl_` lines point at your files, and `root` is the same document folder as the HTTP site, so both serve the same page.

---

## 3. Test before you reload

```sh
nginx -t
nginx -s reload
ss -ltn
```

`nginx -t` reads the whole configuration and says `syntax is ok` or points at the broken line, **without touching the running server**. Always do this first: a broken config that you load can take the site down. `nginx -s reload` then asks the running nginx to pick up the new file gracefully, without dropping existing connections. `ss -ltn` should now list port **443** next to 80 and 22 (if 443 is not there yet, give the reload a second and run it again).

**Your turn:** if you had skipped `nginx -t` and made a typo in `tls.conf`, what would `nginx -s reload` have done? Decide before you read on.

<!-- dojo-reveal: Reload with a broken config -->

A reload of a broken config is refused and the old configuration keeps running, so the damage is usually small. But if the process is *restarted* with a broken file it will not start at all and the site stays down until you fix it. `nginx -t` shows you the problem first, either way. Lab A6 puts this test inside the playbook.

<!-- /dojo-reveal -->

---

## 4. Test from the pc

```sh
exit
ssh root@pc-m-@POD@
curl -k https://10.10.20.10/
curl https://10.10.20.10/
```

The first, with `-k` (insecure), prints your page: HTTPS works. The second, without `-k`, **fails** with a certificate problem. That is the trust issue from the start of the lab, shown for real: the connection could be encrypted, but `curl` has no reason to believe this server is who it says. To see the certificate that was offered, run `curl -vk https://10.10.20.10/ 2>&1 | grep -i subject`. You should see `subject: CN=web`.

---

## Check it

```sh
cd ~/netlab
ansible-playbook probe.yml -e branch=m -e port=443 -e expect=allowed
```

`PASS` means HTTPS gets through the firewall and the server answers. (The probe uses `curl -k`, because it checks reachability, not trust.)

---

## Recap

- A certificate says who the server is; the private key proves it. The key must be `chmod 600`.
- A **self-signed** certificate encrypts but is not trusted, so clients need `-k` (or to be told to trust it).
- `nginx -t` before `nginx -s reload`: test first, then apply.
- That is five separate steps on one server. Notice which ones are safe to repeat and which are not (running `openssl` again would replace your certificate); Lab A6 is about that.

**Next:** [Lab M7](labM7.md): harden SSH on the web server.
