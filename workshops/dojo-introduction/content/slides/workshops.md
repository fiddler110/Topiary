---
marp: true
theme: default
paginate: false
size: 16:9
html: true
style: |
  @import url('assets/themes/labs.css');
  .shelf { display: grid; gap: 14px; grid-template-columns: 1fr 1fr 1fr; margin-top: 10px; }
  .shelf > div { background: var(--surface) !important; border: 1px solid var(--line) !important; border-left: 6px solid var(--blue) !important; border-radius: 6px; padding: 6px 14px; }
  .shelf h3 { font-size: 23px !important; margin: 0 0 2px !important; }
  .shelf p { color: var(--muted) !important; font-size: 15px !important; line-height: 1.3 !important; margin: 0 !important; }
  .shelf .with { font-size: 13px !important; margin-top: 4px !important; }
footer: '[&larr; Hub](index.md)'
---

<!-- _class: lead lab-index -->

# Workshop library

<p class="nav">Eight workshops and a CTF series, each with its own slides, labs and cheat sheet. Pick one to open its hub.</p>

<div class="shelf">
<div>
<h3><a href="w/git-fundamentals/index.md">Git Fundamentals &rarr;</a></h3>
<p>Clone, branch, commit, push and open a pull request. The base for everything else.</p>
<p class="with">~100 min · Forgejo</p>
</div>
<div>
<h3><a href="w/dns-as-code/index.md">DNS as Code &rarr;</a></h3>
<p>Manage DNS records from git with dnscontrol, behind review and a CI preview.</p>
<p class="with">~2 h · PowerDNS · dnscontrol · Actions</p>
</div>
<div>
<h3><a href="w/cert-autorenewal/index.md">Certificate Autorenewal &rarr;</a></h3>
<p>Issue and renew real TLS certificates with ACME: step-ca, certbot and acme.sh.</p>
<p class="with">~1¾ h · step-ca · certbot · acme.sh</p>
</div>
<div>
<h3><a href="w/tofu-basics/index.md">OpenTofu Basics &rarr;</a></h3>
<p><code>init</code>, <code>plan</code>, <code>apply</code>, <code>destroy</code> and repo layout, on Dojo Cloud.</p>
<p class="with">~2¼ h · OpenTofu · Dojo Cloud</p>
</div>
<div>
<h3><a href="w/vault-fundamentals/index.md">Vault Fundamentals &rarr;</a></h3>
<p>Keep secrets out of code, git and pipelines: OpenBao, identity, CI logins, dynamic credentials.</p>
<p class="with">~4½ h · OpenBao · sops · runners</p>
</div>
<div>
<h3><a href="w/cloud-policy-as-code/index.md">Cloud-Policy-as-Code &rarr;</a></h3>
<p>Write the rules that keep a cloud safe as code: policy definitions, Rego checks and a CI pipeline.</p>
<p class="with">~5½ h · OpenTofu · OPA · Dojo Cloud</p>
</div>
<div>
<h3><a href="w/netlab-ansible/index.md">Ansible on a Small Network &rarr;</a></h3>
<p>Build a firewall, a VLAN switch and a web server twice: by hand, then by playbook.</p>
<p class="with">~4½ h · Ansible · netlab pods</p>
</div>
<div>
<h3><a href="index.md">Dojo Introduction &rarr;</a></h3>
<p>This tour: how the platform is built, with Git, CI, DNS and Dojo Cloud running at once.</p>
<p class="with">~35 min · Forgejo · PowerDNS · Dojo Cloud</p>
</div>
<div>
<h3><a href="workshops.md#2">CTF series &rarr;</a></h3>
<p>Five capture-the-flag sessions: four attack, one defends. Next slide.</p>
<p class="with">~2 to 2½ h each · CTF range</p>
</div>
</div>

---

<!-- _class: lead lab-index -->

# CTF series

<p class="nav">Capture-the-flag sessions on the same range. Each is its own workshop: pick one per class.</p>

<div class="shelf">
<div>
<h3><a href="w/ctf-access/index.md">CTF-1: Access and Identity &rarr;</a></h3>
<p>Warm-up: getting in when auth or access checks are weak.</p>
<p class="with">~150 min · four targets</p>
</div>
<div>
<h3><a href="w/ctf-server-trust/index.md">CTF-2: Server-side Trust and APIs &rarr;</a></h3>
<p>When the server trusts input, or the caller, a little too much.</p>
<p class="with">~150 min · four targets</p>
</div>
<div>
<h3><a href="w/ctf-secrets-config/index.md">CTF-3: Secrets and Misconfiguration &rarr;</a></h3>
<p>Leaked credentials and how far they reach.</p>
<p class="with">~115 min · two targets · OpenBao</p>
</div>
<div>
<h3><a href="w/ctf-trust-chain/index.md">CTF-4: Trusting the Wrong Thing &rarr;</a></h3>
<p>A component, a rule or a pipeline you trusted and shouldn't have.</p>
<p class="with">~155 min · three targets · runners</p>
</div>
<div>
<h3><a href="w/ctf-defend/index.md">CTF-5: Defend &rarr;</a></h3>
<p>A live incident on your own app, patched with a PR, a CI gate and a redeploy.</p>
<p class="with">~2 h · three apps · runners</p>
</div>
<div>
<h3><a href="workshops.md#1">&larr; Core workshops &rarr;</a></h3>
<p>Back to the other workshops.</p>
<p class="with">Git, DNS, certificates, OpenTofu, vault, policy, Ansible</p>
</div>
</div>
