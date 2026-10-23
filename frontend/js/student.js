/**
 * WattWise — Student Dashboard JavaScript
 * Building Energy Waste Detective — Student Module
 * Ocean Blue & Soft Mint Theme
 */
'use strict';

/* ═══════════════ STATE ═══════════════ */
let studentCharts = {};
let currentPage = 'overview';
let wasteData = [];
let wastePage = 0;
const WASTE_PAGE_SIZE = 20;

/* ═══════════════ INIT ═══════════════ */
document.addEventListener('DOMContentLoaded', () => {
  // Load data
  store.load();
  wasteData = store.wasted.sort((a,b) => b.residualKw - a.residualKw);

  // Update waste badge
  document.getElementById('waste-badge').textContent = wasteData.length;

  // Sidebar navigation
  document.querySelectorAll('.nav-item[data-page]').forEach(btn => {
    btn.addEventListener('click', () => navigateTo(btn.dataset.page));
  });

  // Mobile sidebar
  const sidebar   = document.getElementById('sidebar');
  const overlay   = document.getElementById('sidebar-overlay');
  const mobileBtn = document.getElementById('mobile-menu-btn');
  mobileBtn?.addEventListener('click', () => {
    sidebar.classList.toggle('mobile-open');
    overlay.classList.toggle('active');
  });
  overlay?.addEventListener('click', () => {
    sidebar.classList.remove('mobile-open');
    overlay.classList.remove('active');
  });

  // Desktop sidebar collapse
  const sidebarToggle = document.getElementById('sidebar-toggle');
  const mainArea = document.getElementById('main-area');
  sidebarToggle?.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
  });

  // Drawer close
  document.getElementById('drawer-close')?.addEventListener('click', closeDrawer);
  document.getElementById('drawer-overlay')?.addEventListener('click', closeDrawer);

  // Explorer filters
  setupExplorerFilters();
  // Waste filters
  setupWasteFilters();

  // Render initial page
  renderPage('overview');
});

/* ═══════════════ NAVIGATION ═══════════════ */
function navigateTo(page) {
  if (currentPage === page) return;
  currentPage = page;

  document.querySelectorAll('.page-section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-item[data-page]').forEach(b => b.classList.remove('active'));

  const pageEl = document.getElementById(`page-${page}`);
  if (pageEl) pageEl.classList.add('active');

  const navBtn = document.querySelector(`.nav-item[data-page="${page}"]`);
  if (navBtn) navBtn.classList.add('active');

  const titles = {
    overview: '📊 Overview', explorer: '⚡ Energy Explorer', buildings: '🏢 Buildings',
    waste: '🔍 Waste Incidents', trends: '📊 Energy Trends', insights: '🌱 What\'s Wasted?'
  };
  document.getElementById('breadcrumb-title').textContent = titles[page] || page;

  renderPage(page);
}

function renderPage(page) {
  // Destroy stale charts for this page before re-rendering
  const pageCharts = {
    overview:  ['chart-actual-pred','chart-hourly'],
    explorer:  ['chart-exp-daily','chart-exp-dist','chart-exp-hourly'],
    buildings: ['chart-bldg-trend','chart-bldg-occ'],
    trends:    ['chart-trends-daily','chart-trends-wdwe','chart-trends-buildings','chart-trends-cost'],
  };
  (pageCharts[page] || []).forEach(id => {
    if (studentCharts[id]) { studentCharts[id].destroy(); delete studentCharts[id]; }
  });

  switch (page) {
    case 'overview':  renderOverview();  break;
    case 'explorer':  renderExplorer();  break;
    case 'buildings': renderBuildings(); break;
    case 'waste':     renderWaste();     break;
    case 'trends':    renderTrends();    break;
    case 'insights':  renderInsights();  break;
  }
}

