# netlab-ansible: facilitator guide

For the person running the session. The module reference is [`modules/netlab/README.md`](../../modules/netlab/README.md)
and the design is `NETLAB-PLAN.md`; the deck's speaker notes carry the talking points.

**Honest status:** the module and every lab were run on the stack with the pod checker, but this pack has not yet been
run with a room, and the 15-student class has not been started at full size. The times below are estimates. Rehearse.

## The session at a glance (about 3 hours)

| Block | Minutes | What |
| ----- | ------- | ---- |
| Talk | ~20 | Why not by hand, what Ansible is (inventory, module, playbook), the pod and the two branches |
| Core labs 0-4 | ~85 | 10 + 15 + 20 + 20 + 20 |
| Core labs 6 and 8 | ~35 | 20 + 15 |
| Stretch (5, 7, S1-S3) | rest of the time | Vault, roles, and the build-it-yourself switch labs |
| Recap | ~10 | What surprised them: usually "run it twice", `changed=0`, and `compare.yml` flagging a hand-edit |

For a shorter slot (lunch and learn, about 90 minutes): talk 15, then labs 0, 1, 2 and 3, and show lab 8 yourself. The
core path is **0, 1, 2, 3, 4, 6, 8**. Labs 5 and 7 and S1-S3 are stretch. Do S1-S3 in order and only after lab 8: they
break the switch on purpose and `reset_fw.yml` undoes the firewall labs.

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
   and `NETLAB_SWITCH=0` removes the switch and with it labs S1-S3. The default here is `STUDENT_COUNT=12`.
3. `./dojo netlab-ansible` and open `/admin`. Wait for **Terminals**, **Slides**, **netlab-checker** and the netlab
   status checks to go green. Account creation is the slowest part; yellow there is normal.
4. **Rehearse as a student** in a private window: labs 0 to 4 and 8 with `dojo netlab check`, then `./dojo stop` and start clean.
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
students' homes. Lab 8's solution imports its sibling lab folders.

**The checker.** `dojo netlab check N` (N is 0-8, S1-S3) asks `netlab-checker` to look at the student's pod from
outside, on both branches, and to compare the manual and automated branches. It prints one PASS or FAIL line per
assertion. It allows about 6 runs a minute per student, so tell the room to read the output before rerunning. A pass
earns the lab's achievement. **Lab 7** (roles) only checks that `roles/` exists, so look at the roles yourself.

**Resets.**

| Who | How |
| --- | --- |
| One student, firewall or web node wrecked | `ansible-playbook reset_fw.yml -e branch=a` (or `-e branch=m`, or leave off `branch` for both), from `~/netlab` |
| One student, switch wrecked | `ansible-playbook reset_switch.yml` |
| One student wedged | Roster, **Release**, then **Reset** for a fresh terminal (check afterwards that `~/netlab` is still there) |
| The whole pod set back to the baseline | `./dojo restart` recreates the pods at baseline and keeps each student's `~/netlab`. `./dojo stop` wipes everything |

**What to say out loud.** The firewall is only the thing being configured; the lesson is Ansible. Branch m is the
reference: "does your playbook end where your hands ended?". Tell students to run every playbook twice.

**Achievements.** Each lab milestone fires when that lab's `dojo netlab check` passes. They are listed in
[`ACHIEVEMENTS.md`](ACHIEVEMENTS.md); the seven core-path labs (0-4, 6, 8) count towards the certificate, stretch labs
do not. The capstone, "Rebuild From Clean", is a challenge-style unlock: once a student has passed `dojo netlab check` on labs 0-4, 6
and 8, `dojo check capstone` asks the netlab checker (not the terminal) whether it last saw each of them pass on that
student's pod. The checker's record is in memory, so after a checker restart (`./dojo restart netlab-checker`) students
re-run the checks it names before the capstone passes; one already earned stays earned.

## When something breaks

| Symptom | Likely cause and fix |
| ------- | -------------------- |
| `ansible all -m ping` shows `UNREACHABLE` for a whole pod | Pods are still starting (a full class takes minutes). Wait, then `verify_topology.yml`. If it persists, `./dojo logs` and check the node containers for that pod |
| `UNREACHABLE` only on the web node after lab 4 | The student loaded a bad `sshd_config`; the node dies on reload. Fix: `./dojo restart <node>` or restart the stack for that pod, or `reset_fw.yml` once the node is up |
| `dojo netlab check` says "the checker said no (429)" | The rate limit; wait a minute |
| Check fails only with `compare` lines | Branch m and a differ. Run `compare.yml`; the usual cause is a hand-typed rule on m with no matching task on a (or the reverse) |
| Start stops with a STUDENT_COUNT error | Over 15. Lower it, or raise `NETLAB_MAX_STUDENTS` only after measuring the host |
| Start stalls or fails with "Disk quota exceeded" in `crun` | The per-user key limit (see above). Fewer students, or `NETLAB_MANUAL_BRANCH=0` |
| A student cannot log in to a node by hand | Wrong pod (they used another pod's name) or the password: `cat ~/.config/dojo/netlab-password` |
| The `/netlab-view` page is empty | The page is read-only and needs the checker up; it is not required for the labs |

## After the session

- `./dojo stop` wipes everything: pods, volumes, every home and every pod's state.
- Note anything that confused the room or a wrong timing in `ROADMAP.md` and fix the lab.
