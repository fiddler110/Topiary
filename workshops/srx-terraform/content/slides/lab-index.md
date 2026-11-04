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

<p class="nav">Everything for this workshop's labs, in one place. Pick a lab below, or start with the overview.</p>

<div class="cards">
<div>
<h3><a href="labs.md">Lab overview &rarr;</a></h3>
<p>Timing, what to expect, and what each lab covers.</p>
</div>
<div>
<h3><a href="assets/lab-reader.html?file=README.md.txt">Full lab README &rarr;</a></h3>
<p>The complete lab guide, read right here in the browser.</p>
</div>
</div>

<p class="setup-label">Every lab works in your fork of the starter repo (Lab 0). Make it once, or run <code>dojo prep N</code> to catch up to lab N:</p>

```sh
curl --netrc -H "Content-Type: application/json" -d '{}' \
  http://git-server:3000/api/v1/repos/netops/srx-terraform/forks   # signs in with your token
cd ~/lab && git clone http://git-server:3000/$USER/srx-terraform.git
```

<ul class="lab-links">
<li><a href="assets/lab-reader.html?file=lab0.md.txt">Lab 0</a><span class="topic">Tour: fork, portal, init</span></li>
<li><a href="assets/lab-reader.html?file=lab1.md.txt">Lab 1</a><span class="topic">First objects, plan and apply</span></li>
<li><a href="assets/lab-reader.html?file=lab2.md.txt">Lab 2</a><span class="topic">The gateway template</span></li>
<li><a href="assets/lab-reader.html?file=lab3.md.txt">Lab 3</a><span class="topic">Sites and variables</span></li>
<li><a href="assets/lab-reader.html?file=lab4.md.txt">Lab 4</a><span class="topic">Claim and assign</span></li>
<li><a href="assets/lab-reader.html?file=lab5.md.txt">Lab 5</a><span class="topic">Layers: hub profile and override</span></li>
<li><a href="assets/lab-reader.html?file=lab6.md.txt">Lab 6</a><span class="topic">Modules, for_each, moved</span></li>
<li><a href="assets/lab-reader.html?file=lab7.md.txt">Lab 7</a><span class="topic">Shared state and a reviewed pull request</span></li>
<li><a href="assets/lab-reader.html?file=lab8.md.txt">Lab 8</a><span class="topic">Drift and import</span></li>
<li><a href="assets/lab-reader.html?file=lab9.md.txt">Lab 9</a><span class="topic">Capstone: a new branch from a ticket</span></li>
<li><a href="assets/lab-reader.html?file=cheat-sheet.md.txt">Cheat sheet</a><span class="topic">Every command, plain text</span></li>
</ul>