/* ═══════════════ OVERVIEW ═══════════════ */
function renderOverview() {
  const data = store.filtered;
  const kpis = store.summaryKPIs(data);

  // KPI Cards — with plain-English subtitles
  document.getElementById('overview-kpis').innerHTML = `
    ${kpiCard('Total Energy Used', formatKwh(kpis.totalKwh), 'All 4 buildings · 90 days', 'blue', '⚡')}
    ${kpiCard('Waste Incidents', kpis.incidents.toLocaleString('en-IN'), 'Times power was unexpectedly high', 'red', '🚨')}
    ${kpiCard('Excess Energy', formatKwh(kpis.wasteKwh), 'Energy used above normal level', 'amber', '📉')}
    ${kpiCard('Est. Avoidable Cost', formatInr(kpis.wasteCostInr), 'If waste had been prevented (est.)', 'teal', '₹')}
  `;

  // Actual vs Predicted chart — last 14 days
  const daily = store.dailyTimeSeries(data);
  const last14 = daily.slice(-14);
  buildLineChart('chart-actual-pred', {
    labels: last14.map(d => d.date.slice(5)),
    datasets: [
      {
        label: 'Actual Power Used (avg kW)',
        data: last14.map(d => d.count ? +(d.actual/d.count).toFixed(2) : 0),
        borderColor: '#1D3557', backgroundColor: 'rgba(29,53,87,0.08)',
        borderWidth: 2.5, fill: true, tension: 0.3, pointRadius: 3,
      },
      {
        label: 'Expected / Normal Level (avg kW)',
        data: last14.map(d => d.count ? +(d.predicted/d.count).toFixed(2) : 0),
        borderColor: '#457B9D', borderDash: [6,3],
        borderWidth: 2, fill: false, tension: 0.3, pointRadius: 2,
      }
    ]
  }, 'kW');

  // Hourly profile
  const hourly = store.hourlyProfile(data);
  const colors = ['#1D3557','#457B9D','#A8DADC','#4CAF50'];
  const byBuilding = WW.BUILDINGS.map((b,i) => {
    const bd = data.filter(r => r.building === b);
    const hours = store.hourlyProfile(bd);
    return {
      label: b.replace(' & Computing Hub','').replace(' Block',''),
      data: hours.map(h => h.avgActual),
      borderColor: colors[i], borderWidth: 2, tension: 0.4,
      pointRadius: 0, fill: false,
    };
  });
  buildLineChart('chart-hourly', {
    labels: Array.from({length:24},(_,i)=>`${i}:00`),
    datasets: byBuilding,
  }, 'kW');

  // Building cards
  const bBreakdown = store.buildingBreakdown(data);
  const buildingIcons = { 'Academic Block A':'🏫','Library & Computing Hub':'📚','Science Complex':'🔬','Administrative Block':'🏛️' };
  document.getElementById('building-cards').innerHTML = bBreakdown.map(b => `
    <div class="building-card" onclick="navigateTo('buildings');setTimeout(()=>showBuildingDetail('${b.building}'),100)">
      <div class="building-icon">${buildingIcons[b.building] || '🏢'}</div>
      <div class="building-name">${b.building}</div>
      <div class="building-type">${buildingType(b.building)}</div>
      <div class="building-stat"><span class="bstat-label">Energy Used</span><span class="bstat-val">${formatKwh(b.totalKwh)}</span></div>
      <div class="building-stat"><span class="bstat-label">Waste Flags</span><span class="bstat-val danger">${b.incidents}</span></div>
      <div class="building-stat"><span class="bstat-label">Est. Waste Cost</span><span class="bstat-val danger">${formatInr(b.wasteCostInr)}</span></div>
    </div>
  `).join('');

  // Recent alerts
  const recent = store.wasted.sort((a,b)=>b.timestamp-a.timestamp).slice(0,8);
  document.getElementById('recent-alerts').innerHTML = recent.map(r => `
    <div class="alert-item" onclick='openDrawer(${JSON.stringify(safeStr(r))})'>
      <div class="alert-dot ${severityClass(r.wasteSeverity)}"></div>
      <div class="alert-content">
        <div class="alert-title">${r.building} · ${r.zone}</div>
        <div class="alert-meta">${fmtTs(r.timestamp)} · ${r.occupancy} people · +${r.residualKw.toFixed(1)} kW above normal</div>
      </div>
      <div class="alert-loss">${formatInr(r.excessCostInr)}</div>
    </div>
  `).join('');
}


/* ═══════════════ EXPLORER ═══════════════ */
function setupExplorerFilters() {
  const bldgSel = document.getElementById('exp-building');
  const zoneSel = document.getElementById('exp-zone');

  bldgSel?.addEventListener('change', () => {
    const b = bldgSel.value;
    const zones = store.availableZones(b);
    zoneSel.innerHTML = zones.map(z=>`<option>${z}</option>`).join('');
    if (currentPage === 'explorer') renderExplorer();
  });
  ['exp-zone','exp-from','exp-to','exp-daytype'].forEach(id => {
    document.getElementById(id)?.addEventListener('change', () => {
      if (currentPage === 'explorer') renderExplorer();
    });
  });
  document.getElementById('exp-reset')?.addEventListener('click', () => {
    document.getElementById('exp-building').value = 'All Buildings';
    document.getElementById('exp-zone').innerHTML = '<option>All Zones</option>';
    document.getElementById('exp-from').value = '2026-01-01';
    document.getElementById('exp-to').value   = '2026-03-31';
    document.getElementById('exp-daytype').value = 'all';
    if (currentPage === 'explorer') renderExplorer();
  });
}

function getExplorerData() {
  const bldg    = document.getElementById('exp-building')?.value || 'All Buildings';
  const zone    = document.getElementById('exp-zone')?.value    || 'All Zones';
  const from    = document.getElementById('exp-from')?.value    || '2026-01-01';
  const to      = document.getElementById('exp-to')?.value      || '2026-03-31';
  const daytype = document.getElementById('exp-daytype')?.value || 'all';

  return store.raw.filter(r => {
    if (bldg !== 'All Buildings' && r.building !== bldg) return false;
    if (zone !== 'All Zones' && r.zone !== zone) return false;
    const ts = r.timestamp.toISOString().slice(0,10);
    if (ts < from || ts > to) return false;
    if (daytype === 'weekday' && r.isWeekend) return false;
    if (daytype === 'weekend' && !r.isWeekend) return false;
    return true;
  });
}

