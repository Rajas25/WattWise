/**
 * WattWise — Admin Dashboard JavaScript
 * Building Energy Waste Detective — Admin Module
 * Royal Purple & Warm Amber Theme
 */
'use strict';

let adminCharts = {};
let currentPage = 'analytics';
let invPage = 0;
const INV_PAGE_SIZE = 15;

/* ══════════════ INIT ══════════════ */
document.addEventListener('DOMContentLoaded', () => {
  store.load();

  // Update badge
  document.getElementById('admin-waste-badge').textContent = store.wasted.length;

  // Navigation
  document.querySelectorAll('.nav-item[data-page]').forEach(btn => {
    btn.addEventListener('click', () => navigateTo(btn.dataset.page));
  });

  // Mobile
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

  // Sidebar collapse
  document.getElementById('sidebar-toggle')?.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
  });

  // Drawer
  document.getElementById('drawer-close')?.addEventListener('click', closeDrawer);
  document.getElementById('drawer-overlay')?.addEventListener('click', closeDrawer);

  // Admin building filter
  document.getElementById('admin-building-filter')?.addEventListener('change', e => {
    store.setFilter('building', e.target.value);
    if (currentPage === 'analytics') renderAnalytics();
  });

  // Investigation filters
  setupInvFilters();

  // Initial page
  renderPage('analytics');
});

/* ══════════════ NAVIGATION ══════════════ */
function navigateTo(page) {
  if (currentPage === page) return;
  currentPage = page;

  document.querySelectorAll('.page-section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-item[data-page]').forEach(b => b.classList.remove('active'));

  document.getElementById(`page-${page}`)?.classList.add('active');
  document.querySelector(`.nav-item[data-page="${page}"]`)?.classList.add('active');

  const titles = {
    analytics:'Analytics Dashboard', investigation:'Waste Investigation',
    financial:'Financial Impact', buildings:'Building Comparison',
    models:'Model Performance', dataset:'Dataset Overview', config:'Configuration'
  };
  document.getElementById('breadcrumb-title').textContent = titles[page]||page;
  renderPage(page);
}

function renderPage(page) {
  const chartsPerPage = {
    analytics:    ['admin-chart-main','admin-chart-incidents','admin-chart-loss','admin-chart-occ'],
    financial:    ['fin-chart-building','fin-chart-weekly'],
    buildings:    ['bldg-chart-energy','bldg-chart-loss'],
    models:       ['model-chart-mae','model-chart-r2'],
    config:       ['config-chart-threshold'],
  };
  (chartsPerPage[page]||[]).forEach(id => {
    if (adminCharts[id]) { adminCharts[id].destroy(); delete adminCharts[id]; }
  });

  switch(page) {
    case 'analytics':    renderAnalytics();    break;
    case 'investigation':renderInvestigation();break;
    case 'financial':    renderFinancial();    break;
    case 'buildings':    renderBuildings();    break;
    case 'models':       renderModels();       break;
    case 'dataset':      renderDataset();      break;
    case 'config':       renderConfig();       break;
  }
}

