---
marp: true
theme: default
paginate: true
size: 16:9
html: true
style: |
    @import url('assets/themes/presentation.css');
    .mermaid { text-align: center; margin: 8px 0; }
    .mermaid:not([data-processed]) { visibility: hidden; }
    .mermaid svg { max-height: 400px; }
    .mermaid foreignObject p, .mermaid foreignObject div { margin: 0 !important; line-height: 1.35 !important; }
footer: "[&larr; Hub](index.md) &nbsp;|&nbsp; Cloud Policy as Code | Engineering & IT Operations"
---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _footer: "[&larr; Hub](index.md)" -->

# Cloud Policy as Code

## Guardrails that live in git, not in a wiki

Builds on OpenTofu Basics: the same plan, review and apply loop, now applied to the rules themselves

**Talk ~45 min · Labs 0-12 ~242 min · Capstone ~45 min · about 5.5 hours total**

<!--
Timing. Labs 0 to 12 add up to 242 minutes from the lab README (10, 8, 12, 15, 12, 15, 15, 30, 20, 25, 25, 30, 25). The capstone is about 45 more. The talk time is my estimate from the slide count, not a measured run.

By part: Part 1 ~7 min, Part 2 ~10, Part 3 ~10, Part 4 ~8, Part 5 ~6, Part 6 ~5.

The README suggests two sittings (labs 0-6, then 7-12). If you split it, stop the talk after Part 4 and give Parts 5 and 6 at the start of the second sitting.

Say early: policy applies are slow (about 3.5 minutes). That is not a bug.
-->

---

## Today

1. **Part 1:** Why guardrails, and why as code
2. **Part 2:** The model: definition, assignment, scope, effect
3. **Part 3:** Rolling out safely: audit, compliance, exemptions
4. **Part 4:** Reuse and repair: sets, modify, and why applies are slow
5. **Part 5:** Shift left: the same rule in Rego, with tests
6. **Part 6:** The pipeline and drift

> Everything you apply today is "Dojo Cloud Policy": the same model as the big clouds' policy services.

<!-- Set expectations in about a minute. The labs follow the same order as this list, so what they hear in a Part is what they do next. -->

---

<!-- _class: section-title -->

# Part 1

## Why guardrails, and why as code

<!-- Short part. Get the problem on the table, then move on. -->

---

## The guardrail problem

- Anyone with access can create anything: wrong region, no owner tag, a 64-core container
- Reviews catch some of it, after the fact
- A wiki page says "use Canadian regions". Nothing enforces it
- Fixing it later means finding every offender by hand
- Rules in people's heads drift as people change

> A guardrail is a rule the platform checks for you, on every request, whoever makes it.

<!-- About 2 minutes. Ask the room who has seen a resource with no owner tag. Someone always has. Let them tell the story before you move on. -->

---

## Access control is not policy

| | Answers | Example |
| --- | --- | --- |
| **Roles** | May this person create resources? | "Sam can create container groups" |
| **Policy** | What may those resources look like? | "...but not in `eastus`, not without a `costCenter` tag" |

- Policy is enforced **by the cloud, at write time**, for every tool: portal, CLI, OpenTofu, a pipeline
- Policy is **data**: a document the cloud evaluates, so you can store, review and test it

<!-- About 2 minutes. This is the Lab 1 idea. The point to land: a person who is allowed to create a container group can still create a bad one, and only policy catches that. Roles and policy are two different questions. -->

---

## Policy as code: the loop

<div class="mermaid">
flowchart LR
  w["Write the rule<br/>in git"] --> t["Test it<br/>opa test"]
  t --> r["Review it<br/>pull request"]
  r --> a["CI applies it<br/>on merge"]
  a --> c["The cloud<br/>enforces it"]
  c --> d["Drift check<br/>git wins"]
  d --> w
</div>

Same loop you used for infrastructure in OpenTofu Basics. The only new thing is that **the thing in git is a rule**.

