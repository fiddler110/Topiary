# netlab-ansible: facilitator guide

For the person running the session. The module reference is [`modules/netlab/README.md`](../../modules/netlab/README.md)
and the design is `NETLAB-PLAN.md`; the deck's speaker notes carry the talking points.

**Honest status:** the module and every lab were run on the stack with the pod checker, but this pack has not yet been
run with a room, and the 15-student class has not been started at full size. The times below are estimates. Rehearse.

## The session at a glance (about 4.5 hours)

| Block | Minutes | What |
| ----- | ------- | ---- |
| Talk | ~25 | Why not by hand, what Ansible is (inventory, module, playbook), the pod and the two branches |
| Part 1, by hand (M1-M9) | ~105 | 10 each for M1-M7, then 15 (lockdown) and 20 (rebuild from clean, timed) |
| Part 2, playbooks (A1-A9) | ~150 | 10, 20, 20, 15, 15, 15, 15, 20, 20 (A9 is the capstone) |
| Stretch (A10 secrets, A11 roles) | rest of the time | Vault with OpenBao, then roles |
| Recap | ~10 | What surprised them: usually "run it twice", `changed=0`, and `compare.yml` flagging a hand-edit |

That is a half day, or two sessions with Part 1 in the first and Part 2 in the second. Part 2 stands alone if the class already knows the commands: the M labs are the reason Part 2 makes sense, so keep at least M4-M8 or demo them.

For a shorter slot (lunch and learn, about 90 minutes): talk 15, then do M5 and M8 by hand yourself (or as a pair), and have the class
do A4, A5 and A6, and show A9 live. The core path is **A1-A9**; A10 and A11 are stretch. The switch labs (M2/M3, A2/A3) come first because
they build the network the others use; skip them in a short slot (the pods start with the switch working, `reset_switch.yml` restores it).
Each A lab builds on the one before, so do them in order.

**Prerequisite:** a shell and `ssh`. No Ansible experience is assumed.

**The idea to land:** each lab is done by hand on branch **m**, then by playbook on branch **a**, then proved. The twist
in each lab (run it twice, undo it, change one value) is where the playbook wins.

## Before the session

**A day ahead**

1. `./dojo setup` if there is no `.env`. Set `PUBLIC_BASE_URL`, `GATEWAY_TOKEN` and `STUDENT_COUNT`.
2. **Class size: at most 15 students** (`NETLAB_MAX_STUDENTS=15`; the generator refuses more and the start stops). Each
   student has 8 containers and the facilitator's pod 00 adds 8 more: 128 for 15 students.
   **Key-limit caveat:** a rootless podman host allows about 200 containers per user (`kernel.keys.maxkeys`, one key
   each), and a start of this size is slow (many minutes). Do not run another large stack beside it. Raising
   `kernel.keys.maxkeys` needs root. `NETLAB_MANUAL_BRANCH=0` halves the load (the labs then lose their by-hand half),
   and `NETLAB_SWITCH=0` removes the switch and with it the switch labs (M2, M3, A2, A3). The class size is `student_count` in `dojo.toml`.
3. `./dojo netlab-ansible` and open `/admin`. Wait for **Terminals**, **Slides**, **netlab-checker** and the netlab
   status checks to go green. Account creation is the slowest part; yellow there is normal.
4. **Rehearse as a student** in a private window: Part 1 and then A1 to A9 with `dojo netlab check A<n>`, then `./dojo stop` and start clean.
5. `./dojo capacity netlab-ansible --students 15` to check the machine.
6. Skim the deck with speaker notes on.

**On the day, 15 minutes before:** start the stack; confirm `/`, `/slides`, `/admin`, and in a terminal
`ansible-playbook verify_topology.yml` is green for you (pod 00).

## During the session

**Your own pod (pod 00).** You are `root` in the terminal tab of `/admin`, and you have a pod of your own: `~/netlab`
with all the labs, hosts named `pc-m-00`, `fw-a-00` and so on. Use it to demo each lab live, to try a student's problem
without touching their pod, and to confirm a fix before you suggest it. The password for pod 00 is in
`~/.config/dojo/netlab-password`.

