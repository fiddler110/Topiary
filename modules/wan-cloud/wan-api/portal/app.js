/*
 * Dojo WAN portal - vanilla ES2020, no build step, no libraries, no external assets.
 * Served by wan-api at /wan/ under a strict CSP (script-src 'self'; style-src 'self').
 *
 * SECURITY RULE: every value from the API (names, vars, serials, event paths, actors...)
 * is typed by students and shown to other students. Render it ONLY with textContent / text
 * nodes via h() below. Never innerHTML, outerHTML, insertAdjacentHTML, eval, inline handlers.
 * CSS classes come from fixed tables, never from data. URLs are relative.
 *
 * Routes (hash): #/ #/sites #/gateways #/gateways/<id> #/templates #/networks #/services
 * #/policies #/delivery #/events #/progress (facilitator; the /admin tab loads this one).
 * Polling: one fetch every 5 s, for the current view only, paused while the tab is hidden.
 */
(function () {
  'use strict';

  const POLL_MS = 5000;
  const TIMEOUT_MS = 10000;
  const ATTR_OK = /^(?:class|id|type|role|title|for|name|value|colspan|scope|tabindex|href|disabled|hidden|aria-[a-z]+|data-[a-z-]+)$/;
  const HASH_RE = /^#\/[\w\/%.~!*'()-]*$/;
  const ID_RE = /^[\w.-]{1,80}$/;

  const S = { me: null, org: null, store: null, config: null, fetchedAt: 0, error: null, open: new Set(),
    driftMsg: {} };   // drift results by panel key ('all' or an org id): kept here so a re-render doesn't wipe them
  let routeToken = 0, pollTimer = null, inflight = null, progressRows = [];

  const $ = (id) => document.getElementById(id);
  const view = $('view');

  // ---------------------------------------------------------------- safe DOM
  function h(tag, attrs, ...kids) {
    const n = document.createElement(tag);
    if (attrs) {
      for (const k of Object.keys(attrs)) {
        const v = attrs[k];
        if (v === false || v == null) continue;
        if (k === 'on') { for (const ev of Object.keys(v)) n.addEventListener(ev, v[ev]); continue; }
        if (!ATTR_OK.test(k)) throw new Error('attribute not allowed: ' + k);
        if (k === 'href' && !HASH_RE.test(v)) continue;
        n.setAttribute(k, v === true ? '' : String(v));
      }
    }
    for (const c of kids.flat(Infinity)) {
      if (c == null || c === false) continue;
      n.append(c instanceof Node ? c : document.createTextNode(String(c)));
    }
    return n;
  }
  const dash = (v) => (v == null || v === '' ? '—' : String(v));
  const obj = (v) => (v && typeof v === 'object' && !Array.isArray(v) ? v : {});
  const arr = (v) => (Array.isArray(v) ? v : []);
  const vals = (m) => Object.keys(obj(m)).sort().map((k) => Object.assign({ _id: k }, obj(m[k])));
  const byName = (a, b) => String(a.name || a._id).localeCompare(String(b.name || b._id));
  function when(ts) {
    const n = Number(ts);
    if (!n) return '—';
    return new Date(n > 1e12 ? n : n * 1000).toLocaleString();
  }

  function table(cols, rows, opts) {
    opts = opts || {};
    if (!rows.length) return h('div', { class: 'table-wrap' }, h('p', { class: 'empty' }, opts.empty || 'Nothing here yet'));
    return h('div', { class: 'table-wrap' }, h('table', null,
      h('thead', null, h('tr', null, cols.map((c) => h('th', { scope: 'col' }, c[0])))),
      h('tbody', null, rows.map((r) => {
        const tr = h('tr', { class: opts.rowClass ? opts.rowClass(r) : false },
          cols.map((c) => h('td', null, c[1](r))));
        if (opts.onRow) {
          tr.classList.add('row-link');
          tr.addEventListener('click', () => opts.onRow(r));
        }
        return tr;
      }))));
  }
  const pill = (text, kind) => h('span', { class: 'pill ' + ({ ok: 'pill-ok', warn: 'pill-warn', err: 'pill-err' }[kind] || '') }, text);
  const pageHead = (title, sub) => h('div', { class: 'page-head' }, h('h1', null, title), sub ? h('span', { class: 'sub' }, sub) : null);
  const jsonPre = (v) => h('pre', { class: 'json' }, JSON.stringify(v, null, 2));

  // ---------------------------------------------------------------- network
  async function api(path, opts) {
    const ctl = new AbortController();
    inflight = ctl;
    const t = setTimeout(() => ctl.abort(), TIMEOUT_MS);
    try {
      const r = await fetch(path, Object.assign({ credentials: 'same-origin', cache: 'no-store', signal: ctl.signal }, opts));
      if (!r.ok) {
        let detail = '';
        if (r.status === 409) { try { detail = String((await r.json()).detail || ''); } catch (_) { /* no JSON body */ } }
        const e = new Error(r.status === 401 || r.status === 403
          ? 'Not signed in or not allowed (' + r.status + '). Open the portal through the workshop gateway.'
          : detail || 'Server answered ' + r.status);
        throw e;
      }
      return (opts && opts.text) || (r.headers.get('content-type') || '').indexOf('json') < 0 ? await r.text() : await r.json();
    } finally { clearTimeout(t); }
  }
  const orgPath = (o) => 'api/orgs/' + encodeURIComponent(o);

  function setBanner(msg) {
    $('banner').hidden = !msg;
    $('banner-msg').textContent = msg || '';
  }

  // ---------------------------------------------------------------- routing
  const NAV = ['home', 'sites', 'gateways', 'templates', 'networks', 'services', 'policies', 'delivery', 'events', 'progress'];
  function parseRoute() {
    const parts = (location.hash.replace(/^#\/?/, '') || '').split('/').map((p) => { try { return decodeURIComponent(p); } catch (e) { return ''; } });
    const name = parts[0] || 'home';
    return { name: NAV.includes(name) ? name : 'home', arg: parts[1] || null };
  }

  async function route() {
    const token = ++routeToken;
    clearTimeout(pollTimer);
    const r = parseRoute();
    for (const a of document.querySelectorAll('[data-nav]')) {
      if (a.dataset.nav === r.name || (r.name === 'home' && a.dataset.nav === 'home')) a.setAttribute('aria-current', 'page');
      else a.removeAttribute('aria-current');
    }
    $('main').focus({ preventScroll: true });
    await refresh(token);
  }

  async function refresh(token) {
    token = token || routeToken;
    if (inflight) inflight.abort();
    const r = parseRoute();
    try {
      if (!S.me) await loadMe();
      if (r.name === 'progress') {
        if (!S.me.facilitator) throw new Error('Class progress is for the facilitator.');
        const rows = await Promise.all(S.me.orgs.map(async (o) => {
          try { return { o, store: await api(orgPath(o.id)) }; } catch (e) { return { o, error: true }; }
        }));
        if (token !== routeToken) return;
        progressRows = rows;
      } else {
        if (!S.org) throw new Error('No organisation is available for this account yet.');
        const store = await api(orgPath(S.org));
        let cfg = null;
        if (r.name === 'gateways' && r.arg && ID_RE.test(r.arg)) {
          try { cfg = await api(orgPath(S.org) + '/devices/' + encodeURIComponent(r.arg) + '/config', { text: true }); }
          catch (e) { cfg = '# could not load config: ' + e.message; }
        }
        if (token !== routeToken) return;
        S.store = store; S.config = cfg;
      }
      S.error = null;
      setBanner('');
      S.fetchedAt = Date.now();
      $('updated').textContent = 'Last updated: ' + new Date(S.fetchedAt).toLocaleTimeString();
      draw(r);
    } catch (e) {
      if (token !== routeToken || e.name === 'AbortError' && token !== routeToken) return;
      setBanner(e.name === 'AbortError' ? 'The portal did not answer in time.' : e.message);
    }
    if (token === routeToken) schedule(token);
  }

  function schedule(token) {
    clearTimeout(pollTimer);
    pollTimer = setTimeout(() => {
      if (token !== routeToken) return;
      if (document.hidden) { schedule(token); return; }
      refresh(token);
    }, POLL_MS);
  }

  async function loadMe() {
    const me = await api('api/me');
    S.me = { user: String(me.user || ''), facilitator: !!me.facilitator, orgs: arr(me.orgs) };
    const saved = S.org && S.me.orgs.some((o) => o.id === S.org) ? S.org : null;
    S.org = saved || (S.me.orgs[0] && S.me.orgs[0].id) || null;
    $('meta-facilitator').hidden = !S.me.facilitator;
    $('nav-progress').hidden = !S.me.facilitator;
    $('org-pick-wrap').hidden = !S.me.facilitator;
    const pick = $('org-pick');
    pick.replaceChildren(...S.me.orgs.map((o) => h('option', { value: o.id }, (o.user || o.name || o.id))));
    if (S.org) pick.value = S.org;
    const cur = S.me.orgs.find((o) => o.id === S.org);
    $('meta-org').textContent = cur ? (cur.name || cur.id) + ' (' + S.me.user + ')' : S.me.user;
  }

  function orgUser() {
    const o = S.me && S.me.orgs.find((x) => x.id === S.org);
    return o ? o.user : '';
  }

  // ---------------------------------------------------------------- views
  function draw(r) {
    const fn = VIEWS[r.name] || VIEWS.home;
    view.replaceChildren(fn(r));
  }

  const siteName = (st, id) => { const s = obj(obj(st.sites)[id]); return s.name || (id ? String(id) : null); };

  const VIEWS = {
    home() {
      const st = S.store || {};
      const n = (m) => Object.keys(obj(m)).length;
      const cards = [
        ['Sites', n(st.sites), '#/sites'], ['Gateways', arr(st.inventory).length, '#/gateways'],
        ['Templates', n(st.gatewaytemplates), '#/templates'], ['Profiles', n(st.deviceprofiles), '#/templates'],
        ['Networks', n(st.networks), '#/networks'], ['Services', n(st.services), '#/services'],
        ['Policies', n(st.servicepolicies), '#/policies'], ['Unclaimed', arr(st.delivery).length - arr(st.inventory).length > 0 ? arr(st.delivery).length - arr(st.inventory).length : 0, '#/delivery'],
      ];
      return h('div', null,
        pageHead(String(obj(st.org).name || 'Organisation'), 'Overview'),
        h('div', { class: 'cards' }, cards.map((c) => h('a', { class: 'card', href: c[2] },
          h('div', { class: 'num' }, c[1]), h('div', { class: 'lbl' }, c[0])))),
        S.me.facilitator ? driftPanel() : null,
        h('div', { class: 'panel' }, h('h2', null, 'Latest events'), eventsTable(arr(st.events).slice(-5).reverse())));
    },

    sites() {
      const st = S.store;
      const rows = vals(st.sites).sort(byName);
      return h('div', null, pageHead('Sites', rows.length + ' total'),
        table([
          ['Name', (s) => s.name], ['Address', (s) => dash(s.address)], ['Timezone', (s) => dash(s.timezone)],
          ['Gateway template', (s) => { const t = obj(obj(st.gatewaytemplates)[s.gatewaytemplate_id]); return s.gatewaytemplate_id ? (t.name || 'unknown id ' + s.gatewaytemplate_id) : pill('none', 'warn'); }],
          ['Variables', (s) => { const v = obj(obj(obj(st.site_settings)[s._id]).vars); const k = Object.keys(v).sort();
            return k.length ? h('dl', { class: 'kv' }, k.map((x) => [h('dt', null, x), h('dd', null, h('code', null, String(v[x])))])) : '—'; }],
        ], rows, { empty: 'No sites. Create one with mist_site.' }));
    },

    gateways(r) {
      const st = S.store;
      const inv = arr(st.inventory);
      if (r.arg) return gatewayDetail(st, inv, r.arg);
      const rows = inv.map((d) => obj(d)).sort((a, b) => String(a.serial).localeCompare(String(b.serial)));
      return h('div', null, pageHead('Gateways', rows.length + ' claimed'),
        table([
          ['Name', (d) => dash(obj(obj(st.devices)[d.id]).name)], ['Model', (d) => dash(d.model)], ['Serial', (d) => h('code', null, dash(d.serial))],
          ['MAC', (d) => h('code', null, dash(d.mac))],
          ['Assigned site', (d) => d.site_id ? dash(siteName(st, d.site_id)) : pill('unassigned', 'warn')],
          ['Profile', (d) => d.deviceprofile_id ? dash(obj(obj(st.deviceprofiles)[d.deviceprofile_id]).name || d.deviceprofile_id) : '—'],
        ], rows, { empty: 'No gateways claimed yet. Claim one with mist_org_inventory.',
          onRow: (d) => { location.hash = '#/gateways/' + encodeURIComponent(d.id); } }));
    },

    templates() {
      const st = S.store;
      const sect = (title, m, kind) => h('div', null, h('h2', null, title),
        vals(m).sort(byName).length ? vals(m).sort(byName).map((o) => {
          const key = kind + ':' + o._id;
          const d = h('details', { 'data-key': key }, h('summary', null, String(o.name || o._id)), jsonPre(withoutId(o)));
          if (S.open.has(key)) d.open = true;
          d.addEventListener('toggle', () => { if (d.open) S.open.add(key); else S.open.delete(key); });
          return d;
        }) : h('p', { class: 'empty' }, 'None yet'));
      return h('div', null, pageHead('Templates & profiles', 'read-only; change them with Terraform'),
        sect('Gateway templates', st.gatewaytemplates, 'gt'), sect('Device profiles', st.deviceprofiles, 'dp'));
    },

    networks() {
      const rows = vals(S.store.networks).sort(byName);
      return h('div', null, pageHead('Networks', rows.length + ' total'),
        table([['Name', (n) => n.name], ['Subnet', (n) => h('code', null, dash(n.subnet))], ['VLAN', (n) => dash(n.vlan_id)],
          ['Internet access', (n) => dash(obj(n.internet_access).enabled)]], rows, { empty: 'No networks. Create one with mist_org_network.' }));
    },

    services() {
      const rows = vals(S.store.services).sort(byName);
      return h('div', null, pageHead('Services', rows.length + ' total'),
        table([['Name', (s) => s.name], ['Type', (s) => dash(s.type)],
          ['Addresses', (s) => arr(s.addresses).join(', ') || '—'],
          ['Specs', (s) => arr(s.specs).map((x) => dash(obj(x).protocol) + '/' + dash(obj(x).port_range)).join(', ') || (s.type === 'apps' ? arr(s.apps).join(', ') : '—')],
        ], rows, { empty: 'No services. Create one with mist_org_service.' }));
    },

    policies() {
      const rows = vals(S.store.servicepolicies).sort(byName);
      return h('div', null, pageHead('Service policies', rows.length + ' total'),
        table([['Name', (p) => p.name], ['Action', (p) => pill(dash(p.action), p.action === 'allow' ? 'ok' : p.action === 'deny' ? 'err' : '')],
          ['Tenants (from)', (p) => arr(p.tenants).join(', ') || '—'], ['Services', (p) => arr(p.services).join(', ') || '—']],
          rows, { empty: 'No service policies. Create one with mist_org_servicepolicy.' }));
    },

    delivery() {
      const st = S.store;
      const claimed = new Set(arr(st.inventory).map((d) => obj(d).serial));
      const rows = arr(st.delivery).map((d) => obj(d));
      return h('div', null, pageHead('Delivery', 'packing slip for this org'),
        h('p', null, 'Your hardware order. Claim each gateway in Terraform with its claim code.'),
        table([['Model', (d) => dash(d.model)], ['Serial', (d) => h('code', null, dash(d.serial))], ['MAC', (d) => h('code', null, dash(d.mac))],
          ['Claim code', (d) => h('code', null, dash(d.magic))],
          ['Status', (d) => claimed.has(d.serial) ? pill('claimed', 'ok') : pill('unclaimed', '')]], rows, { empty: 'No delivery for this org.' }));
    },

    events() {
      return h('div', null, pageHead('Events', 'last 200, newest first'),
        h('p', null, 'Rows in colour were made by someone other than this org’s Terraform user: changed outside Terraform.'),
        eventsTable(arr(S.store.events).slice().reverse()));
    },

    progress() {
      const keys = [['sites', 'Sites'], ['networks', 'Networks'], ['services', 'Services'], ['servicepolicies', 'Policies'],
        ['gatewaytemplates', 'Templates'], ['deviceprofiles', 'Profiles'], ['devices', 'Device cfgs']];
      const cols = [['User', (x) => x.o.user || x.o.name || x.o.id]]
        .concat(keys.map((k) => [k[1], (x) => x.error ? '?' : Object.keys(obj(obj(x.store)[k[0]])).length]))
        .concat([['Claimed', (x) => x.error ? '?' : arr(x.store.inventory).length + '/' + (arr(x.store.delivery).length || '?')],
          ['Outside edits', (x) => { if (x.error) return '?'; const u = x.o.user; const c = arr(x.store.events).filter((e) => obj(e).actor !== u).length; return c ? pill(c, 'warn') : '0'; }],
          ['Last event', (x) => { if (x.error) return 'unavailable'; const e = arr(x.store.events); return e.length ? when(obj(e[e.length - 1]).ts) : '—'; }],
          ['', (x) => h('button', { type: 'button', class: 'btn btn-small', on: { click: () => { S.org = x.o.id; $('org-pick').value = S.org; location.hash = '#/'; } } }, 'Open')]]);
      return h('div', null, pageHead('Class progress', progressRows.length + ' orgs'), table(cols, progressRows, { empty: 'No orgs yet.' }), driftAllPanel());
    },
  };

  function withoutId(o) { const c = Object.assign({}, o); delete c._id; return c; }

  function gatewayDetail(st, inv, id) {
    const d = inv.find((x) => obj(x).id === id);
    const back = h('p', null, h('a', { href: '#/gateways' }, '← All gateways'));
    if (!d) return h('div', null, back, h('p', { class: 'empty' }, 'That gateway is not in this org.'));
    const cfg = S.config == null ? 'Loading…' : S.config;
    const msg = h('span', { class: 'msg', role: 'status' });
    const copy = h('button', { type: 'button', class: 'btn btn-small', on: { click: async () => {
      try { await navigator.clipboard.writeText(cfg); msg.textContent = 'Copied'; } catch (e) { msg.textContent = 'Copy not available here; select the text instead'; }
      setTimeout(() => { msg.textContent = ''; }, 3000);
    } } }, 'Copy');
    const dev = obj(obj(st.devices)[id]);
    return h('div', null, back,
      pageHead(dev.name || d.serial || 'Gateway', dash(d.model)),
      h('div', { class: 'panel' }, h('dl', { class: 'kv' },
        h('dt', null, 'Serial'), h('dd', null, h('code', null, dash(d.serial))),
        h('dt', null, 'MAC'), h('dd', null, h('code', null, dash(d.mac))),
        h('dt', null, 'Site'), h('dd', null, dash(siteName(st, d.site_id))),
        h('dt', null, 'Profile'), h('dd', null, dash(obj(obj(st.deviceprofiles)[d.deviceprofile_id]).name)))),
      h('div', { class: 'panel' }, h('div', { class: 'cfg-head' }, h('h2', null, 'Rendered Junos configuration'), msg, copy),
        h('pre', { class: 'cfg', tabindex: 0 }, cfg)));
  }

  function eventsTable(list) {
    const user = orgUser();
    return table([['Time', (e) => when(e.ts)], ['Actor', (e) => dash(e.actor)], ['Action', (e) => dash(e.action)],
      ['Path', (e) => h('code', null, dash(e.path))], ['', (e) => (user && e.actor !== user ? pill('changed outside Terraform', 'warn') : '')]],
      list.map((e) => obj(e)), { empty: 'No events yet.', rowClass: (e) => (user && e.actor !== user ? 'outside' : false) });
  }

  function driftAllPanel() {
    const msg = h('span', { class: 'msg', role: 'status' }, S.driftMsg.all || '');
    const say = (t) => { S.driftMsg.all = t; msg.textContent = t; };
    const btn = h('button', { type: 'button', class: 'btn btn-danger', on: { click: async () => {
      if (!window.confirm('Make drift in every org? Each student org with a network gets its VLAN changed.')) return;
      btn.disabled = true; say('Working…');
      try {
        const r = await api('/wan/api/drift', { method: 'POST', headers: { 'X-Requested-With': 'dojo-admin' } });
        say('Drift made in ' + r.changed + ' of ' + (r.changed + r.skipped) + ' orgs; ' + r.skipped + ' skipped (no network yet).');
        refresh();
      } catch (e) { say('Failed: ' + e.message); }
      btn.disabled = false;
    } } }, 'Make drift in every org');
    return h('div', { class: 'panel' }, h('h2', null, 'Facilitator'),
      h('p', null, 'Make the canned change in every org that has a network, outside Terraform, for Lab 8.'), btn, msg);
  }

  function driftPanel() {
    const key = S.org;
    const msg = h('span', { class: 'msg', role: 'status' }, S.driftMsg[key] || '');
    const say = (t) => { S.driftMsg[key] = t; msg.textContent = t; };
    const btn = h('button', { type: 'button', class: 'btn btn-danger', on: { click: async () => {
      btn.disabled = true; say('Working…');
      try {
        await api(orgPath(key) + '/drift', { method: 'POST', headers: { 'X-Requested-With': 'dojo-admin' }, text: true });
        say('Drift made. Terraform plan in this org should now show a change.');
        refresh();
      } catch (e) { say('Failed: ' + e.message); }
      btn.disabled = false;
    } } }, 'Make drift');
    return h('div', { class: 'panel' }, h('h2', null, 'Facilitator'),
      h('p', null, 'Make a canned change to this org outside Terraform, logged as a portal edit.'), btn, msg);
  }

  // ---------------------------------------------------------------- start
  $('org-pick').addEventListener('change', (e) => { S.org = e.target.value; const cur = S.me.orgs.find((o) => o.id === S.org);
    $('meta-org').textContent = cur ? (cur.name || cur.id) : ''; route(); });
  $('refresh-btn').addEventListener('click', () => { clearTimeout(pollTimer); refresh(); });
  $('banner-retry').addEventListener('click', () => { clearTimeout(pollTimer); refresh(); });
  window.addEventListener('hashchange', route);
  route();
})();
