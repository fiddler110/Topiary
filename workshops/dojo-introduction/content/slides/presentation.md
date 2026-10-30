---
marp: true
theme: default
paginate: true
size: 16:9
html: true
style: |
    @import url('assets/themes/presentation.css');
    .split { align-items: center; display: flex; gap: 48px; }
    .split > div { flex: 1; min-width: 0; }
    .split-40 > div:first-child { flex: 0 0 40%; }
    .split-60 > div:first-child { flex: 0 0 58%; }
    .mermaid { text-align: center; margin: 8px 0; }
    .mermaid:not([data-processed]) { visibility: hidden; }
    .mermaid svg { max-height: 420px; }
    .mermaid foreignObject p, .mermaid foreignObject div { margin: 0 !important; line-height: 1.35 !important; }
    .small { font-size: 0.85em; }
    .lede { color: var(--muted); font-size: 0.9em; }
footer: "[&larr; Hub](index.md) &nbsp;|&nbsp; Dojo Introduction | Engineering & IT Operations"
---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: "[&larr; Hub](index.md)" -->

# Topiary

## A hands-on lab platform, from one URL

How it works, and what it can do

**Talk ~20 min · Click-through ~15 min · about 35 min total**

<!--
This is a look-at-this-cool-thing talk, not a lab. Aim for 20 minutes, then let people click around for about 15.
The last slide is a route through the student view and the facilitator view. Those numbers are my estimate (they
match WORKSHOP_DURATION); nobody has timed them in a live room.
-->

---

## One URL, nothing to install

Hands-on training loses its first half hour to setup: versions, blocked installs, shared accounts, and a facilitator who can't see who is stuck.

<div class="split">
<div>

**A student** opens one address, types a name, and gets their own:

- **VS Code** and a **terminal**, in the browser
- a **Forgejo** git server account
- the **slides** and lab guides
- the workshop's extras: DNS, a cloud, a vault

</div>
<div>

**The facilitator** gets `/admin`, with everything a student can reach, plus:

- **Roster**: a tile per student, a read-only view of their terminal, **Release**
- the workshop's own tabs: Runners, DNS Admin, Vault, Audit
- a **status strip**: green when each service answers

</div>
</div>

<!--
Start with the problem, not the product: everyone in the room has lost time to setup. Show the student side, then the
facilitator side, and point out that the facilitator can reach everything a student can. The tabs depend on the workshop
that's running. In this tour you'll see Runners and DNS Admin, but not Vault or Audit. About 2 minutes.
-->

---

## The whole picture

<div class="mermaid">
flowchart LR
  b["Browser"] --> gw["gateway (Caddy)<br/>the only door"]
  subgraph net["Internal networks: nothing here is reachable from outside"]
    al["allocator<br/>who is this?"]
    wt["web-terminal<br/>VS Code + terminal<br/>per account"]
    fg["Forgejo<br/>git + Actions"]
    pr["presentation<br/>Marp slides"]
    ex["workshop services<br/>vault, DNS, cloud, ..."]
  end
  gw --> al
  gw --> wt
  gw --> fg
  gw --> pr
  gw --> ex
  wt --> fg
  al -.-> wt
</div>

<p class="small">Everything is a container. The first person to type a name gets <b>studentNN</b>: a real Linux user, and a matching Forgejo account.</p>

<!--
Read the diagram left to right: one door (the gateway), everything else behind it. Don't explain every box. Ask the
room which one they'd expect to break first (usually the answer is "the terminal") and move on. The detail is on the next
slide. About 2 minutes.
-->

---

## Every request is checked

<div class="split">
<div>

<div class="mermaid">
sequenceDiagram
  actor S as Browser
  participant G as gateway
  participant A as allocator
  participant W as web-terminal
  S->>G: /ide/ (login + cookie)
  G->>A: who is this?
  A-->>G: student07, port 9007
  G->>W: that student's VS Code
</div>

</div>
<div>

- The gateway asks the allocator on **every** request
- Caddy sets the identity headers itself: a client **can't send its own**
- Students share a network, so **nothing trusts a source address**
- Student-typed text is shown to the class as **text only**


<!--
This is the slide for the security-minded people in the room. The point is that identity comes from the gateway, never
from the client. Students share one network, so an IP address tells you nothing about who someone is. If nobody asks
about security, spend 30 seconds here and keep going.
-->
</div>
</div>

---

## Three layers: a new workshop is mostly content

<div class="split">
<div>