<!-- About 2 minutes. This is the whole workshop on one slide, and the labs fill it in from left to right. Labs 3 to 8 are "write", 9 and 10 are "test", 11 is "review and apply", 12 is "drift". Come back to this slide at the end if people lose the thread. -->

---

## What is in the repo

| Folder | Holds | Applied by |
| --- | --- | --- |
| `infra/` | The app: a resource group and a container group | you, then CI |
| `policy/cloud/` | Definitions, assignments, sets, exemptions | you, then CI |
| `policy/rego/` | Rego rules and their tests | checked on every PR |
| `.forgejo/workflows/` | `pr.yml`, `main.yml`, `drift.yml` | Forgejo |

- You work in your own **fork** of the team repo (Lab 0)
- `infra/` and `policy/cloud/` have **separate state**: change the rules without touching the app

<!-- About 2 minutes. Lab 0 is setup: fork, CI secrets, deploy the app. Policy is assigned at subscription scope so it never needs the app to exist first. Tell them not to push to main until Lab 11, because a push runs the Apply pipeline. -->

---

<!-- _class: section-title -->

# Part 2

## The model

<!-- Labs 1 and 2. This is the vocabulary part. Go slowly, because every later slide uses these words. -->

---

## The model in five words

| Word | What it is | Example |
| --- | --- | --- |
| **Definition** | The rule itself: a condition and an effect | "tag `costCenter` must exist" |
| **Assignment** | Switches a definition on at a scope, with settings | the rule, on the subscription, as `deny` |
| **Scope** | Where it applies: subscription, resource group | everything under the subscription |
| **Effect** | What happens on a match | `deny`, `audit`, `modify` |
| **Compliance** | What the cloud reports afterwards | "`rg-legacy` is NonCompliant" |

A definition on its own does nothing. **Nothing is enforced until it is assigned.**

<!-- About 2 minutes. The lab calls these the five parts. An analogy that works: a definition is a function, an assignment is a call with arguments. Write once, assign many times. People mix definition and assignment up constantly, so say the split out loud. -->

---

## Scope and inheritance

```text
platform scope      <- built-in guardrails, read-only to you
  └─ subscription   <- your assignment here covers everything below
       └─ resource group  <- or assign narrower
            └─ container group, network, ...
```

- An assignment applies to its scope **and everything beneath it**
- Rules add up: a resource must satisfy every assignment that reaches it
- There is no "closer scope wins" for `deny`. To carve out an exception, use an exemption
- Built-ins here: Canadian regions, tags `owner` and `env`, two images, cpu and memory caps, port 80, 10 env vars

<!-- About 2 minutes. Show the Policy blade in the portal and open one built-in (Lab 2 does this). The common wrong guess is that a narrower assignment can loosen a broader one. It can't. -->

---

## Anatomy of a rule

```json
{
  "mode": "Indexed",
  "policyRule": {
    "if":   { "field": "location",
              "notIn": ["canadacentral", "canadaeast"] },
    "then": { "effect": "deny" }
  }
}
```

- **if**: the condition. When it is true, the resource is a match
- **then**: what the engine does about the match
- **mode**: `Indexed` skips resource groups, `All` includes them

<!-- About 2 minutes. Read it aloud: "if the location is not in the list, deny". Mode matters in Lab 3: the costCenter rule uses All because resource groups need the tag too, and Indexed would skip them. -->

---

## A rule describes the bad case

```json
{
  "if":   { "field": "tags['costCenter']", "exists": false },
  "then": { "effect": "[parameters('effect')]" }
}
```

- "No `costCenter` tag" is the **match**, so it is the thing that gets stopped
- Beginners write the good case ("has a tag") and get the rule backwards
- Note the effect: a **parameter**, not the word `deny`. The assignment picks how strict to be

<!-- About 2 minutes. This is the Lab 3 rule, so they will see the same file in a few minutes. Ask: "If I wanted to require a tag, what condition do I write?" Wait for someone to say "the tag exists", then correct it gently. -->

