# Ansible on a Small Network (netlab-ansible)

About four and a half hours (best as a half day or two sessions): learn Ansible by configuring the same small network twice, first by hand and then with playbooks.
For anyone comfortable in a shell. The firewall is only the thing being configured.

Each student has a **pod** (a pc, a VLAN switch, a Linux firewall and an nginx web server) in two branches: **m** (by
hand) and **a** (by playbook). **Part 1** is nine by-hand labs (M1-M9) on branch m; **Part 2** is the same jobs as playbooks (A1-A9, plus the
stretch labs A10 secrets and A11 roles) on branch a. A2 and A3 are the build-it-yourself switch labs.

```sh
./dojo setup               # first time only
./dojo netlab-ansible      # up to 15 students (NETLAB_MAX_STUDENTS); class size from student_count in dojo.toml
```

| Part | Where |
|---|---|
| The pods, the checker, the seeded `~/netlab` and its labs | [`modules/netlab`](../../modules/netlab/README.md) |
| Slides, cheat sheet and lab pages | `content/slides/`, `content/lab/` (the full walkthroughs; the seeded `~/netlab/labs/*/README.md` are short pointers to them) |
| Running the session | [`FACILITATOR.md`](FACILITATOR.md) |
| Achievements (a pass of `dojo netlab check A<n>` earns lab A<n>) | [`ACHIEVEMENTS.md`](ACHIEVEMENTS.md), `achievements/` |
| Reference solutions (facilitator only) | `modules/netlab/solutions/` |

`MODULES="netlab openbao"` (lab A10 keeps its vault passwords in the shared OpenBao: `compose/openbao-setup.d/` makes each student a namespace `students/<name>` and the `student` policy); the achievements module is added when `ACHIEVEMENTS_ENABLED` is on (the default for a pack with a
catalog). The pack adds no compose overlay of its own.

## Demo bots

`./dojo netlab-ansible --test 3 --fast` starts three bots that work their own pods (pods 13-15 beside a class of 12; see
the module README for the cap). Each runs `dojo netlab check A<n>` after every lab it does, so lab achievements unlock for
them: `testuser1` (expert) does labs A1-A11 with one deliberate failed check, `testuser2` (intermediate) A1-A11
with a failed check before every fix, `testuser3` (novice) A1-A5 with wrong-directory runs, typos and early checks.
The bots copy the reference solution over the lab and run it; branch m, which a student builds by hand, gets the same
playbooks pointed at the `manual` group, so the checker's comparison of the two branches still holds. Not covered:
typing the hand-built commands over SSH, the interactive-zsh shell hook (bots use the engine's `bot.d` hook instead),
and anything in lab A11 beyond a role run (its check only looks for `roles/`). The bots do only the Part 2 (A) labs.
