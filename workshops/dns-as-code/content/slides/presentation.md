---
marp: true
theme: default
paginate: true
size: 16:9
html: true
style: |
  @import url('assets/themes/presentation.css');
footer: '[&larr; Hub](index.md) &nbsp;|&nbsp; DNS as Code | Engineering & IT Operations'
---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: "[&larr; Hub](index.md)" -->

# DNS as Code

## Managing DNS records the way we manage everything else

Builds on Git Fundamentals: the same workflow, applied to a new kind of file

**Talk ~20 min · Labs ~102 min (Part 1 ~30, Part 2 ~72) · about 2 h**

<!--
Assumes the room already did Git Fundamentals, or at least knows
clone/branch/commit/push/PR. This is the same muscle memory applied to a
system most people currently change by clicking around a web console.

Timing: talk about 20 min (an estimate, not measured). Labs 1-2 are Part 1,
your own zone, about 30 min (20 + 10). Labs 3-6 are Part 2, the shared
zone, about 72 min (30 + 20 + 10 + 12). Add about 5 min for a recap. Every
lab is mandatory, in order. If you're short on time, shorten the talk, not
the labs.
-->

---

## Today

1. Why DNS changes need the same care as code, and why the file always wins
2. What dnscontrol does
3. Reading `dnsconfig.js`
4. The change workflow, Track A: raw git
5. The change workflow, Track B: the `dnsctl.py` wrapper
6. Hands-on practice

> Same loop as last session. Different file, same discipline.

<!--
One minute. The point to land is that nothing here is new except the file
type. If the room skipped Git Fundamentals, say so now and slow down in
Part 4.
-->

---

<!-- _class: section-title -->

# Part 1

## Why DNS-as-Code

---

## The core idea

> Whatever's committed in `dnsconfig.js` **is** the DNS configuration: not a
> description of it, the actual, enforced state.

- `dnscontrol push` makes live DNS match the file **exactly**: additions,
  edits, and **removals**. Anything live but undeclared gets deleted
- Nothing reconciles the other way. Click a record into existence in the
  dashboard and the next `push` deletes it. Nothing "remembers" a manual
  edit the file never mentioned
- Not DNS-specific. Terraform, Kubernetes or any GitOps tool gives you the
  same guarantee for its own kind of file

<!--
Spend the time here. Everything that follows (preview/push, PRs, dnsctl.py)
is tooling built on this one guarantee. The dashboard isn't a second way to
make changes anymore. It's not a way to make changes at all.

Ask the room who has clicked a fix into a dashboard "just this once". It
sets up Lab 2, where they cause drift on purpose and watch push undo it.
Questions are welcome here; it's the idea that makes "why review every
diff" and "why did my dashboard click disappear" make sense later. About
3 min.
-->

---

## How DNS usually gets changed

<div class="two-column">

- Someone opens a provider's web dashboard
- Clicks around, changes a record
- No review, no diff, no history of *why*
- "Who changed the MX record last Tuesday?" Nobody knows
- A typo in an A record <label for="dns-outages" class="pop-trigger">takes down a service with zero warning</label>

</div>

> The dashboard *is* the audit log, and it's not a very good one.