/* ══════════════ ANALYTICS DASHBOARD ══════════════ */
function renderAnalytics() {
  const data = store.filtered;
  const kpis = store.summaryKPIs(data);

  document.getElementById('admin-kpis').innerHTML = `
    ${aKpiCard('Total Energy (kWh)', fmt0(kpis.totalKwh)+' kWh', '90-day simulated period', 'purple', '⚡')}
    ${aKpiCard('Waste Incidents', kpis.incidents.toLocaleString('en-IN'), 'Contextual detector flags', 'amber', '🚨')}
    ${aKpiCard('Excess Energy', fmt0(kpis.wasteKwh)+' kWh', 'Above model baseline', 'amber', '📉')}
    ${aKpiCard('Est. Financial Loss', fmtInr(kpis.wasteCostInr), '₹8.50/kWh · Estimated', 'purple', '₹')}
  `;

  // Main chart: actual vs predicted (daily, last 14)
  const daily = store.dailyTimeSeries(data);
  const last14 = daily.slice(-14);
  buildChart('admin-chart-main', 'line', {
    labels: last14.map(d=>d.date.slice(5)),
    datasets:[
      { label:'Actual (avg kW)', data:last14.map(d=>d.count?+(d.actual/d.count).toFixed(1):0),
        borderColor:'#5B21B6', backgroundColor:'rgba(91,33,182,0.07)', fill:true, tension:0.3, borderWidth:2.5, pointRadius:3 },
      { label:'Predicted (avg kW)', data:last14.map(d=>d.count?+(d.predicted/d.count).toFixed(1):0),
        borderColor:'#7C3AED', borderDash:[5,3], fill:false, tension:0.3, borderWidth:2, pointRadius:0 },
    ]
  });

  // Incidents by building
  const bData = store.buildingBreakdown(data);
  buildChart('admin-chart-incidents', 'bar', {
    labels: bData.map(b=>shortName(b.building)),
    datasets:[{ label:'Waste Incidents', data:bData.map(b=>b.incidents),
      backgroundColor:['rgba(91,33,182,0.7)','rgba(124,58,237,0.7)','rgba(217,119,6,0.7)','rgba(253,230,138,0.9)'],
      borderColor:['#5B21B6','#7C3AED','#D97706','#B45309'], borderWidth:1.5 }]
  });

  // Loss by building
  buildChart('admin-chart-loss', 'bar', {
    labels: bData.map(b=>shortName(b.building)),
    datasets:[{ label:'Est. Loss (₹)', data:bData.map(b=>+b.wasteCostInr.toFixed(0)),
      backgroundColor:'rgba(217,119,6,0.7)', borderColor:'#D97706', borderWidth:1.5 }]
  });

  // Occupancy scatter (sampled)
  const sample = data.sort(()=>Math.random()-0.5).slice(0,500);
  buildChart('admin-chart-occ', 'scatter', {
    datasets:[
      { label:'Normal', data:sample.filter(r=>!r.isWasteDetected).map(r=>({x:r.occupancy,y:r.actualPowerKw})),
        backgroundColor:'rgba(91,33,182,0.3)', pointRadius:3 },
      { label:'Waste Detected', data:sample.filter(r=>r.isWasteDetected).map(r=>({x:r.occupancy,y:r.actualPowerKw})),
        backgroundColor:'rgba(220,38,38,0.7)', pointRadius:5 },
    ]
  }, {scales:{x:{title:{display:true,text:'Occupancy (people)'}},y:{title:{display:true,text:'Power (kW)'}}}});

  // Recent incidents table
  const recent = store.wasted.sort((a,b)=>b.timestamp-a.timestamp).slice(0,12);
  document.getElementById('admin-incidents-table').innerHTML = recent.map(r=>`
    <div class="inv-row" onclick='openDrawer(${JSON.stringify(rowData(r))})'>
      <div style="font-size:10px;color:var(--neutral-500)">${fmtTs(r.timestamp)}</div>
      <div><div style="font-weight:600;font-size:11px">${r.building}</div><div style="font-size:10px;color:var(--neutral-400)">${r.zone}</div></div>
      <div class="hide-md">${r.occupancy}</div>
      <div class="hide-md" style="font-weight:600">${r.actualPowerKw.toFixed(1)}</div>
      <div class="hide-md" style="color:var(--a-text-muted)">${r.predictedPowerKw.toFixed(1)}</div>
      <div class="hide-md" style="color:#DC2626;font-weight:700">+${r.residualKw.toFixed(1)}</div>
      <div><span class="badge ${sevBadge(r.wasteSeverity)}" style="font-size:10px">${r.wasteSeverity.replace(' Waste','')}</span></div>
      <div style="font-weight:800;color:#D97706">${fmtInr(r.excessCostInr)}</div>
      <div><button class="btn btn-sm" style="background:var(--a-selected-bg);color:var(--a-primary);border:1px solid var(--a-border);font-size:10px" onclick="event.stopPropagation();openDrawer(${JSON.stringify(rowData(r))})">View</button></div>
    </div>
  `).join('');
}

/* ══════════════ WASTE INVESTIGATION ══════════════ */
function setupInvFilters() {
  ['inv-building','inv-severity','inv-sort'].forEach(id => {
    document.getElementById(id)?.addEventListener('change', () => { invPage=0; if(currentPage==='investigation') renderInvTable(); });
  });
  document.getElementById('inv-search')?.addEventListener('input', () => { invPage=0; if(currentPage==='investigation') renderInvTable(); });
  document.getElementById('inv-reset')?.addEventListener('click', () => {
    ['inv-building','inv-severity','inv-sort'].forEach(id => { const el=document.getElementById(id); if(el) el.selectedIndex=0; });
    document.getElementById('inv-search').value='';
    invPage=0;
    if(currentPage==='investigation') renderInvestigation();
  });
}

function getInvData() {
  const bldg   = document.getElementById('inv-building')?.value || 'All Buildings';
  const sev    = document.getElementById('inv-severity')?.value || 'all';
  const sort   = document.getElementById('inv-sort')?.value    || 'residual';
  const search = (document.getElementById('inv-search')?.value||'').toLowerCase();

  let d = store.wasted;
  if (bldg !== 'All Buildings') d = d.filter(r=>r.building===bldg);
  if (sev  !== 'all')           d = d.filter(r=>r.wasteSeverity===sev);
  if (search) d = d.filter(r=>r.building.toLowerCase().includes(search)||r.zone.toLowerCase().includes(search));

  d = [...d];
  if (sort==='residual') d.sort((a,b)=>b.residualKw-a.residualKw);
  if (sort==='cost')     d.sort((a,b)=>b.excessCostInr-a.excessCostInr);
  if (sort==='time')     d.sort((a,b)=>b.timestamp-a.timestamp);
  return d;
}

function renderInvestigation() {
  renderInvTable();
}

