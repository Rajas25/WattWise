/**
 * WattWise — Shared Simulated Data Store
 * Building Energy Waste Detective
 * 
 * ⚠️ ACADEMIC SIMULATION NOTICE:
 * All data below is synthetically generated for demonstration.
 * It does NOT represent verified readings from a real campus.
 * Ground-truth labels (isAnomaly) are for evaluation only — never used as features.
 */

'use strict';

/* ══════════════════════════════════════════════════════
   CONSTANTS (matching Python constants in utils.py)
   ══════════════════════════════════════════════════════ */
const WW = {
  TARIFF_INR_PER_KWH: 8.50,
  DEFAULT_RESIDUAL_THRESHOLD: 10.0,
  DEFAULT_OCCUPANCY_THRESHOLD: 5,
  TOTAL_RECORDS: 8640,
  DATE_START: '2026-01-01',
  DATE_END: '2026-03-31',

  BUILDINGS: [
    'Academic Block A',
    'Library & Computing Hub',
    'Science Complex',
    'Administrative Block'
  ],

  ZONES: {
    'Academic Block A': ['Lecture Halls & Classrooms', 'Faculty Offices', 'Student Lounge'],
    'Library & Computing Hub': ['Central Study Area', 'Server & Data Room', 'Reading Galleries'],
    'Science Complex': ['Chemistry & Bio Labs', 'Equipment Storage', 'Research Offices'],
    'Administrative Block': ['Administration Offices', 'Conference Rooms', 'Reception & Lobby']
  },

  // Regression benchmark results (from models/model_comparison.csv)
  REGRESSION_METRICS: [
    { model: 'Linear Regression',     mae: 3.257, rmse: 5.644, r2: 0.8922, mape: 13.97, isBest: false },
    { model: 'Random Forest',          mae: 2.128, rmse: 5.409, r2: 0.9010, mape: 10.36, isBest: false },
    { model: 'XGBoost (Champion)',     mae: 2.106, rmse: 5.330, r2: 0.9038, mape: 10.07, isBest: true  },
  ],

  // Anomaly detection results (from models/model_metadata.json)
  DETECTION_METRICS: {
    contextual: { precision: 0.9318, recall: 1.0000, f1: 0.9647, accuracy: 0.9983,
                  tp: 41, fp: 3, tn: 1684, fn: 0 },
    isoForest:  { precision: 0.0128, recall: 0.0244, f1: 0.0168, accuracy: 0.9323,
                  tp: 1, fp: 77, tn: 1610, fn: 40 }
  },

  // Default detection thresholds
  THRESHOLDS: { residual: 10.0, occupancy: 5, tariff: 8.50 },

  // Feature columns used by the ML model
  FEATURES: ['building','zone','occupancy','temperature','humidity','hour',
              'day_of_week','is_weekend','is_business_hours','cooling_need','hour_sin','hour_cos'],
};

/* ══════════════════════════════════════════════════════
   SYNTHETIC TELEMETRY DATA GENERATOR
   Matches the physics of generate_data.py
   ══════════════════════════════════════════════════════ */