<div class="pop">
<input type="checkbox" id="dns-outages" class="pop-toggle">
<div class="pop-overlay">
<label for="dns-outages" class="pop-close">close &#10005;</label>
<h3>One DNS change, everything down</h3>
<p class="pop-sub">Routine changes, big outages: DNS sits in front of everything else.</p>
<div class="leak-grid cols-4">
<div class="leak"><i>2009</i><b>.se (Sweden)</b>A script left the trailing dot off every record.<em>The whole .se domain offline for about 1.5 hours</em></div>
<div class="leak"><i>2019</i><b>Microsoft Azure</b>A nameserver delegation change during a DNS migration.<em>Microsoft 365, Dynamics and DevOps down worldwide, ~2 hours</em></div>
<div class="leak"><i>2021</i><b>Salesforce</b>A DNS change pushed everywhere at once, through the emergency process.<em>Global outage of about 5 hours</em></div>
<div class="leak"><i>2021</i><b>Akamai</b>A configuration update hit a bug in Edge DNS.<em>Banks, airlines and more unreachable for an hour</em></div>
<div class="leak"><i>2021</i><b>Slack</b>A DNSSEC change, then a rollback some resolvers didn't see.<em>Some users cut off for 24 hours</em></div>
<div class="leak"><i>2021</i><b>Facebook</b>A maintenance command cut the backbone; its DNS servers went dark.<em>Facebook, Instagram, WhatsApp down 7+ hours</em></div>
<div class="leak"><i>2025</i><b>Cloudflare 1.1.1.1</b>A June config mistake, set off by a July change.<em>The resolver offline worldwide for 62 minutes</em></div>
<div class="leak"><i>2025</i><b>AWS</b>Automation left DynamoDB's DNS record empty.<em>us-east-1 disrupted for about 15 hours</em></div>
</div>
<p class="pop-src">Sources: <a href="https://www.theregister.com/on-prem/2009/10/13/missing-dot-sends-sweden-tumbling-off-internet/744915" target="_blank" rel="noopener">The Register (.se)</a>, <a href="https://www.theregister.com/2019/05/02/microsoft_azure_outage_dns/" target="_blank" rel="noopener">The Register (Azure)</a>, <a href="https://www.theregister.com/2021/05/19/salesforce_root_cause" target="_blank" rel="noopener">The Register (Salesforce)</a>, <a href="https://www.akamai.com/blog/news/akamai-summarizes-service-disruption-resolved" target="_blank" rel="noopener">Akamai</a>, <a href="https://slack.engineering/what-happened-during-slacks-dnssec-rollout/" target="_blank" rel="noopener">Slack</a>, <a href="https://engineering.fb.com/2021/10/05/networking-traffic/outage-details/" target="_blank" rel="noopener">Meta</a>, <a href="https://blog.cloudflare.com/cloudflare-1-1-1-1-incident-on-july-14-2025/" target="_blank" rel="noopener">Cloudflare</a>, <a href="https://www.thousandeyes.com/blog/aws-outage-analysis-october-20-2025" target="_blank" rel="noopener">ThousandEyes (AWS)</a>.</p>
</div>
</div>

<!--
Click "takes down a service with zero warning" to open the wall of real DNS
outages; "close" at the top right hides it. Don't read the table. Pick two
or three that your room will know (Facebook and AWS usually land) and make
one point: DNS sits in front of everything, so a small mistake gets big
fast. If you're short on time, skip the popup and just say that.
-->

---

## What changes with DNS-as-Code

- Records live in a file (`dnsconfig.js`), in a git repo
- Every change is a **pull request**, reviewed before it's live
- `dnscontrol preview` shows the **exact diff** before anything happens
- `git log` becomes a real audit trail: who, when, why (commit message)
- Rolling back a mistake is `git revert`, not "does anyone remember what
  it used to say?"
- A well-intentioned dashboard fix doesn't survive the next `push` either.
  The fix has to go through the file, or it isn't real

<!--
This is the case for infrastructure-as-code in general, applied to DNS.
DNS is infrastructure, and it's usually the least-reviewed part. The
rollback bullet pays off in Lab 5, so a quick mention is enough. About
2 min.
-->

---

<!-- _class: section-title -->

# Part 2

## What dnscontrol does

---

## dnscontrol, in one sentence

> A CLI that reads a config file describing what DNS records **should**
> exist, compares it to what **actually** exists, and shows or applies the
> difference.

```text
dnsconfig.js  --preview-->  "here's what would change"
dnsconfig.js  --push------->  makes it actually change
```

It doesn't matter which DNS provider is behind it (Cloudflare, Route53, or
PowerDNS, which this lab uses). The workflow is identical.

<!--
Keep this short. The provider-neutral point matters: what they learn today
carries to whatever DNS host they use at work. About 1 min.
-->

---

## Two commands you'll use constantly

```sh
dnscontrol preview
```
Dry run. Shows the diff. **Changes nothing.** Always run this first.

```sh
dnscontrol push
```
Applies the diff. Normally this happens via CI after a PR merges, not by
hand. This lab has that CI wired up for real, so once you're past today's
initial bootstrap step you'll mostly watch it happen instead of typing
this yourself.

<!--
Students push by hand only in their own zone (Part 1). In the shared zone
the API refuses it with a 403, and that surprise is deliberate. Mention it
now so it doesn't read as a broken lab later.
-->

---

<!-- _class: section-title -->

# Part 3

## Reading `dnsconfig.js`

---

## The shape of the file