function renderExplorer() {
  const data = getExplorerData();
  const kpis = store.summaryKPIs(data);

  document.getElementById('exp-kpis').innerHTML = `
    ${kpiCard('Records', data.length.toLocaleString('en-IN'), 'Filtered dataset', 'blue', '📋')}
    ${kpiCard('Total Energy', formatKwh(kpis.totalKwh), 'Period total', 'teal', '⚡')}
    ${kpiCard('Avg Power', kpis.avgPower.toFixed(1)+' kW', 'Mean per record', 'blue', '📊')}
    ${kpiCard('Waste Incidents', kpis.incidents.toString(), 'Filtered period', 'red', '🚨')}
  `;

  ['chart-exp-daily','chart-exp-dist','chart-exp-hourly'].forEach(id => {
    if (studentCharts[id]) { studentCharts[id].destroy(); delete studentCharts[id]; }
  });

  // Daily chart
  const daily = store.dailyTimeSeries(data);
  const everyNth = Math.max(1, Math.floor(daily.length/30));
  const labels = daily.filter((_,i)=>i%everyNth===0).map(d=>d.date.slice(5));
  buildLineChart('chart-exp-daily', {
    labels,
    datasets: [
      { label:'Actual', data: daily.filter((_,i)=>i%everyNth===0).map(d=>d.count?+(d.actual/d.count).toFixed(1):0), borderColor:'#1D3557', backgroundColor:'rgba(29,53,87,0.07)', fill:true, tension:0.3, borderWidth:2, pointRadius:2 },
      { label:'Predicted', data: daily.filter((_,i)=>i%everyNth===0).map(d=>d.count?+(d.predicted/d.count).toFixed(1):0), borderColor:'#457B9D', borderDash:[5,3], fill:false, tension:0.3, borderWidth:2, pointRadius:0 },
    ]
  }, 'kW');

  // Distribution histogram
  const bins = Array.from({length:20},(_,i)=>i*5);
  const hist = bins.map(b => data.filter(r=>r.actualPowerKw>=b && r.actualPowerKw<b+5).length);
  buildBarChart('chart-exp-dist', {
    labels: bins.map(b=>`${b}–${b+5}`),
    datasets: [{ label:'Records', data:hist, backgroundColor:'rgba(69,123,157,0.7)', borderColor:'#457B9D', borderWidth:1 }]
  }, 'Count');

  // Hourly
  const hourly = store.hourlyProfile(data);
  buildLineChart('chart-exp-hourly', {
    labels: hourly.map(h=>`${h.hour}:00`),
    datasets: [
      { label:'Avg Actual', data:hourly.map(h=>h.avgActual), borderColor:'#1D3557', fill:false, tension:0.4, borderWidth:2, pointRadius:2 },
      { label:'Avg Predicted', data:hourly.map(h=>h.avgPredicted), borderColor:'#457B9D', borderDash:[5,3], fill:false, tension:0.4, borderWidth:2, pointRadius:0 },
    ]
  }, 'kW');
}

/* ═══════════════ BUILDINGS ═══════════════ */
function renderBuildings() {
  const data = store.raw;
  const bBreakdown = store.buildingBreakdown(data);
  const bIcons = { 'Academic Block A':'🏫','Library & Computing Hub':'📚','Science Complex':'🔬','Administrative Block':'🏛️' };

  document.getElementById('buildings-detail-grid').innerHTML = bBreakdown.map(b => `
    <div class="building-card" style="padding:var(--space-6)" onclick="showBuildingDetail('${b.building}')">
      <div style="display:flex;align-items:center;gap:var(--space-3);margin-bottom:var(--space-4)">
        <span style="font-size:2.5rem">${bIcons[b.building]||'🏢'}</span>
        <div>
          <div class="building-name">${b.building}</div>
          <div class="building-type">${buildingType(b.building)}</div>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--space-3);margin-bottom:var(--space-4)">
        <div style="background:var(--s-selected-bg);padding:var(--space-3);border-radius:var(--radius-md)">
          <div style="font-size:10px;color:var(--neutral-400);font-weight:600;text-transform:uppercase;letter-spacing:.05em">Total Energy</div>
          <div style="font-size:var(--text-lg);font-weight:800;color:var(--s-primary)">${formatKwh(b.totalKwh)}</div>
        </div>
        <div style="background:#FEF2F2;padding:var(--space-3);border-radius:var(--radius-md)">
          <div style="font-size:10px;color:var(--neutral-400);font-weight:600;text-transform:uppercase;letter-spacing:.05em">Est. Loss</div>
          <div style="font-size:var(--text-lg);font-weight:800;color:var(--color-danger)">${formatInr(b.wasteCostInr)}</div>
        </div>
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span style="font-size:var(--text-sm);color:var(--neutral-500)">🚨 ${b.incidents} waste incidents</span>
        <span style="font-size:var(--text-sm);font-weight:600;color:var(--s-secondary)">View Analytics →</span>
      </div>
    </div>
  `).join('');
}