function renderInvTable() {
  const data  = getInvData();
  const start = invPage * INV_PAGE_SIZE;
  const page  = data.slice(start, start+INV_PAGE_SIZE);

  document.getElementById('inv-table-body').innerHTML = page.map(r=>`
    <div class="inv-row" onclick='openDrawer(${JSON.stringify(rowData(r))})'>
      <div style="font-size:10px;color:var(--neutral-500)">${fmtTs(r.timestamp)}</div>
      <div><div style="font-weight:600;font-size:11px">${r.building}</div><div style="font-size:10px;color:var(--neutral-400)">${r.zone}</div></div>
      <div class="hide-md">${r.occupancy}</div>
      <div class="hide-md" style="font-weight:700">${r.actualPowerKw.toFixed(1)}</div>
      <div class="hide-md" style="color:var(--neutral-500)">${r.predictedPowerKw.toFixed(1)}</div>
      <div class="hide-md" style="color:#DC2626;font-weight:800">+${r.residualKw.toFixed(1)}</div>
      <div><span class="badge ${sevBadge(r.wasteSeverity)}" style="font-size:10px">${r.wasteSeverity.replace(' Waste','')}</span></div>
      <div style="font-weight:800;color:#D97706">${fmtInr(r.excessCostInr)}</div>
      <div><button class="btn btn-sm" style="background:var(--a-selected-bg);color:var(--a-primary);border:1px solid var(--a-border);font-size:10px">Details</button></div>
    </div>
  `).join('') || `<div class="empty-state" style="padding:var(--space-8)"><div class="empty-state-icon">✅</div><div class="empty-state-title">No incidents found</div></div>`;

  const total = data.length;
  const pages = Math.ceil(total/INV_PAGE_SIZE);
  document.getElementById('inv-pagination').innerHTML = `
    <span>${total} incidents · Page ${invPage+1} of ${pages}</span>
    <div style="display:flex;gap:var(--space-2)">
      <button onclick="changeInvPage(-1)" class="btn btn-outline btn-sm" ${invPage===0?'disabled':''}>← Prev</button>
      <button onclick="changeInvPage(1)"  class="btn btn-outline btn-sm" ${invPage>=pages-1?'disabled':''}>Next →</button>
    </div>
  `;
}

window.changeInvPage = function(dir) {
  const pages = Math.ceil(getInvData().length/INV_PAGE_SIZE);
  invPage = Math.max(0,Math.min(pages-1,invPage+dir));
  renderInvTable();
};

/* ══════════════ FINANCIAL ══════════════ */
function renderFinancial() {
  const data = store.raw;
  const wasted = store.wasted;
  const kpis = store.summaryKPIs(wasted);

  document.getElementById('fin-kpis').innerHTML = `
    ${aKpiCard('Total Excess Energy', fmt0(kpis.wasteKwh)+' kWh', 'Sum of all incident residuals', 'amber', '📉')}
    ${aKpiCard('Total Est. Loss', fmtInr(kpis.wasteCostInr), 'At ₹8.50/kWh tariff', 'purple', '₹')}
    ${aKpiCard('Incidents', kpis.incidents.toLocaleString('en-IN'), 'Contextual waste flags', 'amber', '🚨')}
    ${aKpiCard('Avg Loss/Incident', fmtInr(kpis.incidents ? kpis.wasteCostInr/kpis.incidents : 0), 'Per flagged hour-record', 'purple', '📊')}
  `;

  const bData = store.buildingBreakdown(data);
  buildChart('fin-chart-building', 'bar', {
    labels: bData.map(b=>shortName(b.building)),
    datasets:[{ label:'Est. Financial Loss (₹)', data:bData.map(b=>+b.wasteCostInr.toFixed(0)),
      backgroundColor:'rgba(217,119,6,0.75)', borderColor:'#D97706', borderWidth:2 }]
  });

  // Weekly trend
  const weekly = {};
  wasted.forEach(r => {
    const wk = `W${Math.floor((r.timestamp - new Date('2026-01-01')) / (7*86400000))+1}`;
    weekly[wk] = (weekly[wk]||0) + r.excessCostInr;
  });
  const wkKeys = Object.keys(weekly).sort((a,b)=>+a.slice(1)-+b.slice(1));
  buildChart('fin-chart-weekly', 'line', {
    labels: wkKeys,
    datasets:[{ label:'Weekly Loss (₹)', data:wkKeys.map(k=>+weekly[k].toFixed(0)),
      borderColor:'#7C3AED', backgroundColor:'rgba(124,58,237,0.08)', fill:true, tension:0.4, borderWidth:2, pointRadius:3 }]
  });

  // Top 20 incidents by loss
  const top20 = [...wasted].sort((a,b)=>b.excessCostInr-a.excessCostInr).slice(0,20);
  document.getElementById('fin-table').innerHTML = top20.map(r=>`
    <tr>
      <td style="font-size:var(--text-xs)">${fmtTs(r.timestamp)}</td>
      <td style="font-weight:600">${r.building}</td>
      <td style="font-size:var(--text-xs);color:var(--neutral-400)">${r.zone}</td>
      <td style="color:#DC2626;font-weight:700">${r.residualKw.toFixed(1)} kW</td>
      <td>${r.excessKwh.toFixed(2)} kWh</td>
      <td style="color:var(--neutral-500)">₹8.50</td>
      <td style="font-weight:800;color:#D97706">${fmtInr(r.excessCostInr)}</td>
    </tr>
  `).join('');
}

