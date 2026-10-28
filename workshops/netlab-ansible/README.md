# Ansible on a Small Network (netlab-ansible)

About three hours: learn Ansible by configuring the same small network twice, first by hand and then with playbooks.
For anyone comfortable in a shell. The firewall is only the thing being configured.

Each student has a **pod** (a pc, a VLAN switch, a Linux firewall and an nginx web server) in two branches: **m** (by
hand) and **a** (by playbook). Labs 0-8 guide the firewall and web work; S1-S3 are build-it-yourself switch labs.

```sh
./dojo setup               # first time only
./dojo netlab-ansible      # up to 15 students (NETLAB_MAX_STUDENTS); default STUDENT_COUNT=12
```

| Part | Where |
|---|---|
| The pods, the checker, the seeded `~/netlab` and its labs | [`modules/netlab`](../../modules/netlab/README.md) |
| Slides, cheat sheet and lab pages | `content/slides/`, `content/lab/` (the lab pages point at the seeded `~/netlab/labs/*/README.md`) |
| Running the session | [`FACILITATOR.md`](FACILITATOR.md) |
| Achievements (a pass of `dojo netlab check N` earns lab N) | [`ACHIEVEMENTS.md`](ACHIEVEMENTS.md), `achievements/` |
| Reference solutions (facilitator only) | `modules/netlab/solutions/` |

`MODULES="netlab"`; the achievements module is added when `ACHIEVEMENTS_ENABLED` is on (the default for a pack with a
catalog). The pack adds no compose overlay of its own.

## Demo bots

`./dojo netlab-ansible --test 3 --fast` starts three bots that work their own pods (pods 13-15 beside 12 students; see
the module README for the cap). Each runs `dojo netlab check N` after every lab it does, so lab achievements unlock for
them: `testuser1` (expert) does labs 0-8 and S1-S3 with one deliberate failed check, `testuser2` (intermediate) labs 0-8
with a failed check before every fix, `testuser3` (novice) labs 0-3 with wrong-directory runs, typos and early checks.
The bots copy the reference solution over the lab and run it; branch m, which a student builds by hand, gets the same
playbooks pointed at the `manual` group, so the checker's comparison of the two branches still holds. Not covered:
typing the hand-built commands over SSH, the interactive-zsh shell hook (bots use the engine's `bot.d` hook instead),
and anything in lab 7 beyond a role run (its check only looks for `roles/`).
