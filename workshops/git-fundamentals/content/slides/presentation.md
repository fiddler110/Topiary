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
  .split-30-70 > div:first-child { flex: 0 0 30%; }
  .split-30-70 > div:last-child { flex: 0 0 70%; }
  .mermaid .commit-label { font-size: 18px !important; }
  .mermaid foreignObject p, .mermaid foreignObject div { margin: 0 !important; line-height: 1.5 !important; }
footer: '[&larr; Hub](index.md) &nbsp;|&nbsp; Git Fundamentals | Engineering & IT Operations'
---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: "[&larr; Hub](index.md)" -->

# Git Fundamentals

## What, why, and how

Version control for Engineering & IT Operations

**Talk ~30 min · Labs ~65 min (five labs) · about 95 min total**

<!--
Welcome everyone and cover logistics. The lab runs entirely in the browser, so nobody needs Git or an editor installed.
Timing: the talk is about 30 minutes (an estimate). The labs add up to about 65 minutes: Lab 1 ~20, Lab 2 ~10, Lab 3 ~8, Lab 4 ~15, Lab 5 ~12. Lab 1 is the core. If the room is short on time, do Lab 1 and pick from the rest. Labs 2 to 5 are independent of each other, and "dojo prep N" catches anyone up.
-->

---

## Today

1. **Part 1:** Why version control matters
2. **Part 2:** What Git is, and the words teams use for it
3. **Part 3:** The everyday workflow
4. **Part 4:** Hands-on practice
5. Appendix: stash, undo, history, `.gitignore` (reference, if time allows)

> The goal: understand what Git is doing, then do it yourself.

<!-- Ask for a show of hands: who has used Git before? It tells you how fast to go through Part 2. The appendix is reference only. Skip it in the talk and point people at it afterwards. -->

---

<!-- _class: section-title -->

# Part 1

## Why version control matters

<!-- About 5 minutes for this whole part. -->

---

## Does this look familiar?

```text
dns-config.txt
dns-config-final.txt
dns-config-final-v2.txt
dns-config-REALLY-FINAL.txt
dns-config-REALLY-FINAL-fixed.txt
USE-THIS-ONE.txt
```

**Which is current? Who changed it? Why? Can we safely go back?**

<!-- Let the room react. Someone will admit to a file named "final-v2-fixed". Keep it quick: this is the problem Git solves, and the next slide says why it matters in ops. -->

---

## The operations reality

- Change tickets describe intent, but are not the changed files
- Shared drives allow accidental overwrites
- Backup dates are not a useful change history
- A bad configuration needs a fast, known rollback
- "Who changed this DNS record?" turns into incident detective work

> Scripts, runbooks, infrastructure, and DNS configuration all deserve history.

<!-- Ask the room for a real example: a change nobody could trace, or a rollback that took too long. Their stories land better than ours. This is also why the later workshops put DNS and certificates in Git. -->

---

## What Git gives us

| Capability        | Practical result                          |
| ----------------- | ----------------------------------------- |
| **Full history**  | Who changed what, when, and why           |
| **Safe branches** | Experiment away from the stable version   |
| **Collaboration** | Combine work without overwriting it       |
| **Review**        | Discuss and approve a change before merge |
| **Rollback**      | Return to a known state when needed       |

<!-- Don't read the table out. Pick two rows that fit the room. Review and rollback are the ones ops people care about most. Everything here comes back in the lab. -->

---

<!-- _class: section-title -->

# Part 2

## What Git is, and the words teams use

<!-- About 10 minutes. Vocabulary is the main thing people take away from this part, so go slowly on the mental model. -->

---

## Git is not Forgejo or Azure DevOps

| Git                          | Forgejo / Azure Repos                          |
| ---------------------------- | ---------------------------------------------- |
| Runs where you work          | Runs as a shared service                       |
| Records local history        | Hosts the team's remote copy                   |
| Creates branches and commits | Adds pull requests, review, and access control |
| Works offline                | Connects collaborators                         |

**Today:** Forgejo keeps the lab contained. The same Git commands work with Azure Repos, GitHub, or GitLab.

<!-- People mix these up all the time: "Git" gets used to mean the website. Git is the tool on your machine. Forgejo is where the team's shared copy lives. If your audience uses Azure DevOps, say so here: same Git, different host. -->