/* ══════════════ BUILDING COMPARISON ══════════════ */
function renderBuildings() {
  const bData = store.buildingBreakdown(store.raw);
  const icons = {'Academic Block A':'🏫','Library & Computing Hub':'📚','Science Complex':'🔬','Administrative Block':'🏛️'};

  document.getElementById('building-compare-cards').innerHTML = `
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:var(--space-4)">
    ${bData.map(b=>`
      <div style="background:#fff;border-radius:var(--radius-xl);border:2px solid var(--a-border);padding:var(--space-5)">
        <div style="font-size:2rem;margin-bottom:var(--space-3)">${icons[b.building]||'🏢'}</div>
        <div style="font-size:var(--text-base);font-weight:700;color:var(--a-primary);margin-bottom:var(--space-4)">${b.building}</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--space-2)">
          <div style="background:var(--a-selected-bg);padding:var(--space-3);border-radius:var(--radius-md)">
            <div style="font-size:10px;color:var(--neutral-400);font-weight:600;text-transform:uppercase">Energy</div>
            <div style="font-size:var(--text-base);font-weight:800;color:var(--a-primary)">${fmt0(b.totalKwh)} kWh</div>
          </div>
          <div style="background:#FFF7ED;padding:var(--space-3);border-radius:var(--radius-md)">
            <div style="font-size:10px;color:var(--neutral-400);font-weight:600;text-transform:uppercase">Est. Loss</div>
            <div style="font-size:var(--text-base);font-weight:800;color:#D97706">${fmtInr(b.wasteCostInr)}</div>
          </div>
          <div style="background:var(--neutral-50);padding:var(--space-3);border-radius:var(--radius-md)">
            <div style="font-size:10px;color:var(--neutral-400);font-weight:600;text-transform:uppercase">Incidents</div>
            <div style="font-size:var(--text-base);font-weight:800;color:#DC2626">${b.incidents}</div>
          </div>
          <div style="background:var(--neutral-50);padding:var(--space-3);border-radius:var(--radius-md)">
            <div style="font-size:10px;color:var(--neutral-400);font-weight:600;text-transform:uppercase">Avg Power</div>
            <div style="font-size:var(--text-base);font-weight:800;color:var(--neutral-700)">${b.avgPower.toFixed(1)} kW</div>
          </div>
        </div>
      </div>
    `).join('')}
    </div>
  `;

  buildChart('bldg-chart-energy', 'bar', {
    labels: bData.map(b=>shortName(b.building)),
    datasets:[{ label:'Total Energy (kWh)', data:bData.map(b=>+b.totalKwh.toFixed(0)),
      backgroundColor:['rgba(91,33,182,0.7)','rgba(124,58,237,0.7)','rgba(217,119,6,0.7)','rgba(168,218,220,0.9)'],
      borderWidth:1.5 }]
  });

  buildChart('bldg-chart-loss', 'bar', {
    labels: bData.map(b=>shortName(b.building)),
    datasets:[{ label:'Est. Financial Loss (₹)', data:bData.map(b=>+b.wasteCostInr.toFixed(0)),
      backgroundColor:'rgba(217,119,6,0.75)', borderColor:'#D97706', borderWidth:1.5 }]
  });

  document.getElementById('bldg-compare-tbody').innerHTML = bData.map(b=>`
    <tr>
      <td style="font-weight:700">${b.building}</td>
      <td>${fmt0(b.totalKwh)} kWh</td>
      <td>${b.avgPower.toFixed(1)} kW</td>
      <td style="font-weight:700;color:#DC2626">${b.incidents}</td>
      <td>${b.wasteKwh.toFixed(1)} kWh</td>
      <td style="font-weight:800;color:#D97706">${fmtInr(b.wasteCostInr)}</td>
    </tr>
  `).join('');
}

