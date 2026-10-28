# Lab 5: Secrets with Vault (stretch)

Goal: `/admin` on the web server asks for a user name and password (`admin` and a password of your choice), and that password
never appears in a file you could commit or in the playbook's output. Needs lab 2 (port 80 open).

## 1. By hand, on branch m

Make the password hash with `openssl passwd -apr1 'yourpassword'` (there is no `htpasswd` here), put `admin:<hash>` in
`/etc/nginx/.htpasswd`, make `/var/www/html/admin/index.html`, and in the `default.conf` server block add a `location /admin`
with `auth_basic "admin";` and `auth_basic_user_file /etc/nginx/.htpasswd;`. Test: `curl -i http://10.10.20.10/admin/` from the pc gives 401; with `-u admin:yourpassword` it gives 200.

Notice where the password now lives: your shell history.

## 2. With a playbook, on branch a

Create the encrypted file and a vault password file, then fill in `labs/5-vault/site.yml`:

```sh
cd ~/netlab
echo 'choose-a-vault-password' > .vault_pass && chmod 600 .vault_pass
ansible-vault create labs/5-vault/secrets.yml        # content: admin_password: "yourpassword"
ansible-playbook labs/5-vault/site.yml --vault-password-file .vault_pass
```

You will use `vars_files:`, `ansible-vault view|edit|rekey`, `no_log: true` on every task that touches the password,
and a **fixed salt** so the hash is the same on every run (otherwise the file changes each time).

## 3. Prove it

```sh
ansible-playbook labs/5-vault/site.yml --vault-password-file .vault_pass      # second run: changed=0
head -1 labs/5-vault/secrets.yml                                              # $ANSIBLE_VAULT;1.1;AES256
ansible 'pc:&auto' -m ansible.builtin.command -a "curl -s -o /dev/null -w %{http_code} http://10.10.20.10/admin/"   # 401
```

## The twist

Run the playbook with `-vvv` and look for the password: `no_log` hides it. Now remove `no_log` from one task, rerun
with `-v`, and see it printed in the clear. Then `ansible-vault rekey` the file.

Next lab: `labs/6-lockdown/README.md`.