```js
var PDNS = NewDnsProvider("powerdns", { "zone_kind": "Native" });
var REG = NewRegistrar("none");

D("dojo.test", REG,
	DnsProvider(PDNS),
	DefaultTTL(300),

	A("@", "203.0.113.10"),
	CNAME("app", "dojo.test."),
	MX("@", 10, "mail.dojo.test."),
);
```

One `D("<zone>", ...)` block per domain. Records inside are plain
JavaScript function calls, so there's no special syntax beyond "find the
right block, then add, edit or remove a line."

<!--
Walk through it top to bottom: provider, registrar, one zone block, records.
People who don't write JavaScript get stuck on the tab-indented commas and
the closing `);`. Tell them to copy an existing line and edit it. About
2 min.
-->
right block, add/edit/remove a line."

---

## Record types you'll see today

| Type | Purpose | Example |
| ---- | ------- | ------- |
| `A` | name → IPv4 address | `A("www", "203.0.113.10")` |
| `CNAME` | alias → another hostname | `CNAME("app", "dojo.test.")` |
| `MX` | mail routing, with priority | `MX("@", 10, "mail.dojo.test.")` |
| `TXT` | arbitrary text (SPF/DKIM/verification) | `TXT("@", "v=spf1 -all")` |

<p class="small">`"@"` means the bare apex domain. CNAME/MX targets need a
trailing dot. It's the most common mistake, and one <code>preview</code>
usually catches for you.</p>

<!--
Only four types, and you don't need to teach DNS. If someone asks about
other types, say the same pattern works for them. The trailing dot is worth
saying out loud, since Lab 1 has them hit it on purpose.
-->

---

<!-- _class: section-title -->

# Part 4

## The change workflow, Track A: raw git

---

## Track A: git + dnscontrol by hand

<div class="flow">
<span><b>1</b><br>edit<br><small>on a branch</small></span>
<span>→</span>
<span><b>2</b><br>preview<br><small>local diff</small></span>
<span>→</span>
<span><b>3</b><br>PR<br><small>Forgejo</small></span>
<span>→</span>
<span><b>4</b><br>review<br><small>a teammate</small></span>
<span>→</span>
<span><b>5</b><br>merge</span>
<span>→</span>
<span><b>6</b><br>push<br><small>CI applies it</small></span>
</div>

Last session's git workflow plus `dnscontrol preview`. Step 6 happens
without you: the merge triggers CI, which runs `push`. You run `push`
yourself only in your own zone.

<!--
Trace the six boxes with your finger. Steps 1, 3, 4 and 5 are what they
did last session, and step 2 is the only new one. Step 6 is the one people
forget isn't theirs. About 2 min.
-->
yourself only in your own zone.

---

## Why review the diff twice

1. **Locally**, before opening the PR. Catch your own mistakes first, for
   free, before anyone else has to look at them.
2. **On the PR**, before merging. It's a second set of eyes on something
   that can take down email or a whole domain if it's wrong.

> If the diff shows anything you don't expect, stop. Don't merge a diff
> you don't fully understand.

<!--
Say it plainly: reviewing a diff you don't understand is worse than not
reviewing, because it feels like a control. When someone approves in Lab 3,
ask what they checked in the diff. About 1 min.
-->

---

## CI is watching too

This lab has real CI on the sample repo (Forgejo Actions, not GitHub
Actions, but the same idea):

- **`DNS Preview`** runs on every PR, posts the exact `dnscontrol
  preview` diff as a comment, and sets a pass/fail check
- **`DNS Apply`** runs on merge to `main` and runs `dnscontrol push` for
  real

CI previews your branch *merged into* the current `main`, so the comment
shows exactly what merging would do, even after classmates merged first.

<!--
The merged-into-main detail matters when two people touch the same file,
which is exactly what Lab 6 does. If the room asks why the preview
differs from their local one, this is why. About 2 min.
-->

---

## Gates on the shared zone

A process only counts if you can't skip it. On `dojo.test`:

- **Only CI changes the zone.** The DNS API refuses a `dnscontrol push`
  from your terminal (`403`); only the pipeline's runner may write.
- **`main` is protected.** No direct pushes. A PR merges only with a
  passing **DNS Preview** check and **one approval** from someone else.

In a real company: only the pipeline holds the production credential, and
branch protection makes review mandatory, not a habit.