---

## Fields, aliases, combinators

```json
{ "allOf": [
    { "field": "type", "equals": "Microsoft.ContainerInstance/containerGroups" },
    { "anyOf": [
        { "field": "tags['costCenter']", "exists": "false" },
        { "field": "tags['costCenter']", "isBlank": "true" } ] } ] }
```

- Fields: `type`, `name`, `location`, `tags['x']`, plus **aliases** for resource properties
- Combine with `allOf`, `anyOf`, `not`
- Operators are in the cheat sheet; `inExact` and `isBlank` are Dojo extras

<!-- About 2 minutes. Walk the nesting from the outside in: it must be a container group, and the tag must be missing or blank. Always put a type check first, or the rule tries to read container properties off every resource. -->

---

## Worked example: the images rule

```json
{ "allOf": [
    { "field": "type", "equals": "Microsoft.ContainerInstance/containerGroups" },
    { "not": {
        "field": "Microsoft.ContainerInstance/containerGroups/containers[*].image",
        "in": "[parameters('allowedImages')]" } } ] }
```

- `containers[*].image` is a list: the condition must hold for **every** container
- One image outside the list makes the whole group non-compliant
- The file holds **no image names**. The assignment supplies them

<!-- About 2 minutes. This is the rule from Lab 5 and the capstone, so it pays to read it now. Ask: "Does this file contain any image names?" The answer is no, and that is the setup for parameters. -->

---

## Effects

| Effect | What it does |
| --- | --- |
| `deny` | Refuses the write with a 403 |
| `audit` | Allows it, marks it NonCompliant |
| `modify` | Adds, replaces or removes tags for you |
| `append` | Adds fields to the request |
| `disabled` | The rule stays defined but does nothing |

You will use `deny`, `audit` and `modify` today. The same rule can run as any of them.

<!-- About 1 minute. Don't dwell on append or disabled. Disabled is handy as an allowed value on the effect parameter: a rule you can switch off from the assignment without deleting it. -->

---

## Reading a refusal

```text
RequestDisallowedByPolicy: resource 'ci-sam-app' was disallowed by policy.
  assignment: require-costcenter   message: Add a costCenter tag.
```

- A `deny` comes back as **403 `RequestDisallowedByPolicy`**
- It names the resource, the assignment, the definition and the message
- It shows up at `apply`, not at `plan`: the cloud decides when the write arrives
- A missing permission is a different error. A denied write has no side effects

> Write a clear `nonComplianceMessage`. It is the only help the engineer gets.

<!-- About 2 minutes. Lab 1 makes everyone trigger this on purpose: a resource group in eastus, then one with no env tag. Tell them a denied apply is the point, not a mistake. The scratch folder has its own state so the app is never at risk. -->

---

<!-- _class: section-title -->

# Part 3

## Rolling out safely

<!-- Labs 3, 4, 5 and 8. This is where the habits come from. -->

---

## Definition and assignment in OpenTofu

```hcl
resource "azurerm_policy_definition" "require_costcenter" {
  name        = "require-costcenter-tag"
  policy_type = "Custom"
  mode        = "All"
  policy_rule = file("${path.module}/rules/require-costcenter-tag.json")
}

resource "azurerm_subscription_policy_assignment" "require_costcenter" {
  name                 = "require-costcenter"
  subscription_id      = data.azurerm_subscription.current.id
  policy_definition_id = azurerm_policy_definition.require_costcenter.id
}
```

<!-- About 2 minutes, and this is cut down from the Lab 3 block (the parameters argument is trimmed to fit). Two resources: the rule, then the switch. The assignment names the definition by reference, so tofu creates the definition first and you never need depends_on. Rule JSON lives in its own file so an editor or a test can read it as plain JSON. -->

---

## Parameters: one rule, many uses

