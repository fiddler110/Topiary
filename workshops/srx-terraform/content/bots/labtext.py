#!/usr/bin/env python3
"""labtext.py: turn a lab page into the steps a student performs, so the demo bot runs the lab TEXT.

  labtext.py steps LAB.md OUTDIR   write OUTDIR/NN.sh per step and OUTDIR/index.tsv (NN, kind, label)
  labtext.py file  LAB.md NAME     write the page's `hcl` block headed `# NAME` into NAME (what a student pastes)

Every ```hcl block headed `# path.tf` becomes a paste into that file (`# path.tf (add)` appends) and every
```sh block becomes the commands as written. A step is changed only where a person would answer a prompt or
look something up, never to make a broken lab pass:

  - the lab's claim-code placeholders (SRX300XXXXXXXXX ...) and `<mac of ...>` become this bot's delivery;
  - `terraform apply` gets -auto-approve and `init -migrate-state` gets -force-copy (a student types `yes`);
  - `--netrc` points at the bot's token file;
  - the page's held `terraform apply -replace=...` (a student's first pane, left at its question) runs in the
    background for 20 s with no answer, and the plan after it must FAIL with the lock error, as the page says;
  - a `merge` step is put before the `git checkout main` that follows a pushed branch: the page says "open a
    pull request, review, merge in Forgejo", which is not a code block, so the bot opens (if the page did not)
    and merges its own pull request through the API.

Anything the page shows that no rule covers is run as written; an anchor that is missing exits non-zero.
"""
import os
import re
import subprocess
import sys

FENCE = re.compile(r"^```(\w*)[^\n]*\n(.*?)^```[ \t]*$", re.S | re.M)
HEAD = re.compile(r"^# (\S+\.(?:tf|tfvars))( \(add\))?\s*$")
# Blocks the bot cannot run as a student does, with the reason that is logged.
SKIP = {
    ("lab0.md", "/forks"): "the engine already forked and cloned for this bot (FORGEJO_FORK_WORKFLOW) before step 1",
}


def blocks(path):
    text = open(path, encoding="utf-8").read()
    return [(m.group(1), m.group(2)) for m in FENCE.finditer(text) if m.group(1) in ("sh", "hcl")]


def delivery():
    out = subprocess.run(["dojo", "wan", "delivery"], capture_output=True, text=True).stdout.splitlines()[1:]
    rows = [l.split() for l in out if len(l.split()) >= 4]  # model serial mac magic
    by = {}
    for model, _serial, mac, magic in (r[:4] for r in rows):
        by.setdefault(model, []).append((mac, magic))
    return by


def substitutions():
    d = delivery()
    try:
        ott, tor = d["SRX300"][0][1], d["SRX300"][1][1]
        mon, hal = d["SRX345"][0][1], d["SRX345"][1][1]
        dc = d["SRX1500"][0][1]
    except (KeyError, IndexError):
        sys.exit("labtext: the delivery is not readable yet (dojo wan delivery)")
    return [
        ("SRX300XXXXXXXXX", ott), ("SRX300YYYYYYYYY", tor), ("SRX345XXXXXXXXX", mon),
        ("SRX345YYYYYYYYY", hal), ("SRX1500ZZZZZZZZ", dc),
        ("<mac of your first SRX300>", d["SRX300"][0][0]),
        ("<mac of your Toronto gateway>", d["SRX300"][1][0]),
        ("<mac of your SRX1500>", d["SRX1500"][0][0]),
    ]


def apply_subs(s, subs):
    for a, b in subs:
        s = s.replace(a, b)
    return s


