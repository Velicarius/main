//
// ---- Simple SPA Router + API base autodetect (no frameworks) ----
//

// --- globals / guards ---
let __INIT_DONE = false;
let __pollTimer = null;

const DEFAULT_API_BASE = `${location.protocol}//${location.host}`;

// Load/save backend URL (sanitized: replace 127.0.0.1 -> current host to avoid CORS)
function loadApiBase() {
  const saved = localStorage.getItem('ui_backend_url');
  const base = (saved && saved.trim()) ? saved.trim() : DEFAULT_API_BASE;
  try {
    const u = new URL(base);
    if (u.hostname === '127.0.0.1') {
      u.hostname = location.hostname; // normalize
      return u.origin;
    }
    return u.origin;
  } catch {
    return DEFAULT_API_BASE;
  }
}

function saveApiBase(v) {
  try {
    const u = new URL(v);
    if (u.hostname === '127.0.0.1') u.hostname = location.hostname;
    localStorage.setItem('ui_backend_url', u.origin);
    return u.origin;
  } catch {
    localStorage.setItem('ui_backend_url', DEFAULT_API_BASE);
    return DEFAULT_API_BASE;
  }
}

let API_BASE = loadApiBase();

// bind once
function initOnce() {
  if (__INIT_DONE) return;
  __INIT_DONE = true;
  window.addEventListener('hashchange', renderRoute);       // bind ONCE
  window.addEventListener('DOMContentLoaded', renderRoute); // bind ONCE
}

// cancel any polling before leaving page
function stopPolling() {
  if (__pollTimer) {
    clearInterval(__pollTimer);
    __pollTimer = null;
  }
}

// OPTIONAL: safe polling helper (use rarely, e.g., 30s; don't re-create on every render)
function startPolling(cb, ms = 30000) {
  stopPolling();
  __pollTimer = setInterval(cb, ms);
}

// ----- DOM helpers -----
function el(id) { return document.getElementById(id); }
function setApp(html) { el('app').innerHTML = html; }

// ----- Top controls (backend URL + reload) -----
function renderTopBar() {
  const html = `
    <div class="topbar">
      <label>Backend URL:</label>
      <input id="backendUrl" type="text" value="${API_BASE}" style="width:280px" />
      <button id="btnApply">Apply</button>
      <button id="btnReload">Reload</button>
    </div>
  `;
  el('topbar').innerHTML = html;

  el('btnApply').onclick = () => {
    const newBase = saveApiBase(el('backendUrl').value);
    API_BASE = newBase;
    el('backendUrl').value = API_BASE;
  };
  el('btnReload').onclick = () => renderRoute();
}

// ----- Pages -----
async function renderPositions() {
    setApp(`<h2>AI Portfolio — Positions</h2><div id="pos">Loading...</div>`);
    try {
      const resp = await fetch(`${API_BASE}/positions`);
      const data = await resp.json();
  
      // поддержка обоих форматов: {items:[...]} или просто [...]
      const rows = Array.isArray(data?.items) ? data.items :
                   (Array.isArray(data) ? data : []);
  
      if (!rows.length) {
        document.getElementById('pos').innerHTML =
          `<div style="color:#faa">No positions returned</div>`;
        return;
      }
  
      const rowsHtml = rows.map(
        x => `<tr>
                <td>${x.symbol || '-'}</td>
                <td>${x.qty || '-'}</td>
                <td>${x.buy_price || '-'}</td>
                <td>${x.last ?? '—'}</td>
              </tr>`
      ).join('');
  
      document.getElementById('pos').innerHTML = `
        <table class="tbl">
          <thead><tr><th>Symbol</th><th>Qty</th><th>Buy Price</th><th>Last</th></tr></thead>
          <tbody>${rowsHtml}</tbody>
        </table>`;
    } catch (e) {
      document.getElementById('pos').innerHTML = `Error: ${e}`;
    }
  }
  