---

## Local and remote

```text
┌─────────────────────────────┐       ┌────────────────────────┐
│ Your workspace              │       │ Shared Git service     │
│                             │ push  │                        │
│ Files + complete history    │ ────► │ Team's remote copy     │
│                             │ ◄──── │                        │
└─────────────────────────────┘ pull  └────────────────────────┘
```

- **Local:** full history, branches, and commits
- **Remote:** the shared collaboration point, usually named `origin`

<!-- Stress that local has the full history, so nothing here needs the network until you push or pull. That surprises people who've only used shared drives. -->

---

## The mental model

<div class="flow">
	<span><strong>Working directory</strong><br><small>Your edits</small></span>
	<b>→</b>
	<span><strong>Staging area</strong><br><small>Selected changes</small></span>
	<b>→</b>
	<span><strong>Local repository</strong><br><small>Commits</small></span>
	<b>→</b>
	<span><strong>Remote repository</strong><br><small>Shared commits</small></span>
</div>

<!-- This is the anchor diagram. Trace a change left to right with your finger and name each arrow (add, commit, push). The staging area is where most beginners get stuck, so ask who has seen it before. Refer back to these four zones in Lab 1 and Lab 2. -->

---

## Repository and commit

### Repository
A project folder plus its complete history, stored by Git in `.git`.

### Commit
A named snapshot of selected changes, with author and time.

```text
7c13b8a  Add DNS record for api.example.com
```

**A useful message says what changed and gives future-you context.**

<!-- Keep it short here. Commit messages get a proper slide in Part 3. -->

---

## Branch and main

<div class="split">
<div>

- A **branch** is an independent line of work
- `main` is the stable, shared line
- One focused change per branch makes review and rollback easier

> Branch off. Make the change. Ask for review. Merge when ready.


</div>
<div>

<div class="mermaid">
gitGraph
	commit id: "Init"
	commit id: "Add homepage"
	branch add-api-record
	commit id: "Add endpoint"
	commit id: "Add tests"
	checkout main
	branch fix-typo
	commit id: "Fix typo"
	checkout main
	merge fix-typo id: "Merged fix" tag: "merge"
	checkout main
	merge add-api-record id: "Merged feature" tag: "merge"
</div>

<div class="small">

- **Step 1:** Branch off `main`
- **Step 2:** Commit on each branch, in isolation
- **Step 3:** Merge each one back on its own
- **Step 4:** Never commit to `main` directly

</div>

</div>
</div>

<!-- Walk the graph: two branches off main, each merged back on its own. The point is isolation. Nobody's half-finished work touches main. If the mermaid graph hasn't drawn, reload the slide. -->

---

## Moving between local and remote

| Term       | Meaning                                               |
| ---------- | ----------------------------------------------------- |
| **Clone**  | Make the first full local copy                        |
| **Remote** | A named connection to a hosted repo, usually `origin` |
| **Pull**   | Bring remote commits into your current branch         |
| **Push**   | Send your local commits to the remote                 |

```bash
git clone http://git-server:3000/training/sample-training-repo.git
git pull
git push
```

<!-- Clone once, then pull and push from then on. Don't demo it. Students do it in Lab 1 in about two minutes. -->

---

## Pull Request & Merge

### Pull request
A conversation and review **before** one branch is merged into another.

```text
branch → push → pull request → review → merge → main
```

**A pull request is a Forgejo/Azure DevOps feature, not a Git command.**

### Merge
Combine the histories of two branches.

```text
Like two rivers merging: separate currents become one flow, carrying both histories downstream
```

<!-- Say it plainly: Git has no "pull request" command. It's the hosting service's review step. People look for it in the CLI otherwise. Merge is the Git part. -->

---

## Conflict: Git needs a decision

Two branches changed the same line. Git can't guess which one you want, so it pauses the merge and marks the file:

<div class="split split-30-70">
<div>


```text
<<<<<<< HEAD
ttl: 600
=======
ttl: 300
>>>>>>> feature-branch
```
</div>
<div>

1. Open the file and decide: keep `600`, keep `300`, pick a new value, or combine them
2. Delete the `<<<<<<<`, `=======`, and `>>>>>>>` marker lines
3. `git add dns-config.txt`: tell Git this file is resolved
4. `git commit`: completes the merge with your resolution

