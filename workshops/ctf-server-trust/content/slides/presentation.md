---
marp: true
theme: default
paginate: true
size: 16:9
html: true
style: |
  @import url('assets/themes/presentation.css');
footer: '[&larr; Hub](index.md) &nbsp;|&nbsp; CTF-2: Server-side Trust and APIs'
---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: "[&larr; Hub](index.md)" -->

# CTF-2: Server-side Trust and APIs

## Capture-the-flag: when the server trusts input or the caller a little too much

**Talk + hands-on lab**

<!--
Speaker notes: This deck is the briefing, not the walkthrough. It sets the scenario, the rules and the tools, and nothing more. The labs guide people toward the technique, and a separate exploit guide is there for anyone who's still stuck after a real try. Don't improvise hints from the stage. If someone's stuck, point them at the lab's own hints first.
-->

---

## Today

1. The engagement: who you are, what you're looking at
2. Rules of engagement (read this slide even if you skip everything else)
3. Your attack box and how the range works
4. Scanning before guessing
5. Flags, scoring, and what to do when you're stuck
6. Hands-on lab

<!--
Speaker notes: Read the six items out loud and move on. This is a briefing, so keep it short and get people into the terminal. If you're short on time, protect the rules slide and the "if you get stuck" slide.
-->

---

## The engagement

**Glasswing Systems** has brought you in to assess four small, independent
systems before they go further into production. Each one trusts *something*
it shouldn't, without quite knowing it: a diagnostics page trusts the text
you type, a preview feature trusts the address it's told to fetch, an
accounts API trusts the fields in your own request, and an internal API
trusts that "logged in" means "allowed."

You are not told which one is broken, or how. That's the job.

Each of you gets your **own private copy** of all four systems. Nothing you
do touches anyone else's, and nothing anyone else does touches yours.

<!--
Speaker notes: Set the scene like a consultant would: they've been hired, they have a scope, and nobody's told them what's wrong. Say that last part plainly, because finding it is the job. Every student has a private copy, so nobody can spoil it or break it for a neighbour. Even if someone asks for a nudge, don't describe what's wrong with any of the systems.
-->

---

## Rules of engagement

Same rules as any real engagement, scaled down to this room:

- **Scope is your own slot, full stop.** The firewall only lets your attack
  box reach your own target; scanning for anyone else's is pointless and
  against the rules even where it isn't blocked.
- **The box in front of you is the whole scope.** Don't look for a way out of
  it: there isn't one, and that's intentional (the range has no route to
  the internet or anything else in this lab).
- **In the real world, you'd need written authorization.** Use what you learn today only against systems you own or have explicit permission to test.

<!--
Speaker notes: Take your time here. It's the one slide I'd call mandatory. Say the legal point in your own words: these same techniques against a system you don't own, or aren't authorized to test, are a crime, and "it was a training exercise" isn't a defence. Also say the range is sealed on purpose, so nobody wastes time hunting for a way out.
-->

---

## Your attack box

Your terminal already has the tools this session needs: `nmap`, `curl`,
`jq`, `httpie`, `ncat`, `openssl`, and more. The **Lab Info** card explains how each one works (mechanics, not answers). Have a look before you start.

<p class="nav">No git and no repo to clone this time. Everything happens against your target, over the network.</p>

<!--
Speaker notes: Don't read the tool list. Point at the Lab Info card and tell people to open it now. It explains how each tool works without giving answers, and most people who stall early haven't looked at it. If anyone asks where the repo is, there isn't one this time.
-->

---

## The Attack Range card

One target is **live** in your slot at a time, picked from the card on the
landing page:

- **Start** boots the target you picked; **Stop** tears it down; **Reset**
  returns it to its untouched state (your progress on *solved* flags is kept
  either way).
- The card shows your slot's **IP only**, never the ports. Finding those is
  your first step, every time.
- Starting a different target stops the current one. Only one is ever live,
  so plan your time.

<!--
Speaker notes: If you can, show the card on screen. People trip on three things: only one target runs at a time, the card shows an IP and never ports, and Reset keeps solved flags. Say it once, clearly, and tell them to plan their order. I haven't timed how long a target takes to boot, so don't promise a number.
-->

---

## Scan before you guess

Every target publishes more than one port. Some are real and some are decoys, like on a real box. **Don't skip this step.** It's not filler. It's the first real skill this session teaches.

```sh
nmap -sV -p- <your-slot-ip>
```

Read what comes back before you touch anything else.

<!--
Speaker notes: Run the scan live if you have a minute. The point is the habit: see what's listening before you poke at anything. Warn them that some ports are decoys and a full scan takes a while, so they should start it and read the lab while it runs. Don't say which ports matter.
-->

---

## Flags and scoring

Each solved target hands you a flag, `flag{...}`, unique to you. Nobody else's flag works for you, and yours won't work for them.

```sh
dojo flag '<flag>'
```

Solving earns points on the room's leaderboard (the same achievements you may know from other sessions). A wrong flag just tells you to keep looking. It doesn't cost you anything.

<!--
Speaker notes: Show the submit command and say a wrong flag costs nothing, so there's no reason to hold back. Flags are per student, so sharing one is pointless. If the room is competitive, mention the leaderboard. If it isn't, don't push it.
-->

---

## Four systems, today

| System | What it is |
|---|---|
| **Network diagnostics page** | Looks up a host you type, server-side |
| **URL preview feature** | Fetches a URL you give it, server-side |
| **Accounts API** | A JSON API for reading and updating your own profile |
| **Internal ops API** | Administrative routes, gated by nothing but "logged in" |

No further hints here. What's wrong with each one is for you to find.

<!--
Speaker notes: Read the table, then stop. There's nothing more to say from the stage, and that's on purpose. Suggest an order only if someone asks, and say any order works. If the room splits on where to start, that's fine. It spreads the questions out.
-->

---

## If you get stuck

1. **Re-read the lab.** Each lab has two rounds of hints before it gets anywhere near an answer.
2. **Check Lab Info** for the tool you're trying to use.
3. **Ask.** A facilitator would rather talk you through *where to look* than
   watch you stall.
4. Only after a real try: each lab's last line points at an **exploit guide** with the full walkthrough. Using it isn't failing, but using it *first* skips the part that teaches you something.

<!--
Speaker notes: This slide keeps you from turning into a hint machine. Walk the order: lab hints, Lab Info, then you. When someone asks, point at where to look, not what to find. Be straight about the exploit guide: it's there and using it is fine, but using it first skips the learning. Check in with anyone who's gone quiet around the halfway mark.
-->

---

<!-- _class: lead -->
<!-- _paginate: false -->

# Your turn

## Open the Labs tab, or `~/lab/README.md` in the terminal

<p class="nav">Next: <a href="lab-index.md">Labs &rarr;</a></p>