/* ══════════════ MODEL PERFORMANCE ══════════════ */
function renderModels() {
  // Regression model cards
  document.getElementById('model-cards').innerHTML = WW.REGRESSION_METRICS.map(m=>`
    <div class="model-card ${m.isBest?'best':''}">
      <div class="model-name">${m.model}</div>
      <div class="model-metric">
        <span class="mm-label">MAE (kW)</span>
        <span class="mm-value ${m.isBest?'best-val':''}">${m.mae.toFixed(3)}</span>
      </div>
      <div class="model-metric">
        <span class="mm-label">RMSE (kW)</span>
        <span class="mm-value ${m.isBest?'best-val':''}">${m.rmse.toFixed(3)}</span>
      </div>
      <div class="model-metric">
        <span class="mm-label">R² Score</span>
        <span class="mm-value ${m.isBest?'best-val':''}">${m.r2.toFixed(4)}</span>
      </div>
      <div class="model-metric">
        <span class="mm-label">MAPE (%)</span>
        <span class="mm-value ${m.isBest?'best-val':''}">${m.mape.toFixed(2)}%</span>
      </div>
    </div>
  `).join('');

  // MAE bar chart
  buildChart('model-chart-mae', 'bar', {
    labels: WW.REGRESSION_METRICS.map(m=>m.model),
    datasets:[{ label:'MAE (kW) — lower is better', data:WW.REGRESSION_METRICS.map(m=>m.mae),
      backgroundColor:['rgba(91,33,182,0.5)','rgba(124,58,237,0.5)','rgba(124,58,237,0.9)'],
      borderColor:['#5B21B6','#7C3AED','#7C3AED'], borderWidth:2 }]
  });

  // R² chart
  buildChart('model-chart-r2', 'bar', {
    labels: WW.REGRESSION_METRICS.map(m=>m.model),
    datasets:[{ label:'R² Score — higher is better', data:WW.REGRESSION_METRICS.map(m=>m.r2),
      backgroundColor:['rgba(217,119,6,0.5)','rgba(217,119,6,0.7)','rgba(217,119,6,0.95)'],
      borderColor:'#D97706', borderWidth:2 }]
  });

  // Detection comparison cards
  const ctx = WW.DETECTION_METRICS.contextual;
  const iso = WW.DETECTION_METRICS.isoForest;

  document.getElementById('detection-cards').innerHTML = `
    <div class="detector-card best">
      <div class="detector-name" style="color:var(--a-primary)">✅ Contextual ML Residual Detector</div>
      <p style="font-size:var(--text-xs);color:var(--neutral-500);margin-bottom:var(--space-4)">Supervised physics baseline + occupancy gating. Domain-specific design for energy waste.</p>
      ${metricBar('Precision', ctx.precision, '#5B21B6')}
      ${metricBar('Recall', ctx.recall, '#059669')}
      ${metricBar('F1-Score', ctx.f1, '#7C3AED')}
      ${metricBar('Accuracy', ctx.accuracy, '#2563EB')}
      <div class="cm-grid">
        <div class="cm-cell cm-tn"><div class="cm-cell-label">True Negatives</div><div class="cm-cell-val">${ctx.tn.toLocaleString('en-IN')}</div></div>
        <div class="cm-cell cm-fp"><div class="cm-cell-label">False Positives</div><div class="cm-cell-val">${ctx.fp}</div></div>
        <div class="cm-cell cm-fn"><div class="cm-cell-label">False Negatives</div><div class="cm-cell-val">${ctx.fn}</div></div>
        <div class="cm-cell cm-tp"><div class="cm-cell-label">True Positives</div><div class="cm-cell-val">${ctx.tp}</div></div>
      </div>
    </div>
    <div class="detector-card">
      <div class="detector-name" style="color:var(--neutral-600)">⚠️ Isolation Forest (Unsupervised Baseline)</div>
      <p style="font-size:var(--text-xs);color:var(--neutral-500);margin-bottom:var(--space-4)">Multidimensional outlier isolation. Flags any statistically rare point, regardless of energy-waste semantics.</p>
      ${metricBar('Precision', iso.precision, '#DC2626')}
      ${metricBar('Recall', iso.recall, '#DC2626')}
      ${metricBar('F1-Score', iso.f1, '#DC2626')}
      ${metricBar('Accuracy', iso.accuracy, '#D97706')}
      <div class="cm-grid">
        <div class="cm-cell cm-tn"><div class="cm-cell-label">True Negatives</div><div class="cm-cell-val">${iso.tn.toLocaleString('en-IN')}</div></div>
        <div class="cm-cell cm-fp"><div class="cm-cell-label">False Positives</div><div class="cm-cell-val cm-cell-val" style="color:#991B1B">${iso.fp}</div></div>
        <div class="cm-cell cm-fn"><div class="cm-cell-label">False Negatives</div><div class="cm-cell-val" style="color:#991B1B">${iso.fn}</div></div>
        <div class="cm-cell cm-tp"><div class="cm-cell-label">True Positives</div><div class="cm-cell-val">${iso.tp}</div></div>
      </div>
    </div>
  `;
}

function metricBar(label, val, color) {
  return `
    <div class="metric-row">
      <span class="metric-row-label" style="min-width:80px">${label}</span>
      <div class="metric-bar-wrap">
        <div class="metric-bar-fill" style="width:${(val*100).toFixed(1)}%;background:${color}"></div>
      </div>
      <span class="metric-row-val" style="color:${color}">${val.toFixed(4)}</span>
    </div>
  `;
}

