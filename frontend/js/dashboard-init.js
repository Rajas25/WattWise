/**
 * WattWise Dashboard Initializer
 * ================================
 * Injected into both student and admin dashboards.
 * Handles: auth guard, user info display, logout, data-source banner.
 */

'use strict';

(function initDashboard() {
  // ── Auth guard ──────────────────────────────────────────────────────────────
  if (!WW.Auth.isLoggedIn()) {
    window.location.href = '/auth.html';
    return;
  }

  // ── Inject simulated-data notice banner ───────────────────────────────────
  const notice = document.createElement('div');
  notice.id = 'sim-notice';
  notice.style.cssText = `
    position: fixed; bottom: 0; left: 0; right: 0; z-index: 1000;
    background: rgba(251,191,36,.95); color: #451a03;
    padding: .45rem 1.5rem; font-size: .78rem; font-weight: 700;
    display: flex; align-items: center; gap: .5rem;
    box-shadow: 0 -2px 12px rgba(0,0,0,.15);
  `;
  notice.innerHTML = `
    <span style="font-size:1rem">⚠️</span>
    <span>SIMULATED DATA — WattWise Demo. Campus telemetry is generated locally;
    it does not represent real energy meter readings.</span>
    <button onclick="this.parentElement.remove()" style="
      margin-left:auto;background:none;border:none;font-weight:800;
      cursor:pointer;color:#451a03;font-size:1rem;padding:0 .25rem;
    ">&times;</button>
  `;
  document.body.appendChild(notice);

  // ── Populate user info in the sidebar ────────────────────────────────────
  const name = WW.Auth.getName() || 'User';
  const role = WW.Auth.getRole() || 'student';

  const nameEls = document.querySelectorAll('[data-user-name]');
  nameEls.forEach(el => el.textContent = name);

  const roleEls = document.querySelectorAll('[data-user-role]');
  roleEls.forEach(el => {
    el.textContent = role === 'admin' ? 'Administrator' : 'Student';
  });

  const avatarEls = document.querySelectorAll('[data-user-avatar]');
  avatarEls.forEach(el => {
    el.textContent = name.charAt(0).toUpperCase();
  });

  // ── Logout buttons ────────────────────────────────────────────────────────
  document.querySelectorAll('[data-logout]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      WW.Auth.clear();
      window.location.href = '/auth.html';
    });
  });

  // ── Global error handler ──────────────────────────────────────────────────
  window.addEventListener('unhandledrejection', evt => {
    const msg = evt.reason?.message || 'An unexpected error occurred.';
    if (!msg.includes('Not authenticated')) {
      WW.showToast(msg, 'error');
    }
  });

})();

/**
 * Loads dashboard KPIs and charts from the backend API,
 * updating the existing DOM elements created by student.js / admin.js.
 * Falls back gracefully if backend is unreachable.
 */
async function loadDashboardData(building = null, days = 30) {
  try {
    const kpi = await WW.energyApi.dashboard(building, days);
    _updateKpis(kpi);
    return kpi;
  } catch (err) {
    WW.showToast('Dashboard: ' + err.message, 'warning');
    return null;
  }
}

function _updateKpis(kpi) {
  if (!kpi) return;

  const map = {
    '[data-kpi="total-readings"]' : kpi.total_readings?.toLocaleString('en-IN'),
    '[data-kpi="total-kwh"]'      : WW.formatKWh(kpi.total_kwh),
    '[data-kpi="avg-power"]'      : kpi.avg_power_kw?.toFixed(1) + ' kW',
    '[data-kpi="waste-incidents"]': kpi.waste_incidents?.toLocaleString('en-IN'),
    '[data-kpi="excess-kwh"]'     : WW.formatKWh(kpi.excess_kwh),
    '[data-kpi="excess-inr"]'     : WW.formatINR(kpi.excess_cost_inr),
    '[data-kpi="unread-alerts"]'  : kpi.unread_alerts?.toLocaleString('en-IN'),
    '[data-kpi="active-meters"]'  : kpi.active_meters?.toLocaleString('en-IN'),
  };

  Object.entries(map).forEach(([sel, val]) => {
    if (val === undefined || val === null) return;
    document.querySelectorAll(sel).forEach(el => el.textContent = val);
  });
}

