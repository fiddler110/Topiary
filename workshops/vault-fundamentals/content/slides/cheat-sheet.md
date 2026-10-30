---
marp: true
theme: default
paginate: true
size: 16:9
html: true
style: |
    @import url('assets/themes/cheat-sheet.css');
footer: "[&larr; Hub](index.md) &nbsp;|&nbsp; Vault Fundamentals | Cheat Sheet"
---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: "[&larr; Hub](index.md)" -->

# Cheat Sheet

## The commands from Labs 0-13, in one place

Keep this open in a split pane or another tab while you work. You don't need to memorize any of it.

<p class="nav">Every command, plain text: <code>~/lab/cheat-sheet.md</code> in your terminal.</p>

---

## The one idea

```text
request = token (who) + path (what) + operation → policy check → engine does the work → audit log
```

| Piece     | Where you see it                                         |
| --------- | -------------------------------------------------------- |
| Token     | <span class="command">bao token lookup</span>            |
| Path      | `secret/students/$USER/db`, `team/app`, `transit/keys/sops` |
| Policy    | <span class="command">bao policy read app-read</span>    |
| Audit     | <span class="command">bao-audit --accessor ACC</span>    |

`bao` is OpenBao's CLI. Every command is the same as `vault`'s.

---

## Who am I?

| Command                                              | What it does                               |
| ---------------------------------------------------- | ------------------------------------------ |
| <span class="command">bao status</span>              | Is the vault up and unsealed?              |
| <span class="command">bao token lookup</span>        | Your token: entity, policies, TTL          |
| <span class="command">export BAO_NAMESPACE=students/$USER</span> | Work in your own namespace (`unset` to leave) |
| <span class="command">gitleaks git -v</span>         | Scan the whole git history for secrets     |

A secret that reached a remote is leaked: **rotate it**. Deleting it from the file, or from history, isn't enough.

---

## `pass`: secrets on your own machine

| Command                                         | What it does                                  |
| ----------------------------------------------- | --------------------------------------------- |
| <span class="command">pass init KEYID</span>    | A store in `~/.password-store`, for that key  |
| <span class="command">pass git init</span>      | Keep its history in git                       |
| <span class="command">pass insert -m dojo/db</span> | Type lines, then Ctrl+D                   |
| <span class="command">pass generate dojo/api-token 32</span> | A random one                     |
| <span class="command">pass show dojo/db</span>  | Decrypt and print                             |
| <span class="command">pass init -p dojo a@x b@x</span> | Re-encrypt one folder for several people |

Windows: **gopass** reads and writes the same store.

---

## KV v2: write and read

```bash
printf '%s' 'pw' | bao kv put secret/students/$USER/db user=app password=-   # a new version, replaces all keys
printf '%s' 'pw2' | bao kv patch secret/students/$USER/db password=-         # a new version, changes only these keys
bao kv get -field=password secret/students/$USER/db     # one value, for scripts
bao kv get -version=1 secret/students/$USER/db          # an old version
bao kv list secret/students/$USER/
```

`key=-` reads the value from stdin. A value on the command line is visible to everyone in `ps`.

---

## KV v2: versions, delete, destroy

| Command                                                               | What it does                             |
| --------------------------------------------------------------------- | ---------------------------------------- |
| <span class="command">bao kv metadata get PATH</span>                 | Every version, when, deleted or not      |
| <span class="command">bao kv rollback -version=2 PATH</span>          | Old data as a **new** version            |
| <span class="command">bao kv delete PATH</span>                       | Hide the newest version (soft delete)    |
| <span class="command">bao kv undelete -versions=3 PATH</span>         | Bring it back                            |
| <span class="command">bao kv destroy -versions=1 PATH</span>          | Wipe a version for good                  |
| <span class="command">bao kv metadata delete PATH</span>              | Wipe the secret and its history          |

KV v2 paths inside a policy: `<mount>/data/...` for values, `metadata/`, `delete/`, `undelete/`, `destroy/` for the history.

---

## Policies and tokens

```bash
bao secrets enable -path=team kv-v2
bao policy list
bao policy write app-read app-read.hcl
bao token create -orphan -policy=app-read -ttl=15m -field=token
BAO_TOKEN=TOKEN bao kv get team/app     # one command, as another token
bao token revoke TOKEN
```

```hcl
path "team/data/app" {
  capabilities = ["read"]   # create, read, update, patch, delete, list, sudo, deny
}
```

Nothing matches? **Denied.**

---

## AppRole and the Agent

```bash
bao auth enable approle
bao write auth/approle/role/app token_policies=app-read token_ttl=2m token_max_ttl=10m
bao read -field=role_id auth/approle/role/app/role-id          # like a user name
bao write -f -field=secret_id auth/approle/role/app/secret-id  # like a password: secret zero
bao agent -config=agent.hcl > agent.log 2>&1 &                 # logs in, renews, renders templates
```

