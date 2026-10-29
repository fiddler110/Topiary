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
<p>Your pod, the two branches, the labs in order.</p>
</div>
<div>
<h3><a href="cheat-sheet.md">Cheat sheet &rarr;</a></h3>
<p>The Ansible and netlab commands you will use.</p>
</div>
</div>

<p class="setup-label">Your pod is ready when this prints green for every node:</p>

```sh
cd ~/netlab && ansible-playbook verify_topology.yml
```

<div class="parts">
<div>
<p class="setup-label">Part 1: by hand, on branch m</p>

<ul class="lab-links">
<li><a href="assets/lab-reader.html?file=labM1.md.txt">Lab M1</a><span class="topic">Look around the pod</span></li>
<li><a href="assets/lab-reader.html?file=labM2.md.txt">Lab M2</a><span class="topic">VLANs and access ports</span></li>
<li><a href="assets/lab-reader.html?file=labM3.md.txt">Lab M3</a><span class="topic">Trunk and router-on-a-stick</span></li>
<li><a href="assets/lab-reader.html?file=labM4.md.txt">Lab M4</a><span class="topic">Serve a web page</span></li>
<li><a href="assets/lab-reader.html?file=labM5.md.txt">Lab M5</a><span class="topic">Open HTTP and HTTPS</span></li>
<li><a href="assets/lab-reader.html?file=labM6.md.txt">Lab M6</a><span class="topic">HTTPS with a self-signed certificate</span></li>
<li><a href="assets/lab-reader.html?file=labM7.md.txt">Lab M7</a><span class="topic">Harden SSH</span></li>
<li><a href="assets/lab-reader.html?file=labM8.md.txt">Lab M8</a><span class="topic">Lock the server down (segmentation policy)</span></li>
<li><a href="assets/lab-reader.html?file=labM9.md.txt">Lab M9</a><span class="topic">Rebuild from clean</span></li>
</ul>
</div>
<div>
<p class="setup-label">Part 2: as playbooks, on branch a</p>

<ul class="lab-links">
<li><a href="assets/lab-reader.html?file=labA1.md.txt">Lab A1</a><span class="topic">Orientation: inventory, ad-hoc commands, facts</span></li>
<li><a href="assets/lab-reader.html?file=labA2.md.txt">Lab A2</a><span class="topic">VLANs and access ports, build it yourself</span></li>
<li><a href="assets/lab-reader.html?file=labA3.md.txt">Lab A3</a><span class="topic">Trunk and router-on-a-stick</span></li>
<li><a href="assets/lab-reader.html?file=labA4.md.txt">Lab A4</a><span class="topic">A first playbook: the web page</span></li>
<li><a href="assets/lab-reader.html?file=labA5.md.txt">Lab A5</a><span class="topic">Variables, loops, conditionals</span></li>
<li><a href="assets/lab-reader.html?file=labA6.md.txt">Lab A6</a><span class="topic">Idempotency and check mode: HTTPS</span></li>
<li><a href="assets/lab-reader.html?file=labA7.md.txt">Lab A7</a><span class="topic">Templates, handlers, validate: harden SSH</span></li>
<li><a href="assets/lab-reader.html?file=labA8.md.txt">Lab A8</a><span class="topic">Errors, rollback and tests: lock it down</span></li>
<li><a href="assets/lab-reader.html?file=labA9.md.txt">Lab A9</a><span class="topic">Capstone: from clean to done</span></li>
<li><a href="assets/lab-reader.html?file=labA10.md.txt">Lab A10</a><span class="topic">Secrets with OpenBao (stretch)</span></li>
<li><a href="assets/lab-reader.html?file=labA11.md.txt">Lab A11</a><span class="topic">Roles and structure (stretch)</span></li>
</ul>
</div>
</div>
