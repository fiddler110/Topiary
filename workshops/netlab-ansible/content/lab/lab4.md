# Lab 4: Templates, handlers and validate

Harden `sshd` safely: `template` with `validate:` so a typo cannot lock you out.

**Core path.** About 20 min.

The full instructions are the README that is already in your home folder. Read it, then work in three steps, the same in every lab:
by hand on branch **m**, with a playbook on branch **a**, then prove both.

```sh
cd ~/netlab
cat labs/4-templates-validate/README.md
```

You can also open `~/netlab/labs/4-templates-validate/README.md` in VS Code. Your pod number is in your login name (`student07` is pod 07); the
README already has it filled in.

## Check your work

```sh
cd ~/netlab
dojo netlab check 4
```

Each line says `PASS` or `FAIL` with the reason. Fix what failed and run it again (the checker allows about six runs a minute).

## If you are stuck

| You see | Cause and fix |
| ------- | ------------- |
| `ansible all -m ping` shows `UNREACHABLE` | The pod is still starting, or you changed `sshd` badly (lab 4). Wait a minute, then `ansible-playbook reset_fw.yml -e branch=a` |
| Everything on branch a is blocked after a mistake | `ansible-playbook reset_fw.yml -e branch=a` returns the firewall and web node to the baseline |
| `dojo netlab check` says the checker said no | Too many runs in a minute, or the pod is not up yet: wait and try again |
| `compare.yml` shows a difference | Branch m and branch a do not match yet; the output says which rule or setting differs |