/* ══════════════ DATASET ══════════════ */
function renderDataset() {
  const schema = [
    { name:'timestamp',     type:'Datetime', desc:'Hourly telemetry measurement timestamp (UTC)',                    role:'Input Feature' },
    { name:'building',      type:'String',   desc:'Campus facility name (one of 4 simulated buildings)',             role:'Input Feature' },
    { name:'zone',          type:'String',   desc:'Functional zone inside facility',                                 role:'Input Feature' },
    { name:'occupancy',     type:'Integer',  desc:'Headcount present in zone (0–120 people)',                        role:'Input Feature' },
    { name:'temperature',   type:'Float',    desc:'Ambient outdoor temperature (16.0°C – 42.0°C)',                   role:'Input Feature' },
    { name:'humidity',      type:'Float',    desc:'Relative humidity (30.0% – 95.0%)',                               role:'Input Feature' },
    { name:'hour',          type:'Integer',  desc:'Hour of day (0–23) derived from timestamp',                       role:'Engineered' },
    { name:'day_of_week',   type:'Integer',  desc:'Day of week (0=Monday, 6=Sunday)',                                role:'Engineered' },
    { name:'is_weekend',    type:'Binary',   desc:'1 if Saturday or Sunday, else 0',                                 role:'Engineered' },
    { name:'is_business_hours',type:'Binary','desc':'1 if Mon–Fri 08:00–18:00, else 0',                              role:'Engineered' },
    { name:'cooling_need',  type:'Float',    desc:'max(0, temperature − 24°C) — HVAC cooling demand proxy',         role:'Engineered' },
    { name:'hour_sin',      type:'Float',    desc:'sin(2π×hour/24) — cyclical hour encoding',                        role:'Engineered' },
    { name:'hour_cos',      type:'Float',    desc:'cos(2π×hour/24) — cyclical hour encoding',                        role:'Engineered' },
    { name:'actual_power_kw',type:'Float',   desc:'TARGET: Measured active power consumption (kW)',                  role:'Target Variable' },
    { name:'is_anomaly',    type:'Binary',   desc:'Ground-truth waste label — EVALUATION ONLY. Not used as feature.',role:'Eval Only' },
    { name:'anomaly_type',  type:'String',   desc:'Waste category label (e.g., "Empty Room After Hours") — EVAL ONLY.',role:'Eval Only' },
  ];

  document.getElementById('dataset-schema').innerHTML = schema.map(f=>`
    <div class="field-row">
      <div class="field-name">${f.name}</div>
      <div style="font-size:var(--text-xs);color:var(--neutral-500)">${f.type}</div>
      <div style="font-size:var(--text-sm);color:var(--neutral-700)">${f.desc}</div>
      <div>${f.role==='Eval Only'?`<span class="field-eval-badge">⚠️ Eval Only</span>`
           :f.role==='Target Variable'?`<span class="badge badge-purple">${f.role}</span>`
           :f.role==='Engineered'?`<span class="badge badge-info">${f.role}</span>`
           :`<span class="badge badge-neutral">${f.role}</span>`}</div>
    </div>
  `).join('');

  const bldgInfo = [
    { name:'Academic Block A', icon:'🏫', zones:['Lecture Halls & Classrooms','Faculty Offices','Student Lounge'], desc:'Primary teaching facility. High daytime occupancy, strong diurnal load pattern.' },
    { name:'Library & Computing Hub', icon:'📚', zones:['Central Study Area','Server & Data Room','Reading Galleries'], desc:'Continuous server baseload. Study areas follow academic schedule.' },
    { name:'Science Complex', icon:'🔬', zones:['Chemistry & Bio Labs','Equipment Storage','Research Offices'], desc:'Laboratory equipment creates specialized load patterns. Higher waste risk during breaks.' },
    { name:'Administrative Block', icon:'🏛️', zones:['Administration Offices','Conference Rooms','Reception & Lobby'], desc:'Office-hours load profile. Low occupancy on evenings and weekends.' },
  ];

  document.getElementById('dataset-buildings').innerHTML = bldgInfo.map(b=>`
    <div style="background:#fff;border-radius:var(--radius-xl);border:1.5px solid var(--a-border);padding:var(--space-5)">
      <div style="display:flex;align-items:center;gap:var(--space-3);margin-bottom:var(--space-3)">
        <span style="font-size:2rem">${b.icon}</span>
        <div style="font-weight:700;color:var(--a-primary)">${b.name}</div>
      </div>
      <p style="font-size:var(--text-sm);color:var(--neutral-500);margin-bottom:var(--space-3)">${b.desc}</p>
      <div style="font-size:var(--text-xs);font-weight:600;color:var(--neutral-400);text-transform:uppercase;letter-spacing:.06em;margin-bottom:var(--space-2)">Zones:</div>
      ${b.zones.map(z=>`<div style="font-size:var(--text-xs);color:var(--neutral-600);padding:3px 0;border-bottom:1px solid var(--neutral-100)">• ${z}</div>`).join('')}
    </div>
  `).join('');
}