function generateTelemetry(days = 90, seed = 42) {
  const rng = mulberry32(seed);
  const records = [];

  const buildingBaseload = {
    'Academic Block A':       { base: 25, occ: 0.8, hvac: 1.2 },
    'Library & Computing Hub':{ base: 38, occ: 0.4, hvac: 0.8 },
    'Science Complex':        { base: 32, occ: 1.0, hvac: 1.5 },
    'Administrative Block':   { base: 18, occ: 0.6, hvac: 0.7 },
  };

  const anomalyConfig = [
    // Empty rooms, lights/AC left on overnight weekends
    { type: 'Empty Room After Hours', building: 'Academic Block A',
      zone: 'Lecture Halls & Classrooms', hourRange:[22,5], dowRange:[0,6],
      maxOcc:2, excessMin:12, excessMax:28, count:15 },
    { type: 'Night HVAC Running',     building: 'Science Complex',
      zone: 'Chemistry & Bio Labs', hourRange:[0,6], dowRange:[0,6],
      maxOcc:1, excessMin:15, excessMax:35, count:12 },
    { type: 'Weekend Lab Equipment',  building: 'Science Complex',
      zone: 'Chemistry & Bio Labs', hourRange:[8,18], dowRange:[5,6],
      maxOcc:3, excessMin:10, excessMax:20, count:8 },
    { type: 'Idle Server Room Spike', building: 'Library & Computing Hub',
      zone: 'Server & Data Room', hourRange:[2,6], dowRange:[0,6],
      maxOcc:0, excessMin:18, excessMax:40, count:6 },
  ];

  const anomalySet = new Set();
  anomalyConfig.forEach(cfg => {
    for (let i = 0; i < cfg.count; i++) {
      const dayOffset = Math.floor(rng() * days);
      const hr = cfg.hourRange[0] + Math.floor(rng() * (cfg.hourRange[1] - cfg.hourRange[0] + 1)) % 24;
      const dow = cfg.dowRange[0] + Math.floor(rng() * (cfg.dowRange[1] - cfg.dowRange[0] + 1)) % 7;
      anomalySet.add(`${cfg.building}|${cfg.zone}|${dayOffset}|${hr}`);
    }
  });

  const startDate = new Date('2026-01-01T00:00:00');

  for (let day = 0; day < days; day++) {
    const date = new Date(startDate.getTime() + day * 86400000);
    const dow = date.getDay(); // 0=Sun,6=Sat
    const isWeekend = (dow === 0 || dow === 6) ? 1 : 0;

    // Seasonal temperature (Jan cold, Mar warm in India)
    const baseTempC = 18 + (day / days) * 14 + (rng() - 0.5) * 6;
    const humidity = 45 + rng() * 40;

    for (let hour = 0; hour < 24; hour++) {
      const temp = baseTempC + Math.sin((hour - 14) * Math.PI / 12) * 5 + (rng() - 0.5) * 2;
      const isBusinessHrs = (dow > 0 && dow < 6 && hour >= 8 && hour <= 18) ? 1 : 0;
      const coolingNeed = Math.max(0, temp - 24);
      const hourSin = Math.sin(2 * Math.PI * hour / 24);
      const hourCos = Math.cos(2 * Math.PI * hour / 24);

      WW.BUILDINGS.forEach(building => {
        const zones = WW.ZONES[building];
        const cfg = buildingBaseload[building];

        zones.forEach(zone => {
          // Simulate occupancy
          let maxOcc = isWeekend ? 20 : (isBusinessHrs ? 80 : 5);
          if (zone.includes('Server') || zone.includes('Reception')) maxOcc = Math.min(maxOcc, 15);
          const occupancy = Math.floor(rng() * maxOcc);

          // Predicted power (what model would predict)
          const predicted = cfg.base
            + occupancy * cfg.occ
            + coolingNeed * cfg.hvac
            + (isBusinessHrs ? 8 : 0)
            + (rng() - 0.5) * 4;

          // Check anomaly
          const key = `${building}|${zone}|${day}|${hour}`;
          let isAnomaly = 0, anomalyType = 'Normal', excessKw = 0;

          const matchCfg = anomalyConfig.find(c =>
            c.building === building && c.zone === zone &&
            hour >= c.hourRange[0] && occupancy <= c.maxOcc
          );

          if (matchCfg && rng() < (matchCfg.count / (days * 0.15))) {
            isAnomaly = 1;
            anomalyType = matchCfg.type;
            excessKw = matchCfg.excessMin + rng() * (matchCfg.excessMax - matchCfg.excessMin);
          }

          const actual = Math.max(2, predicted + (isAnomaly ? excessKw : 0) + (rng() - 0.5) * 2);
          const residual = actual - predicted;

          // Contextual detection (matches detect_contextual_waste in utils.py)
          const residualThresh = WW.THRESHOLDS.residual;
          const occThresh = WW.THRESHOLDS.occupancy;
          const isWasteDetected = (residual >= residualThresh && occupancy <= occThresh) ? 1 : 0;
          const severity = !isWasteDetected ? 'Normal'
            : residual < 1.5 * residualThresh ? 'Low Waste'
            : residual < 2.5 * residualThresh ? 'Medium Waste'
            : 'High Waste';
          const excessKwh = isWasteDetected ? residual : 0;
          const excessCostInr = +(excessKwh * WW.TARIFF_INR_PER_KWH).toFixed(2);

          records.push({
            timestamp: new Date(date.getTime() + hour * 3600000),
            building, zone, occupancy,
            temperature: +temp.toFixed(1),
            humidity: +humidity.toFixed(1),
            hour, dayOfWeek: dow, isWeekend, isBusinessHours: isBusinessHrs,
            coolingNeed: +coolingNeed.toFixed(2),
            hourSin: +hourSin.toFixed(4), hourCos: +hourCos.toFixed(4),
            actualPowerKw: +actual.toFixed(2),
            predictedPowerKw: +predicted.toFixed(2),
            residualKw: +residual.toFixed(2),
            isAnomaly, anomalyType,
            isWasteDetected, wasteSeverity: severity,
            excessKwh: +excessKwh.toFixed(3),
            excessCostInr,
          });
        });
      });
    }
  }

  return records;
}