```json
"parameters": {
  "allowedImages": { "type": "Array" },
  "effect": { "type": "String", "defaultValue": "deny",
              "allowedValues": ["deny", "audit", "disabled"] }
},
"policyRule": {
  "if": { "field": "image", "notIn": "[parameters('allowedImages')]" },
  "then": { "effect": "[parameters('effect')]" }
}
```

- The **assignment** supplies the values
- Same definition: subscription allows `1.0` and `2.0`, one resource group allows only `2.0`

<!-- About 2 minutes. Parameters are why you write the rule once. The slide shows a simplified field name for space. The real rule uses the full containers[*].image alias from the previous worked example. -->

---

## One definition, two assignments

```hcl
resource "azurerm_subscription_policy_assignment" "images_subscription" {
  # ...
  parameters = jsonencode({ allowedImages = { value = ["dojo/hello:1.0", "dojo/hello:2.0"] } })
}

resource "azurerm_resource_group_policy_assignment" "images_strict" {
  # ...
  parameters = jsonencode({ allowedImages = { value = ["dojo/hello:2.0"] } })
  enforce    = false
}
```

- Different **scope**, different **parameter values**, same rule
- The resource type changes with the scope: `subscription_id` or `resource_group_id`
- `enforce = false` is the new idea. Next slide

<!-- About 2 minutes. This is Lab 5. The ... elisions hide name, scope and definition id; the lab has the full block. Point at the two resource types: that is how scope shows up in code. -->

---

## Audit before deny

| Step | Effect | What happens to a bad resource |
| --- | --- | --- |
| 1 | `audit` | Created, but marked non-compliant |
| 2 | read compliance | You see exactly who would break |
| 3 | fix or exempt the offenders | The list shrinks to zero |
| 4 | `deny` | New bad requests are refused |

- Turning on `deny` blind breaks pipelines and people on day one
- With `effect` as a parameter, step 4 is a **one-line change**

<!-- About 2 minutes. This is the habit to take home. Lab 4 shows the failure first: add a legacy resource group with no costCenter tag while the rule is on deny, and it is refused. The rule is right, but it blocks something that can't comply yet. -->

---

## DoNotEnforce: the dry run

- Assignment `enforce = false` is **DoNotEnforce**: the rule evaluates and reports, but never blocks
- In Lab 5, `images-strict` runs this way. The app is on `1.0`, so it shows **NonCompliant** before anyone is blocked
- Fix the offender (move the app to `2.0`), then delete the `enforce = false` line to start enforcing
- Both `audit` and DoNotEnforce are dry runs. `audit` changes the **effect**; DoNotEnforce changes the **assignment**

> Lab 12 comes back to this setting from the other side: someone flips it by hand.

<!-- About 2 minutes. Students ask when to use which. Short answer: audit when you are writing the rule, DoNotEnforce when the rule is done and you are about to switch it on. Both give you the same report. -->

---

## Compliance: reading the verdict

- Evaluated on every write, and on demand ("Evaluate now" in the portal)
- States: **Compliant**, **NonCompliant**, **Exempt**, **NotStarted**
- The Policy blade lists assignments, resources and the reason for each verdict
- Compliance is the answer to "are we okay?". A `deny` rule leaves nothing non-compliant, because nothing bad got in. An `audit` rule is where the list is long

<!-- About 1 minute. Open the Policy blade and click into one NonCompliant row to show the reason text. Students tend to expect a deny assignment to show non-compliant resources; it only will for things created before the rule existed, or while enforcement is off. -->

---

## Exemptions are a process, not a hole

```hcl
resource "azurerm_resource_group_policy_exemption" "legacy_costcenter" {
  resource_group_id               = data.azurerm_resource_group.legacy.id
  policy_assignment_id            = azurerm_subscription_policy_assignment.team_baseline.id
  policy_definition_reference_ids = ["costcenter"]
  exemption_category              = "Waiver"
  description                     = "Predates the tagging rule; ticket OPS-123."
  expires_on                      = "2026-10-09T00:00:00Z"
}
```

