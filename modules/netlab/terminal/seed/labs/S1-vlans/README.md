# Lab A2: VLANs and access ports, as code

Describe the VLANs as data and build the switch with a template, safely and repeatably. `site.yml` here starts empty.

The full walkthrough, with every command explained, is the lab page **Lab A2** in the lab reader (the lab index
in your portal). This folder is where you do the work.

- You fill in: `labs/S1-vlans/site.yml`, `vlans.yml`, `switch.sh.j2`
- Work from `~/netlab`, on branch **a**; the by-hand twin is Lab M2 on branch **m** (`*-a-@POD@`).
- Check your work: `dojo netlab check A2`
- Stuck or wrecked the firewall or web node? `ansible-playbook reset_fw.yml -e branch=a`