</div>
</div>

**Conflicts are normal. Git stops instead of guessing.**

<!-- Conflicts scare people, so show the markers calmly: the top half is yours, the bottom half is theirs, and you decide. Lab 5 has everyone resolve one. If time is short, make the point and move on. -->

---

<!-- _class: section-title -->

# Part 3

## The everyday workflow

<!-- About 10 minutes. Five steps, one loop. Tell people the labs repeat these exact commands, so they don't need to memorize them now. -->

---

## 1. Clone once

```bash
git clone <repository-url>
cd sample-training-repo
```

You now have:

- The project files
- The complete Git history
- A remote named `origin`
- A checked-out default branch, usually `main`

<!-- Quick. Everyone does this in Lab 1. -->

---

## 2. Start from current `main`

```bash
git checkout main
git pull
git checkout -b add-yourname
```

- Move to the stable branch
- Get teammates' latest commits
- Create a branch for one focused change

> A current starting point means fewer surprises later.

**`checkout` or `switch`?** Newer Git also has `git switch -c add-yourname`: same result.

<!-- checkout vs switch: checkout is the classic do-everything command. It switches branches, but also checks out
individual commits and restores files. Newer Git added git switch (and git restore) to split branch-switching into
its own focused command: `git switch main` / `git switch -c add-yourname` do exactly what the slide does. We teach
checkout because most existing docs, tutorials and scripts use it, but students will see switch too. -->

---

## 3. Edit, inspect, select

```bash
# Edit roster/team.yaml

git status
git diff
git add roster/team.yaml
git status
```

- `status`: what state is my workspace in?
- `diff`: what did I actually change?
- `add`: which changes belong in the next commit?

**Use `git status` constantly.**

<!-- If you have a terminal handy, run status, diff and add once on a real file so people see the output change. Status is the command that gets people unstuck, so say so out loud. Staging lets you commit part of your work, but don't go deep on that today. -->

---

## 4. Commit a useful snapshot

```bash
git commit -m "Add Morgan to the team roster"
```

| Weak      | Useful                                  |
| --------- | --------------------------------------- |
| `updates` | `Add Morgan to the team roster`         |
| `fix`     | `Correct API record TTL to 300 seconds` |
| `stuff`   | `Document DNS rollback procedure`       |

**Describe the outcome, not the act of editing.**

<!-- Ask the room which column they'd rather find in a log at 2 a.m. during an incident. Keep the first line short and say what changed. -->

---

## 5. Push and request review

```bash
git push -u origin add-yourname
```

Then in the Git service:

1. Open a pull request into `main`
2. Explain the change
3. Review and discuss
4. Approve and merge
5. Delete the completed branch

`-u` connects the local branch to its remote counterpart.

<!-- The push is Git. The pull request is Forgejo. Lab 1 ends with students opening one into main. Branch deletion after merge is housekeeping, not a safety step. -->

---

## The whole loop

<div class="mermaid">
flowchart LR
	clone["clone once"] --> pull["pull"]
	pull --> branch["branch"]
	branch --> edit["edit"]
	edit --> status["status/diff"]
	status --> add["add"]
	add --> commit["commit"]
	commit --> push["push"]
	push --> merge["PR + merge"]
	merge -- "next focused change" --> pull
</div>

```bash
git status   # Where am I and what changed?
git log -1   # What did I most recently commit?
```

<!-- This is the recap. Trace the loop once, including the arrow back to pull. -->

---

<!-- _class: section-title -->

# Part 4

## Hands-on practice

<!-- Short pacing note: hand over to the labs here. -->

---

## Ready to practice?

In the browser you'll:
<div class="small">

1. Open your terminal
2. Clone the shared repository
3. Create a personal branch
4. Add yourself to `roster/team.yaml`
5. Inspect, stage, commit, and push
6. Open a pull request in Forgejo

</div>

Next: [labs.md](labs.md) for what each lab covers. 
Help: [cheat-sheet.md](cheat-sheet.md) is available here as well as within the lab environment.

> Questions before we put hands on keyboards?

<!-- Lab 1 is about 20 minutes and covers everything on this slide. Labs 2 to 5 are shorter and independent, about 45 minutes together. Tell people where to find the facilitator, and that stuck for more than a couple of minutes means ask. -->