**Solutions.** The finished playbooks are in `modules/netlab/solutions/<lab>/` (read `solutions/README.md` first: the
order, the end state of each lab and how to try one on a pod). They are facilitator-only and never copied into
students' homes. The A9 (capstone) solution imports its sibling lab folders. Folder names keep the old numbers: A5 is `2-variables-loops`, A9 is `8-capstone`.

**The checker.** `dojo netlab check A<n>` (n is 1-11; the by-hand M labs have no check, use `probe.yml`) asks `netlab-checker` to look at the student's pod from
outside, on branch a, and (for A9) to compare the manual and automated branches. It prints one PASS or FAIL line per
assertion. It allows about 6 runs a minute per student, so tell the room to read the output before rerunning. A pass
earns the lab's achievement. **A11** (roles) only checks that `roles/` exists, so look at the roles yourself.

**Resets.**

| Who | How |
| --- | --- |
| One student, firewall or web node wrecked | `ansible-playbook reset_fw.yml -e branch=a` (or `-e branch=m`, or leave off `branch` for both), from `~/netlab` |
| One student, switch wrecked | `ansible-playbook reset_switch.yml` |
| One student wedged | Roster, **Release**, then **Reset** for a fresh terminal (check afterwards that `~/netlab` is still there) |
| The whole pod set back to the baseline | `./dojo restart` recreates the pods at baseline and keeps each student's `~/netlab`. `./dojo stop` wipes everything |

**What to say out loud.** The firewall is only the thing being configured; the lesson is Ansible. Branch m is the
reference: "does your playbook end where your hands ended?" (compare them in A9). Tell students to run every playbook twice.

**Achievements.** Each lab milestone fires when that lab's `dojo netlab check` passes. They are listed in
[`ACHIEVEMENTS.md`](ACHIEVEMENTS.md); the nine core-path labs (A1-A9) count towards the certificate, stretch labs
(A10, A11) do not. The capstone, "Rebuild From Clean", is a challenge-style unlock: once a student has passed `dojo netlab check` on labs A1 to A9, `dojo check capstone` asks the netlab checker (not the terminal) whether it last saw each of them pass on that
student's pod. The checker's record is in memory, so after a checker restart (`./dojo restart netlab-checker`) students
re-run the checks it names before the capstone passes; one already earned stays earned.

## When something breaks

| Symptom | Likely cause and fix |
| ------- | -------------------- |
| `ansible all -m ping` shows `UNREACHABLE` for a whole pod | Pods are still starting (a full class takes minutes). Wait, then `verify_topology.yml`. If it persists, `./dojo logs` and check the node containers for that pod |
| `UNREACHABLE` only on the web node after A7 | The student loaded a bad `sshd_config`; the node dies on reload. Fix: `./dojo restart <node>` or restart the stack for that pod, or `reset_fw.yml` once the node is up |
| `dojo netlab check` says "the checker said no (429)" | The rate limit; wait a minute |
| Check A9 fails only with `compare` lines | Branch m and a differ. Run `compare.yml`; the usual cause is a hand-typed rule on m with no matching task on a (or the reverse) |
| Start stops with a STUDENT_COUNT error | Over 15. Lower it, or raise `NETLAB_MAX_STUDENTS` only after measuring the host |
| Start stalls or fails with "Disk quota exceeded" in `crun` | The per-user key limit (see above). Fewer students, or `NETLAB_MANUAL_BRANCH=0` |
| A student cannot log in to a node by hand | Wrong pod (they used another pod's name) or the password: `cat ~/.config/dojo/netlab-password` |
| The `/netlab-view` page is empty | The page is read-only and needs the checker up; it is not required for the labs |

## After the session

- `./dojo stop` wipes everything: pods, volumes, every home and every pod's state.
- Note anything that confused the room or a wrong timing in `ROADMAP.md` and fix the lab.