/* ══════════════ CONFIGURATION ══════════════ */
function renderConfig() {
  document.getElementById('config-controls').innerHTML = `
    <div class="config-group">
      <div class="config-title">🔍 Detection Thresholds</div>
      <div class="config-row">
        <label>Residual Threshold (kW) <strong id="val-residual">10.0 kW</strong></label>
        <input type="range" id="slider-residual" min="3" max="30" step="0.5" value="10"
               oninput="document.getElementById('val-residual').textContent=this.value+' kW';updateConfigChart()" />
        <div style="font-size:var(--text-xs);color:var(--neutral-400);margin-top:var(--space-2)">Flag waste if Actual − Predicted ≥ this value.</div>
      </div>
      <div class="config-row">
        <label>Occupancy Threshold (people) <strong id="val-occ">5 people</strong></label>
        <input type="range" id="slider-occ" min="0" max="15" step="1" value="5"
               oninput="document.getElementById('val-occ').textContent=this.value+' people';updateConfigChart()" />
        <div style="font-size:var(--text-xs);color:var(--neutral-400);margin-top:var(--space-2)">Space considered idle at or below this headcount.</div>
      </div>
      <div class="config-row">
        <label>Electricity Tariff (₹/kWh) <strong id="val-tariff">₹8.50</strong></label>
        <input type="range" id="slider-tariff" min="4" max="20" step="0.25" value="8.50"
               oninput="document.getElementById('val-tariff').textContent='₹'+parseFloat(this.value).toFixed(2)" />
        <div style="font-size:var(--text-xs);color:var(--neutral-400);margin-top:var(--space-2)">Standard Indian institutional/commercial billing rate.</div>
      </div>
      <div class="config-proto-note">
        ⚠️ <strong>Prototype Only:</strong> These sliders preview how configuration changes would look.
        The Python ML backend is not modified from this interface. Changes here do not affect the trained model.
      </div>
    </div>
    <div class="config-group">
      <div class="config-title">🤖 Model Configuration</div>
      <div class="config-row">
        <label>Active Prediction Model <strong>XGBoost Regressor</strong></label>
        <select class="filter-select" style="width:100%">
          <option selected>XGBoost Regressor (Champion · R²=0.9038)</option>
          <option>Random Forest Regressor (R²=0.9010)</option>
          <option>Linear Regression Baseline (R²=0.8922)</option>
        </select>
      </div>
      <div class="config-row">
        <label>Dataset</label>
        <div style="padding:var(--space-3);background:var(--neutral-50);border-radius:var(--radius-md);font-size:var(--text-sm);color:var(--neutral-700)">
          📋 8,640 synthetic records · Jan 1 – Mar 31, 2026 · 90 days · 4 buildings
        </div>
      </div>
      <div class="config-row">
        <label>Train / Test Split</label>
        <div style="padding:var(--space-3);background:var(--neutral-50);border-radius:var(--radius-md);font-size:var(--text-sm);color:var(--neutral-700)">
          🔒 Chronological 80/20 split · Train: 6,912 records · Test: 1,728 records
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--space-3);margin-top:var(--space-4)">
        <button class="btn btn-outline" onclick="alert('This is a UI prototype. Save configuration is not implemented in the frontend demo.')">💾 Save (Prototype)</button>
        <button class="btn btn-outline" onclick="alert('Retrain would run: python train_model.py — not available from this interface.')">🔄 Retrain (Prototype)</button>
      </div>
    </div>
  `;

  updateConfigChart();
}

function updateConfigChart() {
  if (adminCharts['config-chart-threshold']) {
    adminCharts['config-chart-threshold'].destroy();
    delete adminCharts['config-chart-threshold'];
  }

  const thresholds = [3,5,7,10,13,15,20,25,30];
  const data = store.raw;
  const counts = thresholds.map(t => {
    const occ = parseInt(document.getElementById('slider-occ')?.value || 5);
    return data.filter(r => r.residualKw >= t && r.occupancy <= occ).length;
  });

  buildChart('config-chart-threshold', 'line', {
    labels: thresholds.map(t=>`${t} kW`),
    datasets:[{
      label:'Flagged Incidents', data:counts,
      borderColor:'#7C3AED', backgroundColor:'rgba(124,58,237,0.1)',
      fill:true, tension:0.3, borderWidth:2.5, pointRadius:4,
    }]
  });
}

window.updateConfigChart = updateConfigChart;

