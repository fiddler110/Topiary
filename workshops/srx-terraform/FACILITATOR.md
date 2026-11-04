# srx-terraform: facilitator guide

For the person running the session. The technical reference is [`README.md`](README.md); the deck's speaker notes carry the talking points. This guide is the practical part.

**Honest status:** nobody has run this with a room yet, and the pack was written before the Dojo WAN simulator was finished. The lab commands were validated with `terraform validate` only; run the rehearsal below before a class.

## The session at a glance (about 2¾ hours)

| Block | Minutes | What |
| ----- | ------- | ---- |
| Talk, Parts 1-5 | ~30 | Why Mist and Terraform, the roles (spoke template, hub profile, device override), variables and claim flow, state and workflow, drift and import. *A guess until a dry run.* |
| Labs 0-5 | ~70 | 10 + 12 + 12 + 12 + 12 + 12. Objects, template, sites, claim, layers |
| Labs 6-9 | ~60 | 15 + 15 + 15 + 15. Modules, team workflow, drift and import, capstone |
| Recap and questions | ~5 | Ask each table what surprised them |

Lab times are the estimates in `content/lab/README.md`. The duration in `workshop.env` (`~2¾ h`) must follow this table. **In a 2-hour slot**, stop after Lab 6 (the estate is built and structured) and move Lab 7 to the next session. Labs 7 to 9 depend on each other; Lab 8 and Lab 9 can be skipped together.

Keep the order. Nobody destroys anything: every lab builds on the last.

## Before the session

**A day ahead**

1. `./dojo setup` if there is no `.env`; set `PUBLIC_BASE_URL`, `GATEWAY_TOKEN` and `STUDENT_COUNT`.
2. `./dojo srx-terraform` (the first build downloads Terraform and the 96 MB provider). In `/admin` check the status strip: Forgejo, Terminals, Slides and Dojo WAN green.
3. Size the machine: `./dojo capacity srx-terraform --students 30`. A full apply is about 100 MB of memory for a moment; 15 students applying at once is about 1.5 GB in the terminal.
4. **Rehearse as a student**: private window, then Labs 0 to 9, using `dojo check N` at the end of each. Then `./dojo stop` and start clean.
5. **Check the Junos preview against a real SRX.** The rendered config is invented from the parts the team can confirm (interfaces, zones, policies, NAT). Have someone who knows SRX read `dojo wan config` for one site before the class and fix any line that would mislead. Also confirm Lab 5 against the Mist documentation: a template for spoke sites, a hub profile for a hub gateway (never both on one gateway), the `dns_override`/`ntp_override` flags, and site vars overridden by device `vars`.
6. Skim the deck with its speaker notes on.

**On the day, 15 minutes before:** start the stack, confirm the landing page shows a **Dojo WAN** card, `/slides` and `/admin`. Open the **Dojo WAN** tab in `/admin`: it shows every org, and the drift button for Lab 8.

## During the session

- **Everyone sees only their own org.** Your facilitator token sees all of them: use the Dojo WAN tab to look at a student's sites, gateways and events when they are stuck.
- **Lab 4:** claim codes differ per student. Students copy them from `dojo wan delivery`. A code is exactly 15 characters of `0-9A-Z`.
- **Lab 6:** the point is the first plan, with seven destroys. Tell the room before they start: do not apply that one. `dojo check 6` flags a site whose id changed, meaning someone applied without the `moved` blocks. Recovery: nothing is lost, the sites are rebuilt; `terraform apply` completes it, and the claimed gateways come back with the next apply.
- **Lab 7:** needs a second terminal pane for the lock demo. The pull request is opened in the student's own fork and reviewed by a neighbour; students merge their own. If the room is large, you review two or three and let pairs do the rest.
- **The drift button (Lab 8).** In the Dojo WAN tab, press **Drift** to make a canned out-of-band edit in every org (logged with actor `portal:facilitator`). Do it when most of the room has reached Lab 8 step 1. Students who get there first, or who want to go on, make the same kind of edit with the `curl` in the lab, so you do not hold anyone up. The lab text says the edit is the `corp` VLAN; if the canned drift changes something else, tell the room to read their own `plan` and `dojo wan events` rather than the lab's sample output.

## When something breaks

| Symptom | Likely cause and fix |
| ------- | -------------------- |
| No `MIST_` variables, or `x509: certificate signed by unknown authority` | The shell started before Dojo WAN was ready. A new terminal tab fixes it. |
| `The configured Mist Host does not match the supported Clouds` | `MIST_HOST` is empty. New tab. |
| `claim code ... is not valid` | Code is not 15 characters of `0-9A-Z`. Copy the `magic` column. |
| `Error acquiring the state lock` and nobody is running | A killed run left a lock. Check, then `terraform force-unlock <ID>`. |
| `Error: Failed to get existing workspaces` or 401 in Lab 7 | No `TF_HTTP_USERNAME`/`TF_HTTP_PASSWORD`. New tab. |
| `Inconsistent result after apply` | The simulator answered differently from what was sent. Capture the plan and the resource, note it in `ROADMAP.md`, and carry on with a different resource. |
| `dojo check N` says no gateway in a site | The student has not applied Lab 4, or used the wrong site key in `terraform.tfvars`. |
| A student is far behind | `dojo prep N` builds labs 1 to N-1 for them in about a minute. It keeps replaced files as `*.dojo-bak`. |
| Student wedged | `/admin` roster, **Release** their tile; the Dojo WAN tab can reset their org. |

## Known issues and limits

- The **Junos config is a preview**, not a real commit, and the role model follows Mist's documentation as the simulator reads it. Say so in the room.
- `dojo check` is provided by this pack (`compose/terminal/srx-check`). If the achievements module is added later, its `check` link and this one collide: fold these checks into the achievements catalog instead.
- The token is never moved to a secrets manager in this version (Lab 7 explains it; it does not do it). The plan's `openbao` step and the runner-pool `plan on pull request` are future work.
- The state name `srx-estate` and the checks' wording follow the simulator contract (`docs/SRX-MIST-PLAN.md` section 10). Changing the state path means editing Lab 7, `srx-check` and `stages/lab7`.
- If you change a lab's HCL, the end-of-lab files in `content/stages/` must change with it (they are what `dojo prep` and the bots use). They were cut from the lab pages.

## After the session

`./dojo stop` wipes everything, including every org. Write what confused people, real timings and any failure not in the table into `ROADMAP.md`, and fix the lab.