- Scoped to one resource group, one assignment, **one member rule** of a set
- Every argument is a decision somebody should be able to question

<!-- About 2 minutes. This is Lab 8, cut down to the arguments that matter (name and display_name are left out for space). Point at policy_definition_reference_ids: without it the waiver would cover the whole baseline, not just costCenter. -->

---

## Waiver or mitigated, and always an end date

- **Waiver**: we accept the risk
- **Mitigated**: the risk is handled another way. Say how in the description
- Always set `expires_on` and a `description` with the reason and the ticket
- Raise it as a **pull request**, so the waiver is reviewed and visible in git
- Expired exemptions stop applying: the resource is checked again

> An exemption in git has an owner and an end date. One in the portal has neither.

<!-- About 2 minutes. In the lab they set the expiry a week out. Ask: "What happens on the day it expires?" The resource is evaluated again and, if it still has no tag, it shows NonCompliant. There is a bonus challenge on this at the end of Lab 8. -->

---

<!-- _class: section-title -->

# Part 4

## Reuse and repair

<!-- Labs 6 and 7, plus the slow-apply warning that applies to all of them. -->

---

## Policy sets: bundle the baseline

```hcl
resource "azurerm_policy_set_definition" "baseline" {
  name = "team-baseline"
  policy_definition_reference {
    policy_definition_id = azurerm_policy_definition.costcenter.id
    reference_id         = "costcenter"
  }
  # ... images, locations
}
```

- One **assignment** of the set covers every member; compliance is shown per member
- Add a member rule and it applies **without a new assignment**

