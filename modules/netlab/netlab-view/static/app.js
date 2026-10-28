// Netlab view: polls api/pod/<n> and draws the pod. Node output is student-influenced (firewall rules, addresses),
// so every string goes in through textContent only.
"use strict";

(function () {
  const POLL_MS = 5000;
  const $ = (id) => document.getElementById(id);
  let pod = null;
  let timer = null;

  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }

  function tag(text, good) {
    return el("span", "tag " + (good ? "ok" : "bad"), text);
  }

  function list(title, items) {
    const box = el("div");
    box.append(el("div", "lbl", title));
    const ul = el("ul");
    for (const t of items) ul.append(el("li", "", t));
    if (!items.length) ul.append(el("li", "muted", "none"));
    box.append(ul);
    return box;
  }

  function vlanText(v) {
    return v.id + (v.pvid ? " pvid" : "") + (v.untagged ? " untagged" : " tagged");
  }

  function node(n) {
    const box = el("div", "node" + (n.up ? "" : " down"));
    const h = el("h3");
    h.append(el("span", "", n.name), tag(n.up ? "up" : "down", n.up));
    box.append(h);
    if (!n.up) return box;
    box.append(list("Interfaces", n.ifaces.map((i) => i.name + " " + i.state + "  " + (i.addrs.join(", ") || "no address"))));
    if (n.vlans) box.append(list("VLANs per port", n.vlans.map((p) => p.port + ": " + (p.vlans.map(vlanText).join(", ") || "none"))));
    if (n.rules) box.append(list("Firewall LAB rules (" + n.rules.length + ")", n.rules));
    return box;
  }

  function branch(b) {
    const sec = el("section", "branch");
    sec.append(el("h2", "", "Branch " + b.branch.toUpperCase() + " (" + b.label.toLowerCase() + ")"));
    const chain = el("div", "chain");
    b.nodes.forEach((n, i) => {
      if (i) chain.append(el("span", "arrow", "→"));
      chain.append(tag(n.role, n.up));
    });
    sec.append(chain);
    if (b.probes) {
      const p = el("div", "probes");
      p.append(el("span", "muted", "From pc to web:"));
      for (const [k, v] of Object.entries(b.probes)) p.append(tag(k + " " + v, v === "ok" || /^[23]/.test(v)));
      sec.append(p);
    }
    const grid = el("div", "nodes");
    for (const n of b.nodes) grid.append(node(n));
    sec.append(grid);
    return sec;
  }

  function checks(c) {
    const sec = el("section", "branch");
    sec.append(el("h2", "", "Latest check results"));
    const labs = Object.keys(c || {}).sort();
    if (!labs.length) {
      sec.append(el("p", "muted", "No checks yet. Run dojo netlab check <lab> in the terminal."));
      return sec;
    }
    const t = el("table");
    const head = el("tr");
    for (const h of ["Lab", "Result", "Passed", "When"]) head.append(el("th", "", h));
    t.append(head);
    for (const lab of labs) {
      const r = c[lab];
      const row = el("tr");
      row.append(el("td", "", lab));
      const res = el("td");
      res.append(tag(r.ok ? "pass" : "fail", r.ok));
      row.append(res, el("td", "", r.passed + " / " + r.total), el("td", "", new Date(r.time * 1000).toLocaleTimeString()));
      t.append(row);
    }
    sec.append(t);
    return sec;
  }

  function draw(doc) {
    $("title").textContent = doc.pod === 0 ? "Facilitator pod" : "Pod " + doc.user;
    $("pod").replaceChildren(...doc.branches.map(branch), checks(doc.checks));
    $("status").className = "status";
    $("status").textContent = "Updated " + new Date(doc.updated * 1000).toLocaleTimeString() + ".";
  }

  async function load() {
    try {
      const r = await fetch("api/pod/" + pod, { cache: "no-store" });
      if (!r.ok) throw new Error((await r.json()).error || r.status);
      draw(await r.json());
    } catch (e) {
      $("status").className = "status err";
      $("status").textContent = "Could not read the pod: " + e.message;
    }
    timer = setTimeout(load, POLL_MS);
  }

  async function start() {
    const me = await (await fetch("api/me", { cache: "no-store" })).json();
    if (me.error) {
      $("status").className = "status err";
      $("status").textContent = me.error;
      return;
    }
    pod = me.pods[0];
    if (me.facilitator) {
      const sel = $("pods");
      for (const p of me.pods) sel.append(new Option(p === 0 ? "facilitator (00)" : "student " + String(p).padStart(2, "0"), p));
      sel.addEventListener("change", () => { pod = Number(sel.value); clearTimeout(timer); load(); });
      $("pick").hidden = false;
    }
    load();
  }

  start();
})();