def hcl_step(body, subs, lab):
    lines = body.rstrip("\n").split("\n")
    m = HEAD.match(lines[0])
    if m:
        path, add = m.group(1), bool(m.group(2))
        content = "\n".join(lines[1:]) + "\n"
        d = os.path.dirname(path)
        mk = f"mkdir -p {d}\n" if d else ""
        op = ">>" if add else ">"
        return path, f"{mk}cat {op} {path} <<'__LAB__'\n{apply_subs(content, subs)}__LAB__"
    if re.match(r'\s*"[\w-]+" = \{', lines[0]):
        # the one unnamed block: a map entry for `sites` in terraform.tfvars ("paste it inside the closing }")
        entry = apply_subs("\n".join(lines) + "\n", subs)
        py = ("python3 - <<'__PY__'\n"
              "p = 'terraform.tfvars'\n"
              "s = open(p).read().rstrip()\n"
              "assert s.endswith('}'), 'terraform.tfvars does not end with the sites map'\n"
              "entry = '''" + entry + "'''\n"
              "open(p, 'w').write(s[:-1] + entry + '}\\n')\n"
              "__PY__")
        return "terraform.tfvars (new site entry)", py
    sys.exit(f"labtext: {lab}: an hcl block with no `# file.tf` heading and no map entry: {lines[0]!r}")


def sh_step(body, subs):
    s = apply_subs(body.rstrip("\n"), subs)
    s = re.sub(r"^(terraform apply)(\s*(#.*)?)$", r"\1 -auto-approve\2", s, flags=re.M)
    s = re.sub(r"^(terraform init -migrate-state)\b", r"\1 -force-copy", s, flags=re.M)
    s = s.replace("--netrc ", '--netrc-file "$HOME/.dojo-bot-netrc" ')
    left = re.search(r"(?<!<)<[a-z][a-z0-9 ]+>", s)
    if left:
        sys.exit(f"labtext: a placeholder the bot cannot fill is left in a command: {left.group(0)}")
    return s


def steps(lab_path, outdir):
    lab = os.path.basename(lab_path)
    subs = substitutions()
    os.makedirs(outdir, exist_ok=True)
    index, n, after_console, pushed = [], 0, False, False

    def emit(kind, label, script):
        nonlocal n
        n += 1
        open(os.path.join(outdir, f"{n:02d}.sh"), "w").write(script + "\n")
        index.append(f"{n:02d}\t{kind}\t{label}")

    for lang, body in blocks(lab_path):
        if lang == "hcl":
            label, script = hcl_step(body, subs, lab)
            emit("run", label, script)
            continue
        skip = next((why for (f, anchor), why in SKIP.items() if f == lab and anchor in body), None)
        if skip:
            emit("skip", body.strip().split("\n")[0][:60] + f"  [{skip}]", ":")
            continue
        script = sh_step(body, subs)
        first = body.strip().split("\n")[0][:70]
        if body.strip().startswith("terraform apply -replace="):
            emit("run", first + "  [pane 1 of the lab: held at its question for 20 s in the background]",
                 f"(sleep 20 | {body.strip()} >/dev/null 2>&1 &)\nsleep 5")
            after_console = True
            continue
        if after_console:
            after_console = False
            emit("run", first + "  [must be refused by the lock]",
                 f"out=$({script} 2>&1); rc=$?\necho \"$out\" | head -6\nsleep 18\n"
                 "[ $rc -ne 0 ] && echo \"$out\" | grep -qi 'acquiring the state lock'")
            continue
        if pushed and body.strip().startswith("git checkout main"):
            pushed = False
            emit("merge", "open, review and merge the pull request (prose on the page: Forgejo's Merge button)", ":")
        emit("run", first, script)
        if "git push -u origin" in body:
            pushed = True
    open(os.path.join(outdir, "index.tsv"), "w").write("\n".join(index) + "\n")


def file_cmd(lab_path, name):
    subs = substitutions()
    for lang, body in blocks(lab_path):
        if lang == "hcl":
            m = HEAD.match(body.split("\n", 1)[0])
            if m and m.group(1) == name:
                label, script = hcl_step(body, subs, os.path.basename(lab_path))
                subprocess.run(["bash", "-c", script], check=True)
                return
    sys.exit(f"labtext: no hcl block headed `# {name}` in {lab_path}")


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "steps":
        steps(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 4 and sys.argv[1] == "file":
        file_cmd(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