/**
 * Renders a Chart.js line chart from API daily-trend data.
 * Replaces any existing chart on the canvas.
 */
async function renderDailyTrendChart(canvasId, building = null, days = 30) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === 'undefined') return;

  try {
    const data = await WW.energyApi.dailyTrend(building, days);
    const labels  = data.map(d => d.date.slice(5)); // MM-DD
    const actuals = data.map(d => d.avg_actual_kw);
    const wastes  = data.map(d => d.waste_count);

    const ctx = canvas.getContext('2d');
    if (canvas._wwChart) canvas._wwChart.destroy();

    canvas._wwChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Avg Power (kW)',
            data: actuals,
            borderColor: '#38bdf8',
            backgroundColor: 'rgba(56,189,248,0.1)',
            tension: 0.4,
            fill: true,
            pointRadius: 2,
          },
          {
            label: 'Waste Incidents',
            data: wastes,
            borderColor: '#f43f5e',
            backgroundColor: 'rgba(244,63,94,0.08)',
            tension: 0.4,
            yAxisID: 'y1',
            pointRadius: 2,
          },
        ],
      },
      options: {
        responsive: true,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { labels: { color: '#94a3b8' } },
          tooltip: { backgroundColor: '#1e293b', titleColor: '#f1f5f9', bodyColor: '#cbd5e1' },
        },
        scales: {
          x:  { ticks: { color: '#94a3b8', maxRotation: 45 }, grid: { color: 'rgba(148,163,184,.1)' } },
          y:  { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(148,163,184,.1)' }, title: { display: true, text: 'kW', color: '#94a3b8' } },
          y1: { type: 'linear', position: 'right', ticks: { color: '#f43f5e' }, grid: { drawOnChartArea: false }, title: { display: true, text: 'Incidents', color: '#f43f5e' } },
        },
      },
    });
  } catch (err) {
    console.warn('renderDailyTrendChart:', err.message);
  }
}

/**
 * Renders a Chart.js bar chart from API hourly-profile data.
 */
async function renderHourlyProfileChart(canvasId, building = null, days = 30) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === 'undefined') return;

  try {
    const data = await WW.energyApi.hourlyProfile(building, days);
    const labels  = data.map(d => `${d.hour}:00`);
    const actuals = data.map(d => d.avg_actual_kw);

    const ctx = canvas.getContext('2d');
    if (canvas._wwChart) canvas._wwChart.destroy();

    canvas._wwChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Avg Power (kW)',
          data: actuals,
          backgroundColor: actuals.map((v, i) =>
            (i >= 22 || i <= 5) ? 'rgba(244,63,94,0.6)' : 'rgba(56,189,248,0.6)'
          ),
          borderRadius: 4,
        }],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: { backgroundColor: '#1e293b', titleColor: '#f1f5f9', bodyColor: '#cbd5e1' },
        },
        scales: {
          x: { ticks: { color: '#94a3b8', maxRotation: 60 }, grid: { color: 'rgba(148,163,184,.1)' } },
          y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(148,163,184,.1)' } },
        },
      },
    });
  } catch (err) {
    console.warn('renderHourlyProfileChart:', err.message);
  }
}

/**
 * Renders a building-stats bar chart (waste cost by building).
 */
