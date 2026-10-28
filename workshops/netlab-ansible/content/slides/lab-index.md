---
marp: true
theme: default
paginate: false
size: 16:9
html: true
style: |
  @import url('assets/themes/labs.css');
footer: '[&larr; Hub](index.md)'
---

<!-- _class: lead lab-index -->

# Labs

<p class="nav">Everything for this workshop's labs in one place. Work in `~/netlab` in your terminal; the labs are read here.</p>

<div class="cards">
<div>
<h3><a href="assets/lab-reader.html?file=README.md.txt">Lab overview &rarr;</a></h3>
<p>Your pod, the two branches, the core path and the stretch labs.</p>
</div>
<div>
<h3><a href="cheat-sheet.md">Cheat sheet &rarr;</a></h3>
<p>The Ansible and netlab commands you will use.</p>
</div>
</div>

<p class="setup-label">Your pod is ready when this prints green for every node:</p>

```sh
cd ~/netlab
ansible-playbook verify_topology.yml
```

<ul class="lab-links">
<li><a href="assets/lab-reader.html?file=lab0.md.txt">Lab 0</a><span class="topic">Orientation: inventory, ad-hoc commands, facts</span></li>
<li><a href="assets/lab-reader.html?file=lab1.md.txt">Lab 1</a><span class="topic">A first playbook: the web page</span></li>
<li><a href="assets/lab-reader.html?file=lab2.md.txt">Lab 2</a><span class="topic">Variables, loops, conditionals: open HTTP and HTTPS</span></li>
<li><a href="assets/lab-reader.html?file=lab3.md.txt">Lab 3</a><span class="topic">Idempotency and check mode: HTTPS</span></li>
<li><a href="assets/lab-reader.html?file=lab4.md.txt">Lab 4</a><span class="topic">Templates, handlers, validate: harden SSH</span></li>
<li><a href="assets/lab-reader.html?file=lab5.md.txt">Lab 5</a><span class="topic">Secrets with Vault (stretch)</span></li>
<li><a href="assets/lab-reader.html?file=lab6.md.txt">Lab 6</a><span class="topic">Errors, rollback and tests: lock it down</span></li>
<li><a href="assets/lab-reader.html?file=lab7.md.txt">Lab 7</a><span class="topic">Roles and structure (stretch)</span></li>
<li><a href="assets/lab-reader.html?file=lab8.md.txt">Lab 8</a><span class="topic">Capstone: from clean to done</span></li>
<li><a href="assets/lab-reader.html?file=labS1.md.txt">Lab S1</a><span class="topic">VLANs and access ports, build it yourself (stretch)</span></li>
<li><a href="assets/lab-reader.html?file=labS2.md.txt">Lab S2</a><span class="topic">Trunk and router-on-a-stick (stretch)</span></li>
<li><a href="assets/lab-reader.html?file=labS3.md.txt">Lab S3</a><span class="topic">Segmentation policy (stretch)</span></li>
</ul>