<!--
Someone will try to push from their terminal. Let them, then point at the
403. That's the lesson. You need a classmate to approve, so tell people
to pair up now. Mention that this is a lab simplification: at work, the
pipeline credential is the real control. About 2 min.
-->

---

<!-- _class: section-title -->

# Part 5

## The change workflow, Track B: the `dnsctl.py` wrapper

---

## Same steps, one command each

## Same steps, one command each

```sh
dnsctl.py record add $USER-api.dojo.test --type A --value 203.0.113.30
dnsctl.py preview
dnsctl.py submit "Add $USER-api"
dnsctl.py status
dnsctl.py review <PR#>
dnsctl.py merge <PR#>
```

Every step from Track A still happens underneath (branch, edit, preview,
commit, push, open a PR). `dnsctl.py` just names each one and does the
git/file work for you. The guarantee from Part 1 doesn't change: the file
is still what gets enforced, and this is a faster way to edit it
correctly.

<!--
The wrapper is a convenience, not a different process. Students who found
Track A tedious will like it, but make sure they did Lab 3 first so they
know what's happening underneath. About 2 min.
-->

---

<div class="flow">
<span><b>1</b><br>record add<br><small>edit + write</small></span>
<span>→</span>
<span><b>2</b><br>preview</span>
<span>→</span>
<span><b>3</b><br>submit<br><small>branch+commit+push+PR</small></span>
<span>→</span>
<span><b>4</b><br>status / review</span>
<span>→</span>
<span><b>5</b><br>merge</span>
</div>

Same shape as Track A's diagram, fewer boxes to type. `submit` alone
covers branch, commit, push and opening the PR in one call.

<!--
Quick. Point at box 3: that single command replaces four git steps. About
30 seconds.
-->

---

## One CLI, two forges

`dnsctl.py` doesn't know or care whether this repo lives on GitHub or on
this lab's Forgejo. `submit`/`status`/`review`/`merge`/`validate` all just
call "whatever forge is hosting this repo," resolved automatically from the
`origin` remote's host:

- A GitHub remote → the real GitHub CLI (`gh`), completely unmodified
- Anything else (this lab's `git-server`) → a small, stdlib-only Forgejo
  API client that speaks Forgejo's REST API directly

Same commands, same script, either backend. The wrapper doesn't fork
itself per platform; it just dispatches under the hood.

<!--
The upstream template's docs treat the wrapper as GitHub-only (`gh pr
create/merge/review`). This lab adds the Forgejo side so both tracks can
be taught here. Skip this slide if the room doesn't care how it works;
nothing later depends on it. About 1 min.
-->

---

## What the wrapper does and doesn't check

- `doctor` checks `dnscontrol`, `creds.json`, the PowerDNS API and git
  hooks. `setup` turns the hooks on: git never does that for a clone.
- `merge` checks "DNS Preview" once and only warns if CI hasn't posted
  yet. Forgejo still won't merge without a passing check and an approval.
- `validate` waits for "DNS Apply", then confirms the live zone matches.

> A wrapper shortens the steps. The server still owns the gates.

<!--
The last line is the one to say out loud. The wrapper warning about CI is
advice; the Forgejo gate is enforcement. If anyone tries to merge early
with `dnsctl.py`, they'll see the difference. About 1 min.
-->

---

<!-- _class: section-title -->

# Part 6

## Hands-on practice

---

## What you'll do

**Part 1, your own zone** (`<you>.dojo.test`): nobody else touches it.
**Lab 1:** preview, push, `dig`; add, change and remove
records; catch a mistake. **Lab 2:** drift and undo.

**Part 2, the shared zone** (`dojo.test`): only CI can change it.
**Lab 3:** branch → PR → CI preview → a classmate approves →
merge → CI applies. **Labs 4-6:** `dnsctl.py`, rollback, merge conflicts.

**Full steps are in `~/lab/README.md`** inside your terminal.

<!-- _footer: "[&larr; Hub](index.md)" -->

<!--
Part 1 is about 30 min, Part 2 about 72. Tell people that if they finish
Part 1 early they should wait for Part 2 to start together, because Lab 3
needs a classmate to review. Walk the room; stuck for more than a minute
or two means ask.
-->

---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: "[&larr; Hub](index.md)" -->

# Let's go

## Next: [labs.md](labs.md) for what each lab covers, then your terminal

Keep [cheat-sheet.md](cheat-sheet.md) open in another tab. Ask for help
any time. This is a lab, not a test.
