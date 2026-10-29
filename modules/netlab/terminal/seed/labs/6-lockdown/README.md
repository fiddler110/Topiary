# Lab A8: Lock it down, test it, roll it back

Apply the segmentation policy with `block`/`rescue`/`always`, test it from the pc, and roll back on failure.

The full walkthrough, with every command explained, is the lab page **Lab A8** in the lab reader (the lab index
in your portal). This folder is where you do the work.

- You fill in: `labs/6-lockdown/site.yml`
- Work from `~/netlab`, on branch **a** (`*-a-@POD@`).
- Check your work: `dojo netlab check A8`
- Stuck or wrecked the firewall or web node? `ansible-playbook reset_fw.yml -e branch=a`