| Piece     | Secret? | Lives                                   |
| --------- | ------- | --------------------------------------- |
| Role ID   | no      | in the app's config                     |
| Secret ID | **yes** | seconds, then deleted                   |
| Token     | yes     | the Agent's memory, renewed while it runs |

Log that you loaded a secret, never its value.

---

## sops and transit

```bash
bao secrets enable transit
bao write -f transit/keys/sops                  # a key that never leaves the vault
sops encrypt -i app.enc.yaml                    # uses .sops.yaml's hc_vault_transit_uri
sops decrypt app.enc.yaml
sops decrypt --extract '["database"]["password"]' app.enc.yaml
sops edit app.enc.yaml                          # plaintext only in the editor
bao write -f transit/keys/sops/rotate           # new key version; old ones still decrypt
sops rotate -i app.enc.yaml                     # re-encrypt with the newest version
bao write transit/keys/sops/config min_decryption_version=2   # retire old versions
```

Rotate the key, run `sops rotate` on each file, then retire the old version.

---

## CI and the vault

```bash
bao read auth/jwt-ci/config               # whose keys and issuer the vault trusts
bao write auth/jwt-ci/login role=ci-main jwt=@$HOME/id   # what the job does (in the workflow)
```

| In the workflow                               | Why                                                |
| --------------------------------------------- | -------------------------------------------------- |
| `enable-openid-connect: true`                 | Forgejo offers the job an ID token                 |
| `$ACTIONS_ID_TOKEN_REQUEST_URL&audience=openbao` | The token is made **for** the vault              |
| `bao kv get -field=deploy_token team/ci \| sha256sum` | A fingerprint, never the value             |

`${{ secrets.NAME }}` is masked as `***` in logs, but anyone who can push a workflow can print it (`| base64`).

---

## Deployments

| Command                                                             | What it does                                       |
| ------------------------------------------------------------------- | -------------------------------------------------- |
| <span class="command">bao write -f -wrap-ttl=60s -field=wrapping_token auth/approle/role/app/secret-id</span> | A wrapped secret ID |
| <span class="command">bao write sys/wrapping/lookup token=-</span>  | Where a wrapper was made, how long it lives        |
| <span class="command">BAO_TOKEN="$WRAPPED" bao unwrap</span>        | Open it, **once**                                  |
| <span class="command">curl -s http://app-host:8080/.well-known/jwks.json</span> | The platform's public keys             |
| <span class="command">curl -s http://app-host:8080/$USER/</span>    | Your app (also the **My App** card)                |

Lab 10 delivers a secret ID at every deploy. Lab 11 skips the delivery: the platform's identity logs the app in.

---

## Dynamic logins, and when a token leaks

```bash
bao read database/creds/app                  # a Postgres login made now (lab 12)
bao lease lookup LEASE_ID                    # also: renew, revoke
bao token lookup -format=json TOKEN | jq -r .data.accessor
bao-audit --accessor ACC                     # what that token did (lab 13)
bao token revoke -accessor ACC               # it, and every token it made
```

1. **Find** the accessor 2. **Investigate** 3. **Contain** (revoke the tree) 4. **Rotate** what it read 5. **Recover** 6. **Review**

Pass the **accessor** around during an incident, never the token.

---

## The rules

| #   | Rule                         | In one line                                     |
| --- | ---------------------------- | ----------------------------------------------- |
| 1   | Least privilege              | Read only what you need; deny by default        |
| 2   | Identity over secrets        | Prove who you are instead of holding a password |
| 3   | Short-lived, revocable       | A leaked credential should expire by itself     |
| 4   | Secret zero                  | Know where the first credential comes from      |
| 5   | Separation of duties         | Whoever deploys the app needn't read its secrets |
| 6   | Audit everything             | "Who read this, and when?" has an answer        |
| 7   | Plan for leaks               | Rotation and revocation are routine             |
| 8   | Never in git, logs or images | Including history and build output              |

---

## When something goes wrong

| You see                                  | Do this                                                              |
| ---------------------------------------- | -------------------------------------------------------------------- |
| `permission denied`                      | The policy doesn't allow that path. `bao token lookup` lists the token's policies |
| `secret/` is missing from the engine list | `secret/` is the shared vault, in the root namespace. `unset BAO_NAMESPACE` to get back to it |
| `wrapping token is not valid or does not exist` | The wrapper was already opened, or has expired. Make a new one |
| Agent says `no known secret ID`          | The secret ID was single-use and is spent. Deploy again (lab 10)     |