function showBuildingDetail(building) {
  const data = store.raw.filter(r => r.building === building);
  const kpis = store.summaryKPIs(data);

  document.getElementById('building-detail-panel').style.display = 'block';
  document.getElementById('building-detail-name').textContent = `📊 ${building} Analytics`;
  document.getElementById('building-detail-kpis').innerHTML = `
    ${kpiCard('Total Energy', formatKwh(kpis.totalKwh), '90-day period', 'blue', '⚡')}
    ${kpiCard('Waste Incidents', kpis.incidents.toString(), 'Flagged anomalies', 'red', '🚨')}
    ${kpiCard('Excess Energy', formatKwh(kpis.wasteKwh), 'Above baseline', 'amber', '📉')}
    ${kpiCard('Est. Loss', formatInr(kpis.wasteCostInr), '₹8.50/kWh', 'teal', '₹')}
  `;
  document.getElementById('building-detail-panel').scrollIntoView({ behavior:'smooth' });

  ['chart-bldg-trend','chart-bldg-occ'].forEach(id => {
    if (studentCharts[id]) { studentCharts[id].destroy(); delete studentCharts[id]; }
  });

  // 7-day trend
  const daily = store.dailyTimeSeries(data);
  const last7 = daily.slice(-7);
  buildLineChart('chart-bldg-trend', {
    labels: last7.map(d=>d.date.slice(5)),
    datasets: [
      { label:'Actual', data:last7.map(d=>d.count?+(d.actual/d.count).toFixed(1):0), borderColor:'#1D3557', fill:false, borderWidth:2, pointRadius:3 },
      { label:'Predicted', data:last7.map(d=>d.count?+(d.predicted/d.count).toFixed(1):0), borderColor:'#457B9D', borderDash:[5,3], fill:false, borderWidth:2, pointRadius:0 },
    ]
  }, 'kW');

  // Occupancy scatter (sampled)
  const sample = data.sort(()=>Math.random()-0.5).slice(0,300);
  const scatter = sample.map(r => ({ x: r.occupancy, y: r.actualPowerKw }));
  buildScatterChart('chart-bldg-occ', scatter, 'Occupancy (people)', 'Power (kW)');
}

/* ═══════════════ WASTE DETECTIVE ═══════════════ */
function setupWasteFilters() {
  ['waste-building','waste-severity','waste-sort'].forEach(id => {
    document.getElementById(id)?.addEventListener('change', () => {
      wastePage = 0;
      if (currentPage === 'waste') renderWasteTable();
    });
  });
  document.getElementById('waste-reset')?.addEventListener('click', () => {
    document.getElementById('waste-building').value = 'All Buildings';
    document.getElementById('waste-severity').value = 'all';
    document.getElementById('waste-sort').value = 'excess';
    wastePage = 0;
    if (currentPage === 'waste') renderWaste();
  });
}

function getWasteFiltered() {
  const bldg = document.getElementById('waste-building')?.value || 'All Buildings';
  const sev  = document.getElementById('waste-severity')?.value || 'all';
  const sort = document.getElementById('waste-sort')?.value || 'excess';

  let d = store.wasted;
  if (bldg !== 'All Buildings') d = d.filter(r => r.building === bldg);
  if (sev  !== 'all')           d = d.filter(r => r.wasteSeverity === sev);

  d = [...d];
  if (sort === 'excess') d.sort((a,b) => b.residualKw - a.residualKw);
  if (sort === 'cost')   d.sort((a,b) => b.excessCostInr - a.excessCostInr);
  if (sort === 'time')   d.sort((a,b) => b.timestamp - a.timestamp);
  return d;
}

function renderWaste() {
  const data = getWasteFiltered();
  const kpis = store.summaryKPIs(data);

  document.getElementById('waste-kpis').innerHTML = `
    ${kpiCard('Total Incidents', data.length.toLocaleString('en-IN'), 'Filtered results', 'red', '🚨')}
    ${kpiCard('Excess Energy', formatKwh(kpis.wasteKwh), 'Sum of all incidents', 'amber', '📉')}
    ${kpiCard('Est. Financial Loss', formatInr(kpis.wasteCostInr), '₹8.50/kWh tariff', 'red', '₹')}
    ${kpiCard('Avg Excess per Incident', (data.length ? (kpis.wasteKwh/data.length) : 0).toFixed(1)+' kWh', 'Per flagged hour', 'teal', '📊')}
  `;
  renderWasteTable();
}

function renderWasteTable() {
  const data = getWasteFiltered();
  const start = wastePage * WASTE_PAGE_SIZE;
  const page  = data.slice(start, start + WASTE_PAGE_SIZE);

  document.getElementById('waste-table-body').innerHTML = page.map(r => `
    <div class="incident-row" onclick='openDrawer(${JSON.stringify(safeStr(r))})'>
      <div style="font-size:var(--text-xs);color:var(--neutral-500)">${fmtTs(r.timestamp)}</div>
      <div>
        <div style="font-weight:600;font-size:var(--text-sm)">${r.building}</div>
        <div style="font-size:var(--text-xs);color:var(--neutral-400)">${r.zone}</div>
      </div>
      <div class="hide-mobile">${r.occupancy}</div>
      <div class="hide-mobile" style="font-weight:600">${r.actualPowerKw.toFixed(1)}</div>
      <div class="hide-mobile" style="color:var(--neutral-500)">${r.predictedPowerKw.toFixed(1)}</div>
      <div><span class="badge ${r.wasteSeverity.includes('High')?'badge-danger':r.wasteSeverity.includes('Medium')?'badge-warning':'badge-neutral'}">${r.wasteSeverity}</span></div>
      <div style="font-weight:700;color:var(--color-danger)">${formatInr(r.excessCostInr)}</div>
    </div>
  `).join('') || `<div class="empty-state" style="padding:var(--space-8)"><div class="empty-state-icon">✅</div><div class="empty-state-title">No incidents found</div><div class="empty-state-sub">No waste detected under current filters</div></div>`;

  const total = data.length;
  const pages = Math.ceil(total/WASTE_PAGE_SIZE);
  document.getElementById('waste-pagination').innerHTML = `
    <span>Showing ${start+1}–${Math.min(start+WASTE_PAGE_SIZE,total)} of ${total} incidents</span>
    <div style="display:flex;gap:var(--space-2)">
      <button onclick="changePage(-1)" class="btn btn-outline btn-sm" ${wastePage===0?'disabled':''}>← Prev</button>
      <button onclick="changePage(1)"  class="btn btn-outline btn-sm" ${wastePage>=pages-1?'disabled':''}>Next →</button>
    </div>
  `;
}