async function renderOverview() {
  setApp(`
    <h2>📊 Portfolio Overview</h2>
    <div id="cards" class="cards"></div>
    <div id="chart" style="margin-top:14px"></div>
    <div id="breakdown" style="margin-top:18px"></div>
  `);

  const fmt = (n) => (n === null || n === undefined || isNaN(n)) ? '—' :
    new Intl.NumberFormat('en-US', {maximumFractionDigits: 2}).format(n);

  try {
    const resp = await fetch(`${API_BASE}/positions`);
    const items = await resp.json();
    const rows = Array.isArray(items?.items) ? items.items : (Array.isArray(items) ? items : []);

    // агрегаты
    let totalInvested = 0;
    let totalMkt = 0;
    let symbols = [];

    for (const p of rows) {
      const qty = Number(p.qty || 0);
      const buy = Number(p.buy_price || 0);
      const last = (p.last === null || p.last === undefined || isNaN(p.last)) ? null : Number(p.last);
      totalInvested += qty * buy;
      totalMkt     += last !== null ? qty * last : 0;
      if (p.symbol) symbols.push(p.symbol);
    }
    const pnlAbs = totalMkt - totalInvested;
    const pnlPct = totalInvested > 0 ? (pnlAbs / totalInvested * 100) : 0;

    // карточки
    el('cards').innerHTML = `
      <div class="card-row">
        <div class="card"><div class="h">Total Positions</div><div class="v">${rows.length}</div></div>
        <div class="card"><div class="h">Invested</div><div class="v">$ ${fmt(totalInvested)}</div></div>
        <div class="card"><div class="h">Market Value</div><div class="v">$ ${fmt(totalMkt)}</div></div>
        <div class="card ${pnlAbs>=0?'pos':'neg'}"><div class="h">PnL</div><div class="v">$ ${fmt(pnlAbs)} (${fmt(pnlPct)}%)</div></div>
      </div>
    `;

    // простой «спарклайн» по последним ценам (если last отсутствуют — покажем пустую подпись)
    const series = rows
      .map(r => (r.last === null || r.last === undefined || isNaN(r.last)) ? null : Number(r.last))
      .filter(v => v !== null);

    if (series.length >= 2) {
      const w = 600, h = 120, pad = 8;
      const min = Math.min(...series), max = Math.max(...series);
      const dx = (w - pad*2) / (series.length - 1);
      const mapY = (y) => h - pad - ( (y - min) / (max - min || 1) ) * (h - pad*2);
      const pts = series.map((y, i) => `${pad + i*dx},${mapY(y)}`).join(' ');
      el('chart').innerHTML = `
        <svg width="${w}" height="${h}">
          <polyline points="${pts}" fill="none" stroke-width="2"/>
        </svg>
      `;
    } else {
      el('chart').innerHTML = `<div style="opacity:.7">No enough price data to draw a chart.</div>`;
    }

    // топ по размерам (qty*buy) — первые 5
    const top = rows
      .map(r => ({ sym: r.symbol, v: Number(r.qty||0)*Number(r.buy_price||0) }))
      .sort((a,b)=>b.v-a.v)
      .slice(0,5);

    el('breakdown').innerHTML = `
      <h3>Top Holdings</h3>
      <table class="tbl">
        <thead><tr><th>Symbol</th><th>Invested</th></tr></thead>
        <tbody>${top.map(t=>`<tr><td>${t.sym||'—'}</td><td>$ ${fmt(t.v)}</td></tr>`).join('')}</tbody>
      </table>
    `;
  } catch (e) {
    setApp(`<h2>📊 Portfolio Overview</h2><div class="err">Failed to load: ${e}</div>`);
  }
}
function renderInsights() {
  setApp(`<h2>🤖 AI Insights</h2><p>Short AI summary placeholder.</p>`);
}
function renderPerformance() {
  setApp(`<h2>📈 Performance</h2><p>Returns & benchmark placeholder.</p>`);
}
function renderRisks() {
  setApp(`<h2>⚠️ Risks</h2><p>Volatility, drawdown placeholder.</p>`);
}
function renderCategories() {
  setApp(`<h2>🗂 Categories</h2><p>Sector/geography breakdown placeholder.</p>`);
}
function renderSettings() {
  setApp(`<h2>⚙️ Settings</h2><p>Preferences placeholder.</p>`);
}
function renderDashboard() {
  setApp(`<h2>🏠 Dashboard</h2><p>Welcome.</p>`);
}

// ----- Router -----
function currentRoute() {
  const raw = (location.hash || '#/dashboard').replace('#', '');
  return raw.startsWith('/') ? raw : `/${raw}`;
}

// --- ROUTER ---
function renderRoute() {
  stopPolling();            // prevent duplicate timers
  renderTopBar();           // re-render topbar is fine (only button .onclick)
  const r = currentRoute();

  if (r.startsWith('/dashboard/positions')) {
    renderPositions();
    // example: if you really need refresh, poll no more than every 30s
    // startPolling(renderPositions, 30000);
    return;
  }

  if (r.startsWith('/dashboard/overview')) {
    renderOverview();
    return;
  }

  if (r.startsWith('/dashboard/insights'))  return renderInsights();
  if (r.startsWith('/analysis/performance')) return renderPerformance();
  if (r.startsWith('/analysis/risks'))       return renderRisks();
  if (r.startsWith('/analysis/categories'))  return renderCategories();
  if (r.startsWith('/settings'))             return renderSettings();

  return renderDashboard();
}

// call once on load
initOnce();

// Dev helpers
window.__ui_reset = () => { localStorage.removeItem('ui_backend_url'); API_BASE = DEFAULT_API_BASE; };