// Mulberry32 seeded PRNG (deterministic)
function mulberry32(seed) {
  return function() {
    seed |= 0; seed = seed + 0x6D2B79F5 | 0;
    let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

/* ══════════════════════════════════════════════════════
   GLOBAL DATA STORE — loaded once, cached
   ══════════════════════════════════════════════════════ */
class WattWiseStore {
  constructor() {
    this._raw = null;
    this._filters = {
      building: 'All Buildings',
      zone:     'All Zones',
      dateFrom: '2026-01-01',
      dateTo:   '2026-03-31',
      minResidual: 0,
      maxOccupancy: 999,
    };
    this._listeners = {};
  }

  load() {
    if (!this._raw) {
      console.log('[WattWise] Generating synthetic telemetry (90 days)...');
      this._raw = generateTelemetry(90, 42);
      console.log(`[WattWise] Generated ${this._raw.length} records`);
    }
    return this;
  }

  get raw() { return this._raw || []; }

  get filtered() {
    const f = this._filters;
    return this.raw.filter(r => {
      if (f.building !== 'All Buildings' && r.building !== f.building) return false;
      if (f.zone     !== 'All Zones'     && r.zone     !== f.zone)     return false;
      const ts = r.timestamp.toISOString().slice(0,10);
      if (ts < f.dateFrom || ts > f.dateTo) return false;
      return true;
    });
  }

  get wasted() {
    return this.filtered.filter(r => r.isWasteDetected === 1);
  }

  setFilter(key, val) {
    this._filters[key] = val;
    this._emit('filter');
  }

  resetFilters() {
    this._filters = {
      building: 'All Buildings',
      zone: 'All Zones',
      dateFrom: '2026-01-01',
      dateTo: '2026-03-31',
      minResidual: 0,
      maxOccupancy: 999,
    };
    this._emit('filter');
  }

  // ── Aggregations ──
  summaryKPIs(data = null) {
    const d = data || this.filtered;
    const totalKwh = d.reduce((s, r) => s + r.actualPowerKw, 0);
    const wasteKwh = d.reduce((s, r) => s + r.excessKwh, 0);
    const wasteCostInr = d.reduce((s, r) => s + r.excessCostInr, 0);
    const incidents = d.filter(r => r.isWasteDetected === 1).length;
    const avgPower = d.length ? totalKwh / d.length : 0;
    return { totalKwh, wasteKwh, wasteCostInr, incidents, avgPower, count: d.length };
  }

  buildingBreakdown(data = null) {
    const d = data || this.filtered;
    return WW.BUILDINGS.map(b => {
      const bd = d.filter(r => r.building === b);
      const kpis = this.summaryKPIs(bd);
      return { building: b, ...kpis };
    });
  }

  hourlyProfile(data = null) {
    const d = data || this.filtered;
    const byHour = Array.from({length: 24}, (_, h) => {
      const hrs = d.filter(r => r.hour === h);
      const avg = hrs.length ? hrs.reduce((s,r)=>s+r.actualPowerKw,0)/hrs.length : 0;
      const pred = hrs.length ? hrs.reduce((s,r)=>s+r.predictedPowerKw,0)/hrs.length : 0;
      return { hour: h, avgActual: +avg.toFixed(2), avgPredicted: +pred.toFixed(2) };
    });
    return byHour;
  }

  dailyTimeSeries(data = null) {
    const d = data || this.filtered;
    const byDay = {};
    d.forEach(r => {
      const key = r.timestamp.toISOString().slice(0,10);
      if (!byDay[key]) byDay[key] = { date: key, actual: 0, predicted: 0, excess: 0, incidents: 0, count: 0 };
      byDay[key].actual += r.actualPowerKw;
      byDay[key].predicted += r.predictedPowerKw;
      byDay[key].excess += r.excessKwh;
      byDay[key].incidents += r.isWasteDetected;
      byDay[key].count += 1;
    });
    return Object.values(byDay).sort((a,b)=>a.date.localeCompare(b.date));
  }

  weekdayVsWeekend(data = null) {
    const d = data || this.filtered;
    const wd = d.filter(r => !r.isWeekend);
    const we = d.filter(r => r.isWeekend);
    const avgWd = wd.length ? wd.reduce((s,r)=>s+r.actualPowerKw,0)/wd.length : 0;
    const avgWe = we.length ? we.reduce((s,r)=>s+r.actualPowerKw,0)/we.length : 0;
    return { weekday: +avgWd.toFixed(2), weekend: +avgWe.toFixed(2) };
  }

  // Get available zones for a building filter
  availableZones(building) {
    if (building === 'All Buildings') return ['All Zones'];
    return ['All Zones', ...(WW.ZONES[building] || [])];
  }

  // On / emit
  on(event, fn) {
    if (!this._listeners[event]) this._listeners[event] = [];
    this._listeners[event].push(fn);
  }
  _emit(event) {
    (this._listeners[event] || []).forEach(fn => fn());
  }
}

/* Singleton store */
const store = new WattWiseStore();

/* ══════════════════════════════════════════════════════
   CHART UTILITIES (Chart.js helpers)
   ══════════════════════════════════════════════════════ */
const ChartUtils = {
  studentColors: {
    primary:   '#1D3557',
    secondary: '#457B9D',
    accent:    '#A8DADC',
    danger:    '#DC2626',
    success:   '#059669',
    warning:   '#D97706',
  },
  adminColors: {
    primary:   '#5B21B6',
    secondary: '#7C3AED',
    accent:    '#FDE68A',
    danger:    '#DC2626',
    success:   '#059669',
    warning:   '#D97706',
  },
  defaults: {
    font: { family: 'Inter, sans-serif', size: 12 },
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true, position: 'top', labels: { usePointStyle: true, padding: 16, font: { size: 11, family: 'Inter, sans-serif' } } },
      tooltip: { bodyFont: { size: 12, family: 'Inter, sans-serif' }, titleFont: { size: 12, family: 'Inter, sans-serif', weight: 'bold' }, padding: 10, cornerRadius: 6 },
    },
    scales: {
      x: { grid: { color: 'rgba(0,0,0,0.04)' }, ticks: { font: { size: 11, family: 'Inter, sans-serif' } } },
      y: { grid: { color: 'rgba(0,0,0,0.04)' }, ticks: { font: { size: 11, family: 'Inter, sans-serif' } } },
    }
  },

  formatInr(val) { return '₹' + val.toLocaleString('en-IN', {minimumFractionDigits: 0, maximumFractionDigits: 0}); },
  formatKwh(val) { return val.toLocaleString('en-IN', {maximumFractionDigits: 1}) + ' kWh'; },
  formatKw(val)  { return val.toFixed(2) + ' kW'; },
};

/* ══════════════════════════════════════════════════════
   EXPORT
   ══════════════════════════════════════════════════════ */
window.WW      = WW;
window.store   = store;
window.ChartUtils = ChartUtils;