<!-- About 2 minutes. Lab 6 first removes the two separate subscription assignments the set replaces, otherwise each rule is evaluated twice. It keeps the definitions (the set refers to them) and keeps images_strict (the set can't express a stricter list on one resource group). The reference_id is what an exemption points at. -->

---

## Sets pass parameters down

<div class="mermaid">
flowchart TD
  SA["Assignment: team-baseline<br/>scope + values"] --> SD["Set: Team baseline<br/>set parameters"]
  SD -->|"costcenter"| D1["Require a costCenter tag"]
  SD -->|"images"| D2["Allowed container images"]
  SD -->|"locations"| D3["Allowed locations"]
</div>

- The assignment fills the set's parameters, the set passes each one to the member that needs it
- A definition still used by an assignment or a set can't be deleted (`PolicyDefinitionInUse`)

<!-- About 2 minutes. This is the extra level in the model: assignment, then set, then members. The PolicyDefinitionInUse error is on the cheat sheet, and people hit it when they try to tidy up in the wrong order. Delete the assignment first, or remove the member from the set. -->

---

## Modify: fix it instead of refusing it

```json
"then": {
  "effect": "modify",
  "details": {
    "roleDefinitionIds": ["/providers/Microsoft.Authorization/roleDefinitions/b24988ac-6180-42a0-ab88-20f7382dd24c"],
    "operations": [{ "operation": "addOrReplace",
                     "field": "tags['managedBy']", "value": "policy" }]
  }
}
```

- Runs on **new** writes, adding or removing tags for you
- `addOrReplace` overwrites a wrong value; `add` leaves an existing one alone
- Needs an assignment **identity** (`identity { type = "SystemAssigned" }`) and a `location`
- The role id is required but not checked in Dojo Cloud

<!-- About 2 minutes. Lab 7 is the longest lab (30 min) because it has a slow apply and the tofu-versus-policy fight. The rule uses Indexed mode, so the resource group isn't tagged but container groups are. -->

---

## Remediation and the tofu fight

- `modify` does **not** touch resources that already exist
- A **remediation task** applies it to them: `azurerm_resource_group_policy_remediation`
- Policy adds a tag, then OpenTofu sees drift from your code and removes it
- Fix: tell tofu to ignore what policy owns

```hcl
lifecycle {
  ignore_changes = [tags["managedBy"]]
}
```

<!-- About 2 minutes. Real-world gotcha: two controllers fighting over one field. In Lab 7 they create a second container group, watch policy tag it, then watch the next plan try to strip the tag. The cheat sheet lists this under common errors. -->

---

## Why policy applies are slow

- Creating a definition or assignment takes **about 100 s**; destroying an assignment too
- The provider waits for the cloud's **eventual consistency**: the control plane has accepted the rule, but not every region's evaluator has caught up
- The waits run in parallel: one apply with several policies is about **3.5 min**
- Sets, exemptions and remediations are instant
- Never chain assignments with `depends_on`: it turns parallel waits into serial ones

> Plan the apply, start it, and read the next section while you wait.

<!-- About 2 minutes. Tell them up front so nobody cancels a "stuck" apply. Every lab with an apply (3 to 8) has a "read while it runs" section. If they cancel mid-apply they can leave state locked, which costs far more time than the wait. -->

---

<!-- _class: section-title -->

# Part 5

## Shift left

<!-- Labs 9 and 10. Different tools, same idea. -->

---

## Catch it before the cloud does

- Cloud policy answers at **apply** time: late, slow, after the PR merged
- Rego checks the **plan JSON** in the pull request, in seconds
- The same rule, in two places: Rego for fast feedback, cloud policy as the backstop

```bash
tofu plan -out=plan.out
tofu show -json plan.out > plan.json
conftest test --policy policy/rego plan.json
```

<!-- About 2 minutes. Shift left means earlier in the pipeline. OPA is the engine and Rego is its language. conftest is the small command that runs Rego against a file such as a plan. Plans can contain secrets, so plan.out and plan.json are in .gitignore. -->

---

## What is in a plan

```text
resource_changes[]
  address            azurerm_container_group.app
  type               azurerm_container_group
  change.actions     ["create"]   (or update, delete, no-op)
  change.after       the resource as it will be
```

- `address` names the resource, `actions` says what will happen
- `change.after` is the resource **once applied**: that is what a rule checks
- Rego walks this structure. It never talks to the cloud

<!-- About 1 minute. Lab 9 has them print the plan and read it. A good question: "Which actions will the existing app show if nothing changed?" The answer is no-op. A rule that ignores actions will complain about things that are not being touched. -->

---

## The same rule in Rego

```rego
package main

deny contains msg if {
  some rc in input.resource_changes
  rc.type == "azurerm_container_group"
  not rc.change.after.tags.costCenter
  msg := sprintf("%s: missing costCenter tag", [rc.address])
}
```

- `deny contains msg if` builds a set of messages; empty set = pass
- Every line in the body must be true for the rule to fire
- `conftest` fails the build when `deny` is not empty

<!-- About 2 minutes. Compare line by line with the JSON rule. A second rule with the same name is an OR, which people find surprising. The repo's own regions.rego checks create and update actions only, so a delete of a bad resource isn't flagged. -->

---

## Testing policies

```rego
package main

test_missing_tag_denied if {
  count(deny) == 1 with input as {"resource_changes": [{
    "address": "x", "type": "azurerm_container_group",
    "change": {"after": {"tags": {}}}}]}
}
```

```bash
opa test policy/rego --ignore fixtures -v
```

- A rule has two silent ways to be wrong: too loose, or too strict
- Cover the pass **and** the fail case. A rule with no tests is a guess

<!-- About 2 minutes. Lab 10 has a planted bug they have to find with a failing test. Always pass --ignore fixtures: the fixtures folder holds sample plans as JSON and OPA tries to load them as data, which gives a merge error. It is the most common stumble in the lab. -->

---

<!-- _class: section-title -->

# Part 6

## The pipeline and drift

<!-- Labs 11 and 12, then the capstone. -->

---

## The pipeline

| Event | Workflow | Does |
| --- | --- | --- |
| Pull request | `pr.yml` | plan, `conftest`, `opa test` |
| Merge to `main` | `main.yml` | apply `policy/cloud`, then `infra` |
| Manual, and every push to `main` | `drift.yml` | compare reality with git, fail on **DRIFT** |

- Nobody applies policy from a laptop: **git is the change record**
- A broken rule fails on the PR, long before it reaches the cloud

<!-- About 2 minutes. Policy applies first so new guardrails are in place before infra. pr.yml runs conftest against the plan for both infra and policy/cloud. Branch protection on main requires the Policy check, which is what makes it a gate. In the workshop you can still push to main directly, and an admin can change the rule. Say that honestly. -->

---

## A pull request that can't merge a violation

- Break the rule on a branch, open a pull request, and the **Policy check** goes red
- Fix it on the same branch, push, and it goes green
- Merge, and `main.yml` applies it. About 3.5 minutes if a policy is changing
- The terminal and the pipeline share **one state**, so they can't step on each other

> A check you can walk around is a habit, not a control.

<!-- About 2 minutes. This is Lab 11 and it is the payoff of the whole workshop. Remind them that the pipeline lock waits up to 60 seconds, so do not run apply in the terminal while the pipeline is applying. -->

---

## Drift: when the cloud stops matching git

<div class="mermaid">
flowchart LR
  g["git main<br/>intended policy"] --> p["tofu plan"]
  c["Dojo Cloud<br/>actual policy"] --> p
  p -->|"same"| ok["Green"]
  p -->|"different"| d["Run fails: DRIFT"]
  d --> w["Re-run main.yml<br/>git wins"]
  d --> pr["or change git<br/>in a pull request"]
</div>

- Someone sets an assignment to DoNotEnforce in the portal "just for a minute". Nothing in git says so
- `drift.yml` plans against reality and fails loudly when they differ

<!-- About 2 minutes. Lab 12 does exactly this at 2 a.m., in the portal, and then lets the detector find it. Drift is not always a mistake: sometimes the emergency change was right. Then change git. What is never okay is the cloud quietly differing from git. -->

---

## Policy that can be changed by hand is a suggestion

- A disabled guardrail breaks nothing. It only lets bad things through, silently
- The compliance dashboard you would check is the very thing that was changed
- **Detective** control: `drift.yml` finds the change
- **Corrective** control: re-apply from git, or change git on purpose
- The bad resource created while enforcement was off is still there until someone fixes it

<!-- About 2 minutes. Make the point about the dashboard: if you look for a missing guardrail on the page that was edited, you see what was edited. The capstone puts all of this together on a new rule with no steps given. -->

---

## Recap

- A **definition** is a rule; an **assignment** at a **scope** turns it on
- Roll out with **audit**, read **compliance**, then **deny**
- **Parameters** and **sets** make rules reusable; **modify** plus **remediation** fixes instead of refusing
- **Exemptions** are reviewed, expiring exceptions
- Rego on the plan JSON shifts the check **left**, and `opa test` keeps it honest
- The pipeline applies policy; **drift** detection keeps git in charge

<!-- About 1 minute. Skip it if the room is restless. The lab map is next. -->

---

## The lab map

| Labs | You will |
| --- | --- |
| 0-2 | Set up, meet a denial, read a rule |
| 3-4 | First policy as code, audit and compliance |
| 5-6 | Parameters, DoNotEnforce, policy sets |
| 7-8 | Modify, remediation, exemptions |
| 9-10 | Rego on the plan, testing policies |
| 11-12 | The PR pipeline, drift |
| Capstone | One new rule end to end |

Applies take ~3.5 min. Start them, then read on.

<!-- About 1 minute. Send them to ~/lab/README.md. Labs 5 and 8, and the capstone, have a bonus challenge if the class has achievements on. If someone falls behind, dojo prep N brings them to the start of lab N. -->

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
  // Draw in a scratch element on <body> (see dojo-introduction): Marp scales the slide, which would shrink the boxes.
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