**engine/** the shared runtime; knows nothing about any workshop

**modules/** reusable pieces: vault, CI runners, cloud, DNS, CTF range

**workshops/** slides, labs, a seed repo, and the modules it wants

</div>
<div>

Each declares its front door in an `extensions.json`:

| Gate | Who gets through |
| ---- | ---------------- |
| `shared` | anyone with the class login |
| `identity` | a student with a slot, or the facilitator |
| `facilitator` | the facilitator only |

</div>
</div>

<p class="small">Cards, <code>/admin</code> tabs, routes and status lights all come from fixed templates: a manifest can't inject raw config.</p>

<!--
This is the answer to "how hard is it to add a workshop?". Mostly content: slides, labs and a seed repo. The engine
doesn't change. The three gates are the only choices a workshop gets for who can reach a page. If the audience is
non-technical, skip the gate table.
-->

---

## One terminal with every tool

<div class="mermaid">
flowchart LR
  base["base image<br/>VS Code, ttyd, git"] --> m1["+ module tools<br/>the cloud broker, the DNS key"]
  m1 --> w["+ workshop tools<br/>dnscontrol, tofu"]
  w --> run["the image the class runs"]
</div>

- Terminals have **no internet** and no `docker.sock`: every tool is baked in, version-pinned and checksum-verified
- Each student is a separate Linux user with a private home
- Every external image is pinned by digest

<!--
Why the terminals have no internet: it's a classroom with a lot of people on one connection, and a blocked install is
the fastest way to lose a lab. So everything is baked in and pinned. The chain on the slide is how a workshop adds its
own tools without touching the base image.
-->

---

## What is in the box: the workshops

| Workshop | Teaches | Time | Modules |
| -------- | ------- | ---- | ------- |
| **Git Fundamentals** | clone, branch, commit, PR, undo, merge | ~100 min | `sensei` |
| **DNS as Code** | DNS in git with dnscontrol, review, CI preview | ~2 h | `runner-pool`, `dns-ui`, `dns-gate` |
| **Certificate Autorenewal** | ACME: step-ca, certbot, acme.sh | ~1¾ h | `dns-ui`, `dns-gate` |
| **OpenTofu Basics** | init / plan / apply / destroy | ~2¼ h | `dojo-cloud` |
| **Vault Fundamentals** | secrets out of code, git and pipelines | ~4½ h | `openbao`, `runner-pool` |
| **Cloud-Policy-as-Code** | policy definitions, Rego checks, CI | ~5½ h | `dojo-cloud`, `runner-pool` |
| **Ansible on a Small Network** | one small network, by hand and by playbook | ~4½ h | `netlab`, `openbao` |

<p class="small">Each has slides, labs and a cheat sheet on the <a href="workshops.md">Workshop library</a>. Not running in this tour: the vault, the certificate lab, policy-as-code and the network pods (each needs its own workshop).</p>

<!--
Quick tour of what exists. The times are the session lengths each workshop reports in ./dojo list. Be upfront that this
stack only runs the DNS, CI and cloud pieces, so the vault, the certificate lab, the policy workshop and the Ansible
network pods can't be shown from here. The two long ones (policy and Ansible) are better as a half day or two sessions.
The CTF series is on the next slide. About 2 minutes.
-->

---

## What is in the box: the CTF series

| Session | You | Time |
| ------- | --- | ---- |
| **CTF-1: Access and Identity** | get in where auth or access checks are weak | ~150 min |
| **CTF-2: Server-side Trust and APIs** | find where the server trusts input or the caller too much | ~150 min |
| **CTF-3: Secrets and Misconfiguration** | follow leaked credentials as far as they reach | ~115 min |
| **CTF-4: Trusting the Wrong Thing** | break a component, a rule and a pipeline someone trusted | ~155 min |
| **CTF-5: Defend** | patch a live incident with a PR, a CI gate and a redeploy | ~2 h |

<p class="small">All five run on the <code>ctf-range</code> module's targets. CTF-1 to CTF-4 attack, CTF-5 defends. Slides and labs are on the <a href="workshops.md#2">Workshop library</a>.</p>

<!--
A separate series of capture-the-flag sessions. Each is its own workshop, so you pick one per class. CTF-1 is the
warm-up; CTF-5 is the only one where students patch instead of attack. They share the range module, so the targets look
familiar from one session to the next. The times come from each pack's workshop.env, and CTF-1's includes about 20
minutes of Linux and nmap primer. About 1 minute; skip it for an audience that isn't interested in security.
-->

---

## Modules: the pieces workshops share

<div class="split">
<div>

| Module | What it adds |
| ------ | ------------ |
| `runner-pool` | single-use CI runners |
| `dojo-cloud` | the training cloud |
| `dns-ui`, `dns-gate` | DNS Zones view, per-student DNS keys |
| `openbao` | a class vault |
| `netlab` | per-student Ansible pods |

</div>
<div>

| Module | What it adds |
| ------ | ------------ |
| `ctf-range` | targets, flags, attacker tools |
| `sensei` | reviews the Lab 1 roster PR |
| `lab-prep` | `dojo prep N` to catch up |
| `feedback` | an end-of-class survey |
| `achievements` | leaderboard and certificate (optional) |

</div>
</div>

<!--
This is the list from ./dojo modules. A workshop picks the ones it needs with MODULES= in its workshop.env, which is why
two workshops can share the same runners or the same cloud. Not every module is on by default: achievements isn't
used by any workshop right now. About 1 minute.
-->

---

## What you can click through

| Capability | How it works | Where to look |
| ---------- | ------------ | ------------- |
| **CI** | a single-use runner per job, in its own user, on a network with no route to the control plane | Forgejo **Actions**, facilitator **Runners** |
| **DNS as code** | records declared in git, pushed to PowerDNS through a gate that owns each student's zone | **DNS Zones**, **DNS Admin** |
| **Dojo Cloud** | an Azure-*inspired* cloud: ARM-style API, real containers, policy | **Dojo Cloud** card, `tofu` in the terminal |

<!--
These are the three things worth clicking while the room watches. Pick whichever matches the audience: CI for
developers, DNS for ops, Dojo Cloud for anyone curious about OpenTofu. Dojo Cloud is Azure-inspired and isn't Azure.
About 3 minutes.
-->

---

## Running it, and your route through it

```sh
./dojo setup                  # first time: accounts and secrets
./dojo dojo-introduction      # this tour
./dojo dns-as-code --test 20  # a workshop with 20 demo students
./dojo stop                   # removes every container and volume
```

<div class="split">
<div>

**As a student:** type a name, open `~/lab/tools-tour.md` in **VS Code**, then **Forgejo**, **DNS Zones**, **Dojo Cloud**

</div>
<div>

**As the facilitator:** sign in at `/admin`, watch the **Roster**, then **Runners**, **DNS Admin** and the status strip

</div>
</div>

<!--
Hand it over here. Split the room if you can: half follow the student route, half the facilitator route. The commands
at the top are how you'd run this yourself. `./dojo stop` removes every volume, so say that before anyone runs it on a
machine that holds a real class.
-->

---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: "[&larr; Hub](index.md)" -->

# Let's go

## Next: [workshops.md](workshops.md) for the full library, then your terminal

Open [lab-index.md](lab-index.md) for the tool tour. Click anything. Ask for help any time. Nothing here is a test.

<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs"
  mermaid.initialize({
    startOnLoad: false,
    theme: "dark",
    fontFamily: "Manrope, sans-serif",
    flowchart: { htmlLabels: true, curve: "basis" },
    sequence: { mirrorActors: false, actorFontSize: 18, messageFontSize: 18, noteFontSize: 18, boxMargin: 8 },
    themeVariables: {
      fontSize: "18px",
      background: "#18242e",
      primaryColor: "#21313c",
      primaryTextColor: "#e8f0f2",
      primaryBorderColor: "#3dd6c3",
      secondaryColor: "#18242e",
      tertiaryColor: "#18242e",
      lineColor: "#a9bac2",
      edgeLabelBackground: "#18242e",
      clusterBkg: "#18242e",
      actorBkg: "#21313c",
      actorBorder: "#3dd6c3",
      actorTextColor: "#e8f0f2",
      signalColor: "#a9bac2",
      signalTextColor: "#e8f0f2",
      noteBkgColor: "#137f7a",
      noteTextColor: "#e8f0f2",
      noteBorderColor: "#3dd6c3",
    },
  })
  // Mermaid sizes each box from the text it measures, so it must measure
  // unscaled, in the real font. mermaid.run() measures inside the slide,
  // which Marp scales to the window: a window smaller than 1280x720 got boxes
  // too small and labels cut off. mermaid.render() draws in a scratch element
  // on <body> instead; the finished SVG then goes into the slide.
  async function draw() {
    const decode = document.createElement("textarea")
    let n = 0
    for (const el of document.querySelectorAll(".mermaid:not([data-processed])")) {
      decode.innerHTML = el.innerHTML
      const src = decode.value.replace(/<br\s*\/?>/gi, "<br/>").trim()
      const { svg, bindFunctions } = await mermaid.render(`mermaid-${n++}`, src)
      el.innerHTML = svg
      bindFunctions?.(el)
      el.setAttribute("data-processed", "true")
    }
  }
  document.fonts.load('18px Manrope').catch(() => {}).then(() => document.fonts.ready).then(draw)
</script>