async function renderBuildingStatsChart(canvasId, days = 30) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === 'undefined') return;

  try {
    const data = await WW.energyApi.buildingStats(days);
    const labels = data.map(d => d.building);
    const costs  = data.map(d => d.excess_cost_inr);

    const ctx = canvas.getContext('2d');
    if (canvas._wwChart) canvas._wwChart.destroy();

    canvas._wwChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Estimated Waste Cost (₹)',
          data: costs,
          backgroundColor: ['rgba(244,63,94,.7)', 'rgba(251,191,36,.7)', 'rgba(56,189,248,.7)', 'rgba(167,139,250,.7)'],
          borderRadius: 6,
        }],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#1e293b',
            callbacks: {
              label: (ctx) => ` ₹${Math.round(ctx.raw).toLocaleString('en-IN')}`
            },
          },
        },
        scales: {
          x: { ticks: { color: '#94a3b8', callback: v => '₹' + Math.round(v).toLocaleString('en-IN') }, grid: { color: 'rgba(148,163,184,.1)' } },
          y: { ticks: { color: '#94a3b8' } },
        },
      },
    });
  } catch (err) {
    console.warn('renderBuildingStatsChart:', err.message);
  }
}

/**
 * Populates an anomaly/waste table (tbody) from the API.
 */
async function loadWasteTable(tbodyId, building = null, days = 30, limit = 50) {
  const tbody = document.getElementById(tbodyId);
  if (!tbody) return;

  tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#94a3b8;padding:2rem">Loading\u2026</td></tr>';

  try {
    const items = await WW.energyApi.anomalies(building, true, days, limit);
    if (!items.length) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#94a3b8;padding:2rem">No waste events found in this period.</td></tr>';
      return;
    }
    tbody.innerHTML = items.map(a => `
      <tr>
        <td>${a.timestamp?.slice(0, 16).replace('T', ' ')}</td>
        <td>${a.building}</td>
        <td>${a.zone}</td>
        <td>${a.actual_power_kw?.toFixed(1)} kW</td>
        <td>${a.residual_kw?.toFixed(1)} kW</td>
        <td>${a.occupancy}</td>
        <td><span class="badge badge-${_severityClass(a.waste_severity)}">${a.waste_severity || 'Low'}</span></td>
        <td>${WW.formatINR(a.excess_cost_inr)}</td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;color:#f43f5e;padding:2rem">${err.message}</td></tr>`;
  }
}

function _severityClass(sev) {
  if (!sev) return 'low';
  const s = sev.toLowerCase();
  if (s.includes('high')) return 'high';
  if (s.includes('medium')) return 'medium';
  return 'low';
}

/**
 * Loads recent alerts into an alerts container.
 */
async function loadAlerts(containerId, limit = 10) {
  const container = document.getElementById(containerId);
  if (!container) return;

  try {
    const alerts = await WW.energyApi.alerts(false, limit);
    if (!alerts.length) {
      container.innerHTML = '<p style="color:#94a3b8;font-size:.875rem;padding:1rem">No alerts.</p>';
      return;
    }
    container.innerHTML = alerts.map(a => `
      <div class="alert-item alert-${_severityClass(a.severity).toLowerCase()}" style="
        padding:.75rem 1rem;margin:.5rem 0;border-radius:8px;
        border-left:4px solid ${a.severity==='High'?'#f43f5e':a.severity==='Medium'?'#fbbf24':'#38bdf8'};
        background:rgba(255,255,255,.05);
      ">
        <div style="display:flex;justify-content:space-between;gap:.5rem;align-items:flex-start">
          <span style="font-size:.8rem;font-weight:600;color:#f1f5f9">${a.message}</span>
          <button onclick="WW.energyApi.markAlertRead(${a.id}).then(()=>this.closest('.alert-item').style.opacity='.4')"
            style="background:none;border:none;color:#94a3b8;cursor:pointer;font-size:.75rem;white-space:nowrap">
            Mark read
          </button>
        </div>
        <span style="font-size:.7rem;color:#64748b">${WW.timeAgo(a.created_at)} · ${a.building}</span>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = `<p style="color:#f43f5e;font-size:.875rem;padding:1rem">${err.message}</p>`;
  }
}