window.changePage = function(dir) {
  const data = getWasteFiltered();
  const pages = Math.ceil(data.length/WASTE_PAGE_SIZE);
  wastePage = Math.max(0, Math.min(pages-1, wastePage+dir));
  renderWasteTable();
};

/* ═══════════════ TRENDS ═══════════════ */
function renderTrends() {
  const data = store.raw;
  ['chart-trends-daily','chart-trends-wdwe','chart-trends-buildings','chart-trends-cost'].forEach(id => {
    if (studentCharts[id]) { studentCharts[id].destroy(); delete studentCharts[id]; }
  });

  // Daily: sample every 3 days
  const daily = store.dailyTimeSeries(data);
  const step = 3;
  buildLineChart('chart-trends-daily', {
    labels: daily.filter((_,i)=>i%step===0).map(d=>d.date.slice(5)),
    datasets: [
      { label:'Actual (avg kW)', data:daily.filter((_,i)=>i%step===0).map(d=>+(d.actual/d.count).toFixed(1)), borderColor:'#1D3557', fill:true, backgroundColor:'rgba(29,53,87,0.07)', tension:0.3, borderWidth:2, pointRadius:2 },
      { label:'Predicted (avg kW)', data:daily.filter((_,i)=>i%step===0).map(d=>+(d.predicted/d.count).toFixed(1)), borderColor:'#457B9D', borderDash:[5,3], fill:false, tension:0.3, borderWidth:2, pointRadius:0 },
    ]
  },'kW');

  // Weekday vs Weekend — clearer colors
  const wdwe = store.weekdayVsWeekend(data);
  buildBarChart('chart-trends-wdwe', {
    labels: ['📅 Weekdays (Mon–Fri)', '🏖️ Weekends (Sat–Sun)'],
    datasets: [{ label:'Avg Power (kW)', data:[wdwe.weekday, wdwe.weekend],
      backgroundColor:['rgba(29,53,87,0.85)','rgba(220,38,38,0.65)'],
      borderColor:['#1D3557','#DC2626'], borderWidth:2,
      borderRadius: 6,
    }]
  },'kW');

  // Building distribution (doughnut)
  const bData = store.buildingBreakdown(data);
  buildDoughnut('chart-trends-buildings', {
    labels: bData.map(b=>b.building.replace(' & Computing Hub','').replace(' Block','')),
    datasets: [{ data: bData.map(b=>+b.totalKwh.toFixed(0)), backgroundColor:['#1D3557','#457B9D','#A8DADC','#4CAF50'], borderWidth:0 }]
  });

  // Financial loss over time — sorted numerically (W1, W2, W3...)
  const weekly = {};
  store.wasted.forEach(r => {
    const wk = getWeekLabel(r.timestamp);
    if (!weekly[wk]) weekly[wk] = { label: wk, num: parseInt(wk.slice(1)), total: 0 };
    weekly[wk].total += r.excessCostInr;
  });
  const wkSorted = Object.values(weekly).sort((a,b) => a.num - b.num);
  buildBarChart('chart-trends-cost', {
    labels: wkSorted.map(w => w.label),
    datasets: [{ label:'Est. Financial Loss (₹)', data:wkSorted.map(w=>+w.total.toFixed(0)),
      backgroundColor:'rgba(220,38,38,0.55)', borderColor:'#DC2626', borderWidth:1, borderRadius:4 }]
  },'₹');
}

function getWeekLabel(ts) {
  const d = new Date(ts);
  const week = Math.floor((d - new Date('2026-01-01')) / (7 * 86400000));
  return `W${week+1}`;
}

