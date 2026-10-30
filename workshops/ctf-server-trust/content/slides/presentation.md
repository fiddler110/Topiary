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
Speaker notes: this deck is the briefing, not the walkthrough. It sets the
scenario, the rules and the tools. It never names a specific bug or a
payload, and that's deliberate: the labs guide toward the technique, and a
separate exploit guide exists for anyone who's genuinely stuck after trying.
Don't improvise extra hints from the stage. If someone's stuck, point them
at the lab's own hints first.
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
Speaker notes: Read the six items out loud and move on. This is a briefing, so keep it short and get people into the terminal. If you're pressed for time, the rules and "if you get stuck" slides are the two to protect.
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
Speaker notes: Set the scene as a consultant would. They've been hired, they have a scope, and nobody has told them what's wrong. Say that last part plainly: finding it is the job. Mention that every student has a private copy, so nobody can spoil it or break it for a neighbour. Don't describe what's wrong with any of the systems, even when someone asks for a nudge.
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
- **In the real world, this requires written authorization.** Everything you
  learn today is only legal to use against systems you own or are explicitly
  authorized to test.

<!--
Speaker notes: Take your time on this one. It's the only slide in the deck I'd call mandatory. Say the legal point in your own words: the same techniques against a system you don't own or aren't authorized to test are a crime, and "it was a training exercise" is not a defence. Also say that the range is sealed on purpose, so nobody wastes time hunting for a way out.
-->

---

## Your attack box

Your terminal already has the tools this session needs: `nmap`, `curl`,
`jq`, `httpie`, `ncat`, `openssl`, and more. The **Lab Info** card is a
reference for every one of them (mechanics, not answers) and it's worth
a look before you start.

<p class="nav">No git, no Forgejo repo to clone for this session: everything happens
against your target, over the network.</p>

<!--
Speaker notes: Don't read the tool list. Point at the Lab Info card and tell them to open it now, because it explains how each tool works without giving answers. Most people who stall early haven't looked at it. If anyone asks where the repo is, the answer is on the slide.
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
Speaker notes: If you can, show the card on screen while you talk. The things people trip on are that only one target runs at a time, that the card shows an IP and never ports, and that Reset keeps solved flags. Say it once, clearly, and tell them to plan their order. I haven't timed how long a target takes to boot, so don't promise a number.
-->

---

## Scan before you guess

Every target publishes more than one port. Some are real; some are decoys
that exist purely so scanning tells you something, the way a real box
would. **Don't skip this step.** It's not filler, it's the first real skill
this session teaches.

```sh
nmap -sV -p- <your-slot-ip>
```

Read what comes back before you touch anything else.

<!--
Speaker notes: Run the scan live if you have a minute. The point is the habit: look at what's listening before you poke at anything. Warn them that some ports are decoys and that a full port scan takes a little while, so they should start it and read the lab while it runs. Don't say which ports matter.
-->

---

## Flags and scoring

Each solved target hands you a flag, `flag{...}`, unique to you. A classmate's flag will never work for you and vice versa.

```sh
dojo flag '<flag>'
```

Solving earns points on the room's leaderboard (the achievements module you
may already know from other sessions). A wrong flag just tells you to keep
looking. It never costs you anything.

<!--
Speaker notes: Show the flag submit command and say that a wrong flag costs nothing, so there's no reason to hold back. Flags are per student, so sharing one is pointless. If the room is competitive, mention the leaderboard. If it isn't, don't push it.
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
Speaker notes: Read the table, then stop. The hint-free wording is on purpose: there is nothing more to say from the stage. Suggest an order only if someone asks, and say any order works. If the room is split on where to start, that's fine, it spreads out the questions.
-->

---

## If you get stuck

1. **Re-read the lab.** Each one has two rounds of hints built in before it
   tells you anything close to an answer.
2. **Check Lab Info** for the tool you're trying to use.
3. **Ask.** A facilitator would rather talk you through *where to look* than
   watch you stall.
4. Only once you've genuinely tried: each lab's last line points at an
   **exploit guide** with the full walkthrough. Using it isn't a failure, but
   using it *first* skips the part that actually teaches you something.

<!--
Speaker notes: This is the slide that keeps you from becoming a hint machine. Walk the order: lab hints, Lab Info, then ask you. When someone asks, point at where to look instead of what to find. Be straight about the exploit guide: it's there, using it is fine, but using it first skips the learning. Check in with anyone quiet around the halfway mark.
-->

---

<!-- _class: lead -->
<!-- _paginate: false -->

# Your turn

## Open the Labs tab, or `~/lab/README.md` in the terminal

<p class="nav">Next: <a href="lab-index.md">Labs &rarr;</a></p>