/* ══════════════ INCIDENT DRAWER ══════════════ */
window.openDrawer = function(rStr) {
  const r = typeof rStr === 'string' ? JSON.parse(rStr) : rStr;
  const pct = Math.min(100, (r.predictedPowerKw / r.actualPowerKw) * 100);

  document.getElementById('drawer-content').innerHTML = `
    <div>
      <div class="drawer-section-title">Incident Classification</div>
      <div style="display:flex;gap:var(--space-2);flex-wrap:wrap;margin-bottom:var(--space-4)">
        <span class="badge ${sevBadge(r.wasteSeverity)}">${r.wasteSeverity}</span>
        <span class="badge badge-purple">${r.building}</span>
      </div>
      <div class="drawer-row"><span class="drawer-row-label">Timestamp</span><span class="drawer-row-value">${fmtTs(r.timestamp)}</span></div>
      <div class="drawer-row"><span class="drawer-row-label">Building</span><span class="drawer-row-value">${r.building}</span></div>
      <div class="drawer-row"><span class="drawer-row-label">Zone</span><span class="drawer-row-value">${r.zone}</span></div>
      <div class="drawer-row"><span class="drawer-row-label">Occupancy</span><span class="drawer-row-value">${r.occupancy} people ≤ threshold (5)</span></div>
      <div class="drawer-row"><span class="drawer-row-label">Temperature</span><span class="drawer-row-value">${r.temperature}°C</span></div>
      <div class="drawer-row"><span class="drawer-row-label">Humidity</span><span class="drawer-row-value">${r.humidity}%</span></div>
    </div>
    <div>
      <div class="drawer-section-title">Power Analysis (Contextual Detection)</div>
      <div class="drawer-power-bar">
        <div class="power-bar-labels">
          <span style="color:#5B21B6">Expected: ${r.predictedPowerKw.toFixed(2)} kW</span>
          <span style="color:#DC2626;font-weight:700">Actual: ${r.actualPowerKw.toFixed(2)} kW</span>
        </div>
        <div class="power-bar-track" style="height:14px">
          <div class="power-bar-expected" style="width:${pct}%;background:#5B21B6"></div>
          <div class="power-bar-actual" style="width:100%;background:#DC2626"></div>
        </div>
        <div style="font-size:var(--text-xs);color:var(--neutral-500)">Residual: +${r.residualKw.toFixed(2)} kW ≥ threshold (10.0 kW) → FLAGGED</div>
      </div>
      <div class="drawer-row"><span class="drawer-row-label">Actual Power</span><span class="drawer-row-value" style="color:#DC2626">${r.actualPowerKw.toFixed(2)} kW</span></div>
      <div class="drawer-row"><span class="drawer-row-label">XGBoost Predicted</span><span class="drawer-row-value" style="color:#5B21B6">${r.predictedPowerKw.toFixed(2)} kW</span></div>
      <div class="drawer-row"><span class="drawer-row-label">Residual (Excess)</span><span class="drawer-row-value" style="color:#DC2626;font-size:var(--text-lg);font-weight:800">+${r.residualKw.toFixed(2)} kW</span></div>
    </div>
    <div>
      <div class="drawer-section-title">Financial Impact Calculation</div>
      <div class="formula-box" style="font-size:11px;line-height:1.9">
        excess_kwh = ${r.residualKw.toFixed(2)} kW × 1 hr = <span class="formula-value">${r.excessKwh.toFixed(3)} kWh</span>
        loss_inr   = ${r.excessKwh.toFixed(3)} × ₹8.50 = <span class="formula-value">${fmtInr(r.excessCostInr)}</span>
      </div>
      <div class="drawer-row" style="margin-top:var(--space-3)"><span class="drawer-row-label">Est. Financial Loss</span><span class="drawer-row-value" style="font-size:var(--text-xl);color:#D97706;font-weight:900">${fmtInr(r.excessCostInr)}</span></div>
    </div>
    <div class="drawer-disclaimer">
      <strong>Model Transparency:</strong> An incident is flagged when <code>residual ≥ 10.0 kW</code> AND <code>occupancy ≤ 5 people</code>. The XGBoost model predicted the expected baseline using occupancy, weather, time, and building context. This is a <em>model-identified anomaly</em> — physical verification is required to confirm the root cause.
    </div>
  `;

  document.getElementById('drawer-overlay').classList.add('open');
  document.getElementById('incident-drawer').classList.add('open');
};

function closeDrawer() {
  document.getElementById('drawer-overlay').classList.remove('open');
  document.getElementById('incident-drawer').classList.remove('open');
}

/* ══════════════ CHART BUILDER ══════════════ */
function buildChart(id, type, data, extraOpts={}) {
  const ctx = document.getElementById(id)?.getContext('2d');
  if (!ctx) return;
  adminCharts[id] = new Chart(ctx, {
    type, data,
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display:true, position:'top', labels:{ usePointStyle:true, padding:14, font:{size:11,family:'Inter'} } },
        tooltip: { bodyFont:{size:12,family:'Inter'}, titleFont:{size:12,family:'Inter',weight:'bold'}, padding:10, cornerRadius:6 }
      },
      scales: type==='scatter'||type==='doughnut' ? (extraOpts.scales||{}) : {
        x: { grid:{color:'rgba(0,0,0,0.04)'}, ticks:{font:{size:10,family:'Inter'}, maxRotation:45} },
        y: { grid:{color:'rgba(0,0,0,0.04)'}, ticks:{font:{size:10,family:'Inter'}} },
        ...(extraOpts.scales||{})
      },
      ...extraOpts
    }
  });
}

/* ══════════════ HELPERS ══════════════ */
function aKpiCard(label, value, sub, color, icon) {
  return `
    <div class="kpi-card ${color}">
      <div class="kpi-icon ${color}">${icon}</div>
      <div class="kpi-label">${label}</div>
      <div class="kpi-value">${value}</div>
      <div class="kpi-sub">${sub}</div>
    </div>
  `;
}

function fmtInr(v)  { return '₹'+(v||0).toLocaleString('en-IN',{maximumFractionDigits:0}); }
function fmt0(v)    { return (v||0).toLocaleString('en-IN',{maximumFractionDigits:0}); }
function fmtTs(ts)  {
  const d = ts instanceof Date ? ts : new Date(ts);
  return d.toLocaleString('en-IN',{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});
}
function shortName(b) {
  return b.replace(' & Computing Hub','').replace(' Block','').replace(' Complex','');
}
function sevBadge(sev) {
  if (sev.includes('High'))   return 'badge-danger';
  if (sev.includes('Medium')) return 'badge-warning';
  return 'badge-neutral';
}
function rowData(r) {
  return {
    timestamp: r.timestamp instanceof Date ? r.timestamp.toISOString() : r.timestamp,
    building: r.building, zone: r.zone, occupancy: r.occupancy,
    temperature: r.temperature, humidity: r.humidity, hour: r.hour,
    actualPowerKw: r.actualPowerKw, predictedPowerKw: r.predictedPowerKw,
    residualKw: r.residualKw, wasteSeverity: r.wasteSeverity,
    excessKwh: r.excessKwh, excessCostInr: r.excessCostInr,
  };
}
