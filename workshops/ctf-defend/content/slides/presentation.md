---
marp: true
theme: default
paginate: true
size: 16:9
html: true
style: |
  @import url('assets/themes/presentation.css');
footer: '[&larr; Hub](index.md) &nbsp;|&nbsp; CTF-5: Defend'
---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: "[&larr; Hub](index.md)" -->

# CTF-5: Defend

## Patch it with git: a live incident on your own app, defended with a PR, a CI gate and a redeploy.

**Talk + hands-on lab**

<!--
Speaker notes: This is the one session in the CTF series that isn't about breaking in. People are on the other side of an attack. The lab is where they find what's wrong, by reading the app's own source, so don't volunteer anything from the stage. If someone's stuck, point them back at app.py and the exploit check, not at the fix.
-->

---

## Today

1. The incident: three apps, one clock
2. The loop: detect, triage, contain, fix, verify
3. Your tools
4. Shipping a fix the normal way
5. Hands-on lab

<!--
Speaker notes: Five items, read them fast. This session is different from the rest of the series, so say so up front: people are defending, not attacking.
-->

---

## The incident

Every other CTF session has you attacking. This one flips it.

Three apps are live on **your own slot**: `customer-portal` (high),
`policy-bypass` (medium), `leaky-config` (low).

Each is attacked on its own timer, in an order that differs per student.
Unfixed breaches pile up. You choose what to work on first.

<!--
Speaker notes: Lead with the flip. Everyone expects to break something, and instead they own the apps. Each app has a severity and its own attack timer, and the order differs per student, so there's no shared answer to swap. Let people pick what to work on first. Unfixed breaches pile up, so dithering costs them. Don't say what's wrong with any app.
-->

---

## The loop

1. **Detect**: find it in the evidence
2. **Triage**: which target, how bad, what first
3. **Contain**: stop the bleeding
4. **Fix**: in source, by pull request
5. **Verify**: prove it, don't believe it

<!--
Speaker notes: Walk the five steps in order, one sentence each. Spend the most time on the last one: "prove it, don't believe it" is the habit I care about most. Contain is about stopping the damage fast, fix is about doing it properly in source. If anyone asks which app is which kind of problem, point them at the SIEM panel and the source.
-->

---

## Your tools

- `git`, an editor, `python3`, `curl`
- the **SIEM** panel: a different signal per target, with noise
- `dojo check`: runs the attack against your live slot

```sh
dojo check                  # all three
dojo check policy-bypass    # one
```

`contained` means blocked **and** still usable.

<!--
Speaker notes: Show the SIEM panel and the check command side by side. Two things to get across: each target gets a different signal with noise mixed in, and "contained" means blocked and still usable, so breaking the app to stop the attack doesn't count. Tell them to run the check often, since it's cheap. I haven't timed a full check run.
-->

---

## Your repos

```sh
cd ~/lab
git clone http://git-server:3000/$USER/customer-portal.git
```

One repo per app, all yours. What lands on `main` is what runs.

Read each `README.md` first: it says what the platform provides.

<!--
Speaker notes: Quick slide. Each app is its own repo and whatever lands on main runs, so a bad merge goes live. Have them read each README before they touch the code. It says what the platform already provides, which saves guessing.
-->

---

## Shipping a fix

```sh
git checkout -b fix-<target>
git push -u origin fix-<target>
```

The PR gate runs the attack against your branch, plus one normal request. It's advisory and never blocks the merge.
Merge, and your slot redeploys.

<!--
Speaker notes: Walk through branch, push, PR, merge. The gate is advisory and never blocks the merge, so say clearly that green isn't proof and red isn't a stop sign. The real proof is the check against the live slot after the redeploy.
-->

---

## If you get stuck

1. Re-read the briefing and each README.
2. Use the app, then read the source.
3. Run `dojo check` often.
4. Ask. Hints are in the lab, in order.

<!--
Speaker notes: Hints are in the lab, in order, so send people there first. When you help, point at the source or the SIEM signal rather than at the fix. The usual stuck case is someone who merges and redeploys without running the check, so ask about that first.
-->

---

<!-- _class: lead -->
<!-- _paginate: false -->

# Your turn

## Open the Labs tab, or `~/lab/README.md` in the terminal

<p class="nav">Next: <a href="lab-index.md">Labs &rarr;</a></p>