---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: "[&larr; Hub](index.md)" -->

# Appendix

## When something happens

Optional demonstrations and reference slides

<!-- Reference only. Skip it in the talk. Stash, undo and history each have a lab (3, 2 and 4), so use these slides to answer questions. -->

---

## Pause unfinished work: stash

```bash
git stash          # Set uncommitted work aside
git checkout main  # Handle the interruption
git checkout -     # Return to the previous branch
git stash pop      # Restore the work
```

Useful when you need to switch context but are not ready to commit.

```bash
git stash list     # See saved stashes
```

**A stash is temporary local storage, not a backup or shared commit.**

<!-- Matches Lab 3. People forget stashes exist, so mention "git stash list". -->

---

## Undo at the right level

| Situation                     | Command                       |
| ----------------------------- | ----------------------------- |
| Uncommitted edit              | `git restore <file>`          |
| Staged, not committed         | `git restore --staged <file>` |
| Fix your latest local commit  | `git commit --amend`          |
| Undo an already shared commit | `git revert <commit>`         |

> Once history is pushed and shared, prefer `revert`: it records the undo without rewriting history.

<!-- Matches Labs 2 and 5. Read the table by situation, not by command. The rule of thumb: rewrite only what hasn't left your machine. -->

---

## Investigate history

```bash
git log --oneline --graph --all     # Every branch, drawn
git log --author=Bob --since=<date> # Filter by who and when
git show <commit>                   # One commit's changes
git blame <file>                    # Last commit for each line
git log -p <file>                   # Every change to one file
git log -S"text"                    # Commits that added or removed text
gitleaks git                        # Scan every commit for secrets
```

Use history to answer:

- What changed, when and why?
- Who has useful context?
- Did a secret ever get committed?

<!-- Lab 4 has students find a leaked secret in a practice repo. The point worth making: history keeps everything, so deleting the line later doesn't remove it. -->

---

## Keep local files local

`.gitignore` contains patterns Git should not track:

```gitignore
.DS_Store
.env
*.log
dist/
```

- Keeps `git status` focused on intentional work
- Does not stop tracking a file already committed
- <u>*Does not remove a secret from history*</u>

**If a secret is committed, rotate it immediately.** Find it: `git log -S`, `gitleaks`.

<!-- Rotate first, clean up history second. Rewriting history doesn't help if someone already cloned it. -->

---

## Quick reference

```bash
git status                    # Inspect current state
git checkout -b <branch>       # Create and enter a branch
git diff                      # Review unstaged changes
git add <file>                # Stage selected changes
git commit -m "<message>"     # Save a snapshot
git push -u origin <branch>   # Publish the branch
git log --oneline --graph     # Inspect history
git restore <file>            # Discard an uncommitted edit
git revert <commit>           # Safely undo shared history
```

<!-- Same list as the cheat sheet. Leave it up while people ask questions. -->

---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: "[&larr; Hub](index.md)" -->

# Let's go

## Next: [labs.md](labs.md) for what each lab covers, then your terminal

Keep [cheat-sheet.md](cheat-sheet.md) open in another tab. Ask for help any time. This is a lab, not a test.

<script type="module">
	import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs"
	mermaid.initialize({
		startOnLoad: false,
		theme: "dark",
		themeVariables: {
			background: "#18242e",
			primaryColor: "#21313c",
			primaryTextColor: "#e8f0f2",
			primaryBorderColor: "#3dd6c3",
			lineColor: "#a9bac2",
			git0: "#69aee8",
			git1: "#3dd6c3",
			gitBranchLabel0: "#111820",
			gitBranchLabel1: "#111820",
			commitLabelColor: "#e8f0f2",
			commitLabelBackground: "#111820",
			tagLabelColor: "#111820",
			tagLabelBackground: "#f0b95b",
		},
	})
	// Mermaid sizes each box from the text it measures, so it must measure
	// unscaled, in the real font. Drawing in place (startOnLoad) measures
	// inside the slide, which Marp scales to the window: a window smaller than
	// 1280x720 got boxes too small and labels cut off. mermaid.render() draws
	// in a scratch element on <body> instead; the SVG then goes into the slide.
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
	document.fonts.ready.then(draw)
</script>