/* ═══════════════ SUSTAINABILITY INSIGHTS ═══════════════ */
function renderInsights() {
  const data = store.raw;
  const kpis = store.summaryKPIs(data);
  const wdwe = store.weekdayVsWeekend(data);
  const bData = store.buildingBreakdown(data);
  const worstBuilding = [...bData].sort((a,b)=>b.incidents-a.incidents)[0];
  const wastePercent = kpis.totalKwh > 0 ? ((kpis.wasteKwh / kpis.totalKwh) * 100).toFixed(1) : 0;

  document.getElementById('insights-content').innerHTML = `
    <!-- Simulated notice -->
    <div class="notice-banner sim mb-5">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
      <span><strong>Remember:</strong> This dashboard shows <em>simulated</em> campus data for academic demonstration. These are model-identified patterns, not confirmed real-world waste incidents. Always verify findings with a physical inspection.</span>
    </div>

    <!-- Summary headline numbers -->
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:var(--space-4);margin-bottom:var(--space-6)">
      <div style="background:linear-gradient(135deg,#1D3557,#457B9D);border-radius:var(--radius-xl);padding:var(--space-5);color:#fff">
        <div style="font-size:2rem;font-weight:900;letter-spacing:-0.03em">${kpis.incidents}</div>
        <div style="font-size:var(--text-sm);opacity:0.85">Potential waste incidents found</div>
        <div style="font-size:var(--text-xs);opacity:0.65;margin-top:var(--space-2)">Out of 8,640 hourly records</div>
      </div>
      <div style="background:linear-gradient(135deg,#B91C1C,#DC2626);border-radius:var(--radius-xl);padding:var(--space-5);color:#fff">
        <div style="font-size:2rem;font-weight:900;letter-spacing:-0.03em">${wastePercent}%</div>
        <div style="font-size:var(--text-sm);opacity:0.85">Of total energy is waste</div>
        <div style="font-size:var(--text-xs);opacity:0.65;margin-top:var(--space-2)">${formatKwh(kpis.wasteKwh)} excess out of ${formatKwh(kpis.totalKwh)}</div>
      </div>
      <div style="background:linear-gradient(135deg,#D97706,#F59E0B);border-radius:var(--radius-xl);padding:var(--space-5);color:#fff">
        <div style="font-size:2rem;font-weight:900;letter-spacing:-0.03em">${formatInr(kpis.wasteCostInr)}</div>
        <div style="font-size:var(--text-sm);opacity:0.85">Estimated avoidable cost</div>
        <div style="font-size:var(--text-xs);opacity:0.65;margin-top:var(--space-2)">Based on ₹8.50/kWh tariff</div>
      </div>
    </div>

    <!-- How detection works — plain English -->
    <div class="chart-card" style="margin-bottom:var(--space-4)">
      <h3 style="font-size:var(--text-lg);font-weight:700;color:var(--s-primary);margin-bottom:var(--space-2)">🤔 How Does WattWise Spot Wasted Energy?</h3>
      <p style="font-size:var(--text-sm);color:var(--neutral-600);margin-bottom:var(--space-5);line-height:1.7">WattWise uses a machine learning model to answer one key question: <em>"How much electricity should this room be using right now?"</em> When actual usage is much higher than expected — and nobody is in the room — it flags a potential waste incident.</p>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:var(--space-4)">
        <div style="background:var(--s-selected-bg);border-radius:var(--radius-lg);padding:var(--space-4);border-left:3px solid var(--s-secondary)">
          <div style="font-size:1.5rem;margin-bottom:var(--space-2)">🧠</div>
          <div style="font-weight:700;color:var(--s-primary);margin-bottom:var(--space-2)">Step 1: Predict</div>
          <div style="font-size:var(--text-sm);color:var(--neutral-600);line-height:1.6">The AI model looks at the time, weather, and room occupancy to predict what the <em>normal</em> electricity use should be.</div>
        </div>
        <div style="background:var(--s-selected-bg);border-radius:var(--radius-lg);padding:var(--space-4);border-left:3px solid var(--s-secondary)">
          <div style="font-size:1.5rem;margin-bottom:var(--space-2)">⚡</div>
          <div style="font-weight:700;color:var(--s-primary);margin-bottom:var(--space-2)">Step 2: Compare</div>
          <div style="font-size:var(--text-sm);color:var(--neutral-600);line-height:1.6">It compares the predicted amount to the <em>actual</em> meter reading. If actual is much higher, there's a big gap (called the "residual").</div>
        </div>
        <div style="background:var(--s-selected-bg);border-radius:var(--radius-lg);padding:var(--space-4);border-left:3px solid var(--s-secondary)">
          <div style="font-size:1.5rem;margin-bottom:var(--space-2)">🚨</div>
          <div style="font-weight:700;color:var(--s-primary);margin-bottom:var(--space-2)">Step 3: Flag</div>
          <div style="font-size:var(--text-sm);color:var(--neutral-600);line-height:1.6">If the gap is large <em>AND</em> very few people are in the room, WattWise flags it as a potential waste event for review.</div>
        </div>
      </div>
    </div>

    <!-- Off-Hours Pattern -->
    <div class="chart-card" style="margin-bottom:var(--space-4)">
      <h3 style="font-size:var(--text-lg);font-weight:700;color:var(--neutral-800);margin-bottom:var(--space-2)">🌙 Is Energy Being Used When Nobody Is Here?</h3>
      <p style="font-size:var(--text-sm);color:var(--neutral-600);line-height:1.7;margin-bottom:var(--space-4)">On weekends, the average power draw is <strong style="color:#DC2626">${wdwe.weekend.toFixed(1)} kW</strong> — compared to <strong style="color:#1D3557">${wdwe.weekday.toFixed(1)} kW</strong> on weekdays. That's surprisingly close for periods when most buildings should be empty.</p>
      <div style="display:flex;align-items:center;gap:var(--space-3);padding:var(--space-4);background:#FEF2F2;border-radius:var(--radius-lg);border:1px solid #FECACA">
        <span style="font-size:1.5rem">💡</span>
        <span style="font-size:var(--text-sm);color:#991B1B;line-height:1.6"><strong>What this might mean:</strong> Air conditioners, lights, or computers may be left running on weekends. Turning these off when buildings are empty could reduce the estimated energy waste significantly.</span>
      </div>
    </div>

    <!-- Building to investigate -->
    <div class="chart-card" style="margin-bottom:var(--space-4)">
      <h3 style="font-size:var(--text-lg);font-weight:700;color:var(--neutral-800);margin-bottom:var(--space-2)">🏢 Which Building Needs Attention?</h3>
      <p style="font-size:var(--text-sm);color:var(--neutral-600);line-height:1.7;margin-bottom:var(--space-4)"><strong style="color:var(--s-primary)">${worstBuilding?.building}</strong> was flagged most often with <strong>${worstBuilding?.incidents} incidents</strong>. This means the system detected electricity usage far above normal levels when people weren't present, more times here than anywhere else.</p>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:var(--space-3)">
        ${bData.map(b => `
          <div style="padding:var(--space-3);border-radius:var(--radius-md);background:${b.building===worstBuilding?.building?'#FEF2F2':'var(--neutral-50)'};border:1.5px solid ${b.building===worstBuilding?.building?'#FECACA':'var(--neutral-200)'}">
            <div style="font-size:var(--text-xs);color:var(--neutral-500);margin-bottom:4px">${b.building.replace(' & Computing Hub','').replace(' Block','')}</div>
            <div style="font-weight:800;font-size:var(--text-lg);color:${b.building===worstBuilding?.building?'#DC2626':'var(--neutral-800)'}">${b.incidents}</div>
            <div style="font-size:10px;color:var(--neutral-400)">incidents</div>
          </div>
        `).join('')}
      </div>
    </div>

    <!-- Tips -->
    <div class="chart-card">
      <h3 style="font-size:var(--text-lg);font-weight:700;color:var(--neutral-800);margin-bottom:var(--space-4)">✅ Simple Ways to Help Reduce Waste</h3>
      <div style="display:flex;flex-direction:column;gap:var(--space-3)">
        ${[
          { icon:'🔌', tip:'Turn off computers, monitors, and chargers when leaving a classroom or lab.' },
          { icon:'❄️', tip:'Report air conditioners left running in empty rooms to your facility manager.' },
          { icon:'💡', tip:'Use natural light when available — switch off tube lights during daytime.' },
          { icon:'📱', tip:'If you see lights or AC on in an empty room at night, report it.' },
          { icon:'📋', tip:'Share energy-awareness tips with classmates — small habits add up across the campus.' },
        ].map(t => `
          <div style="display:flex;align-items:flex-start;gap:var(--space-3);padding:var(--space-3) var(--space-4);background:var(--s-selected-bg);border-radius:var(--radius-md)">
            <span style="font-size:1.1rem;flex-shrink:0">${t.icon}</span>
            <span style="font-size:var(--text-sm);color:var(--neutral-700);line-height:1.6">${t.tip}</span>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

/* ═══════════════ INCIDENT DRAWER ═══════════════ */
window.openDrawer = function(rStr) {
  const r = typeof rStr === 'string' ? JSON.parse(rStr) : rStr;
  const pct = Math.min(100, (r.predictedPowerKw / r.actualPowerKw) * 100);

  document.getElementById('drawer-content').innerHTML = `
    <div>
      <div class="drawer-section-title">Incident Summary</div>
      <div style="display:flex;gap:var(--space-2);flex-wrap:wrap;margin-bottom:var(--space-4)">
        <span class="badge ${r.wasteSeverity.includes('High')?'badge-danger':r.wasteSeverity.includes('Medium')?'badge-warning':'badge-neutral'}">${r.wasteSeverity}</span>
        <span class="badge badge-info">${r.building}</span>
      </div>
      <div class="drawer-row"><span class="drawer-row-label">Timestamp</span><span class="drawer-row-value">${fmtTs(r.timestamp)}</span></div>
      <div class="drawer-row"><span class="drawer-row-label">Building</span><span class="drawer-row-value">${r.building}</span></div>
      <div class="drawer-row"><span class="drawer-row-label">Zone</span><span class="drawer-row-value">${r.zone}</span></div>
      <div class="drawer-row"><span class="drawer-row-label">Occupancy</span><span class="drawer-row-value">${r.occupancy} people</span></div>
      <div class="drawer-row"><span class="drawer-row-label">Temperature</span><span class="drawer-row-value">${r.temperature}°C</span></div>
      <div class="drawer-row"><span class="drawer-row-label">Humidity</span><span class="drawer-row-value">${r.humidity}%</span></div>
    </div>
    <div>
      <div class="drawer-section-title">Power Analysis</div>
      <div class="drawer-power-bar">
        <div class="power-bar-labels"><span style="color:#1D3557">Expected: ${r.predictedPowerKw.toFixed(1)} kW</span><span style="color:#DC2626;font-weight:700">Actual: ${r.actualPowerKw.toFixed(1)} kW</span></div>
        <div class="power-bar-track" style="height:12px">
          <div class="power-bar-expected" style="width:${pct}%"></div>
          <div class="power-bar-actual" style="width:100%"></div>
        </div>
        <div style="font-size:var(--text-xs);color:var(--neutral-500)">Residual = +${r.residualKw.toFixed(1)} kW above expected baseline</div>
      </div>
      <div class="drawer-row"><span class="drawer-row-label">Actual Power</span><span class="drawer-row-value" style="color:#DC2626">${r.actualPowerKw.toFixed(1)} kW</span></div>
      <div class="drawer-row"><span class="drawer-row-label">Predicted Expected</span><span class="drawer-row-value" style="color:#457B9D">${r.predictedPowerKw.toFixed(1)} kW</span></div>
      <div class="drawer-row"><span class="drawer-row-label">Residual (Excess)</span><span class="drawer-row-value" style="color:#DC2626;font-weight:800">+${r.residualKw.toFixed(1)} kW</span></div>
    </div>
    <div>
      <div class="drawer-section-title">Financial Impact</div>
      <div class="drawer-row"><span class="drawer-row-label">Excess Energy</span><span class="drawer-row-value">${r.excessKwh.toFixed(2)} kWh</span></div>
      <div class="drawer-row"><span class="drawer-row-label">Tariff Rate</span><span class="drawer-row-value">₹8.50/kWh</span></div>
      <div class="drawer-row"><span class="drawer-row-label">Est. Financial Loss</span><span class="drawer-row-value" style="font-size:var(--text-lg);color:#DC2626;font-weight:800">${formatInr(r.excessCostInr)}</span></div>
    </div>
    <div class="drawer-disclaimer">
      <strong>🔍 System Observation:</strong> Consumption was detected substantially above the model's expected baseline while recorded occupancy was low (${r.occupancy} person(s)). This is a <em>potential</em> energy-waste incident that may require physical verification. The system does not confirm the physical cause of the excess consumption.
    </div>
  `;

  document.getElementById('drawer-overlay').classList.add('open');
  document.getElementById('incident-drawer').classList.add('open');
};

function closeDrawer() {
  document.getElementById('drawer-overlay').classList.remove('open');
  document.getElementById('incident-drawer').classList.remove('open');
}

/* ═══════════════ CHART HELPERS ═══════════════ */
function buildLineChart(id, data, yLabel='') {
  const ctx = document.getElementById(id)?.getContext('2d');
  if (!ctx) return;
  studentCharts[id] = new Chart(ctx, {
    type: 'line',
    data,
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend:{ display:true, position:'top', labels:{ usePointStyle:true, padding:14, font:{size:11,family:'Inter'} } }, tooltip:{ callbacks:{ label:ctx=>`${ctx.dataset.label}: ${ctx.parsed.y} ${yLabel}` } } },
      scales: {
        x:{ grid:{ color:'rgba(0,0,0,0.04)' }, ticks:{ font:{size:10,family:'Inter'}, maxRotation:45 } },
        y:{ grid:{ color:'rgba(0,0,0,0.04)' }, ticks:{ font:{size:10,family:'Inter'} } }
      }
    }
  });
}

