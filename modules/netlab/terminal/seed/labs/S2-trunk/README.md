# Lab A3: Trunk and router-on-a-stick, as code

Add the trunk to the firewall and route between the VLANs, guarded by an assert. `site.yml` here starts empty.

The full walkthrough, with every command explained, is the lab page **Lab A3** in the lab reader (the lab index
in your portal). This folder is where you do the work.

- You fill in: `labs/S2-trunk/site.yml`
- Work from `~/netlab`, on branch **a**; the by-hand twin is Lab M3 on branch **m** (`*-a-@POD@`).
- Check your work: `dojo netlab check A3`
- Stuck or wrecked the firewall or web node? `ansible-playbook reset_fw.yml -e branch=a`
