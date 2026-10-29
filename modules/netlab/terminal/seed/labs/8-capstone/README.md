# Lab A9: Capstone: from clean to done

Reset branch a, rebuild it with one `site.yml` that imports your lab playbooks, run it twice and compare with branch m.

The full walkthrough, with every command explained, is the lab page **Lab A9** in the lab reader (the lab index
in your portal). This folder is where you do the work.

- You fill in: `labs/8-capstone/site.yml`
- Work from `~/netlab`, on branch **a** (`*-a-@POD@`).
- Check your work: `dojo netlab check A9`
- Stuck or wrecked the firewall or web node? `ansible-playbook reset_fw.yml -e branch=a`