function buildBarChart(id, data, yLabel='') {
  const ctx = document.getElementById(id)?.getContext('2d');
  if (!ctx) return;
  studentCharts[id] = new Chart(ctx, {
    type:'bar', data,
    options: {
      responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{ display:true, position:'top', labels:{ usePointStyle:true, padding:14, font:{size:11} } } },
      scales:{ x:{ grid:{ color:'rgba(0,0,0,0.04)' }, ticks:{font:{size:10,family:'Inter'}} }, y:{ grid:{ color:'rgba(0,0,0,0.04)' }, ticks:{font:{size:10}} } }
    }
  });
}

function buildDoughnut(id, data) {
  const ctx = document.getElementById(id)?.getContext('2d');
  if (!ctx) return;
  studentCharts[id] = new Chart(ctx, {
    type:'doughnut', data,
    options:{
      responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{ position:'right', labels:{ usePointStyle:true, font:{size:11,family:'Inter'}, padding:12 } } },
      cutout:'60%'
    }
  });
}

function buildScatterChart(id, points, xLabel, yLabel) {
  const ctx = document.getElementById(id)?.getContext('2d');
  if (!ctx) return;
  studentCharts[id] = new Chart(ctx, {
    type:'scatter',
    data:{ datasets:[{ label:'Records', data:points, backgroundColor:'rgba(69,123,157,0.4)', borderColor:'rgba(69,123,157,0.6)', pointRadius:3 }] },
    options:{
      responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{ display:false } },
      scales:{ x:{ title:{display:true,text:xLabel,font:{size:11}}, ticks:{font:{size:10}} }, y:{ title:{display:true,text:yLabel,font:{size:11}}, ticks:{font:{size:10}} } }
    }
  });
}

/* ═══════════════ HELPERS ═══════════════ */
function kpiCard(label, value, sub, color, icon) {
  return `
    <div class="kpi-card ${color}">
      <div class="kpi-icon ${color}">${icon}</div>
      <div class="kpi-label">${label}</div>
      <div class="kpi-value">${value}</div>
      <div class="kpi-sub">${sub}</div>
    </div>
  `;
}

function formatInr(v) { return '₹' + (v||0).toLocaleString('en-IN',{maximumFractionDigits:0}); }
function formatKwh(v)  { return (v||0).toLocaleString('en-IN',{maximumFractionDigits:0})+' kWh'; }

function fmtTs(ts) {
  const d = ts instanceof Date ? ts : new Date(ts);
  return d.toLocaleString('en-IN',{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});
}

function severityClass(sev) {
  if (sev.includes('High')) return 'high';
  if (sev.includes('Medium')) return 'medium';
  return 'low';
}

function buildingType(b) {
  const types = {
    'Academic Block A': 'Lecture Halls & Faculty Offices',
    'Library & Computing Hub': 'Study Areas & Server Rooms',
    'Science Complex': 'Chemistry & Bio Laboratories',
    'Administrative Block': 'Offices, Cabins & Reception',
  };
  return types[b] || 'Campus Facility';
}

function safeStr(r) {
  return {
    timestamp: r.timestamp instanceof Date ? r.timestamp.toISOString() : r.timestamp,
    building: r.building, zone: r.zone, occupancy: r.occupancy,
    temperature: r.temperature, humidity: r.humidity, hour: r.hour,
    actualPowerKw: r.actualPowerKw, predictedPowerKw: r.predictedPowerKw,
    residualKw: r.residualKw, wasteSeverity: r.wasteSeverity,
    excessKwh: r.excessKwh, excessCostInr: r.excessCostInr,
  };
}
