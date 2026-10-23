/**
 * WattWise API Client
 * ====================
 * Centralized JavaScript module for all communication with the FastAPI backend.
 * All functions return Promises and throw on non-2xx responses.
 *
 * Usage:
 *   import { api } from './api.js';          (if using modules)
 *   -- or include before other scripts --
 *   const token = localStorage.getItem('ww_token');
 */

'use strict';

/* ═══════════════════════════════════════════════════════════════
   CONFIGURATION
   ═══════════════════════════════════════════════════════════════ */

// When frontend is served by FastAPI (same origin) use relative URLs.
// When opened as file:// in dev use localhost:8000.
const API_BASE = (() => {
  if (window.location.protocol === 'file:') return 'http://localhost:8000';
  return '';   // same origin — no prefix needed
})();

const TOKEN_KEY    = 'ww_token';
const ROLE_KEY     = 'ww_role';
const NAME_KEY     = 'ww_name';

/* ═══════════════════════════════════════════════════════════════
   TOKEN HELPERS
   ═══════════════════════════════════════════════════════════════ */

const Auth = {
  getToken  : ()       => localStorage.getItem(TOKEN_KEY),
  getRole   : ()       => localStorage.getItem(ROLE_KEY),
  getName   : ()       => localStorage.getItem(NAME_KEY),
  isLoggedIn: ()       => !!localStorage.getItem(TOKEN_KEY),
  isAdmin   : ()       => localStorage.getItem(ROLE_KEY) === 'admin',
  isStudent : ()       => localStorage.getItem(ROLE_KEY) === 'student',

  save(token, role, fullName) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(ROLE_KEY,  role);
    localStorage.setItem(NAME_KEY,  fullName);
  },

  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ROLE_KEY);
    localStorage.removeItem(NAME_KEY);
  },

  /** Redirect to auth page if not logged in */
  requireAuth(expectedRole = null) {
    if (!this.isLoggedIn()) {
      window.location.href = '/auth.html';
      return false;
    }
    if (expectedRole && this.getRole() !== expectedRole) {
      alert(`This page requires ${expectedRole} access. You are logged in as ${this.getRole()}.`);
      window.location.href = this.getRole() === 'admin'
        ? '/admin-dashboard.html'
        : '/student-dashboard.html';
      return false;
    }
    return true;
  },
};

/* ═══════════════════════════════════════════════════════════════
   CORE HTTP WRAPPER
   ═══════════════════════════════════════════════════════════════ */

async function request(method, path, body = null, requireToken = true) {
  const url     = `${API_BASE}${path}`;
  const headers = { 'Content-Type': 'application/json' };

  if (requireToken) {
    const token = Auth.getToken();
    if (!token) {
      Auth.clear();
      window.location.href = '/auth.html';
      throw new Error('Not authenticated');
    }
    headers['Authorization'] = `Bearer ${token}`;
  }

  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(url, opts);

  if (res.status === 401) {
    Auth.clear();
    window.location.href = '/auth.html';
    throw new Error('Session expired. Please log in again.');
  }

  if (res.status === 403) {
    throw new Error('Access denied — insufficient permissions.');
  }

  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try { const d = await res.json(); msg = d.detail || msg; } catch (_) {}
    throw new Error(msg);
  }

  if (res.status === 204) return null;
  return res.json();
}

const get    = (path, qp = {}) => {
  const qs = new URLSearchParams(qp).toString();
  return request('GET', qs ? `${path}?${qs}` : path);
};
const post   = (path, body, auth = true) => request('POST', path, body, auth);
const patch  = (path, body)              => request('PATCH', path, body);
const del    = (path)                    => request('DELETE', path, null);

/* ═══════════════════════════════════════════════════════════════
   AUTHENTICATION ENDPOINTS
   ═══════════════════════════════════════════════════════════════ */

const authApi = {
  async login(email, password) {
    const data = await post('/api/auth/token', { email, password }, false);
    Auth.save(data.access_token, data.role, data.full_name);
    return data;
  },

  async register(email, password, fullName) {
    return post('/api/auth/register', { email, password, full_name: fullName }, false);
  },

  async me() {
    return get('/api/auth/me');
  },

  logout() {
    Auth.clear();
    window.location.href = '/auth.html';
  },
};

/* ═══════════════════════════════════════════════════════════════
   ENERGY ENDPOINTS
   ═══════════════════════════════════════════════════════════════ */

const energyApi = {
  health        : ()               => get('/api/health'),
  buildings     : ()               => get('/api/energy/buildings'),
  dashboard     : (building, days) => get('/api/energy/dashboard', { building, days }),
  buildingStats : (days = 30)      => get('/api/energy/buildings/stats', { days }),
  hourlyProfile : (building, days) => get('/api/energy/hourly-profile', { building, days }),
  dailyTrend    : (building, days) => get('/api/energy/daily-trend', { building, days }),
  readings      : (building, days, limit) => get('/api/energy/readings', { building, days, limit }),
  anomalies     : (building, isWaste, days, limit) =>
    get('/api/energy/anomalies', { building, is_waste: isWaste, days, limit }),
  alerts        : (unreadOnly = false, limit = 50) =>
    get('/api/energy/alerts', { unread_only: unreadOnly, limit }),
  markAlertRead : (id) => post(`/api/energy/alerts/${id}/read`),
  submitReading : (body)           => post('/api/energy/readings', body),
};

/* ═══════════════════════════════════════════════════════════════
   ML ENDPOINTS
   ═══════════════════════════════════════════════════════════════ */

const mlApi = {
  info         : ()             => get('/api/ml/info'),
  predict      : (body)         => post('/api/ml/predict', body),
  analyze      : (building, days) =>
    post(`/api/ml/analyze?building=${encodeURIComponent(building || '')}&days=${days}`),
};

/* ═══════════════════════════════════════════════════════════════
   ADMIN ENDPOINTS
   ═══════════════════════════════════════════════════════════════ */

const adminApi = {
  dashboard       : ()         => get('/api/admin/dashboard'),
  listMeters      : ()         => get('/api/admin/meters'),
  ingestionHealth : ()         => get('/api/admin/ingestion/health'),
  listUsers       : ()         => get('/api/users/'),
  createUser      : (body)     => post('/api/users/', body),
  updateUser      : (id, body) => patch(`/api/users/${id}`, body),
  deleteUser      : (id)       => del(`/api/users/${id}`),
  acknowledgeAnomaly: (id)     => post(`/api/energy/anomalies/${id}/acknowledge`),
};

/* ═══════════════════════════════════════════════════════════════
   UTILITY
   ═══════════════════════════════════════════════════════════════ */

/**
 * Shows a toast notification in the top-right corner.
 * Creates the container element if it doesn't exist.
 */
function showToast(message, type = 'info', duration = 4000) {
  let container = document.getElementById('ww-toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'ww-toast-container';
    container.style.cssText =
      'position:fixed;top:1rem;right:1rem;z-index:9999;display:flex;flex-direction:column;gap:.5rem;';
    document.body.appendChild(container);
  }
  const colors = {
    success: '#10b981', error: '#f43f5e', warning: '#fbbf24', info: '#38bdf8'
  };
  const toast = document.createElement('div');
  toast.style.cssText = `
    background:${colors[type] || colors.info};color:#0f172a;
    padding:.75rem 1.25rem;border-radius:10px;font-weight:600;
    font-size:.875rem;box-shadow:0 4px 20px rgba(0,0,0,.3);
    animation:slideIn .25s ease;max-width:360px;
  `;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), duration);
}

/**
 * Format INR currency: ₹1,23,456
 */
function formatINR(amount) {
  return '₹' + Math.round(amount).toLocaleString('en-IN');
}

/**
 * Format kWh with comma separator
 */
function formatKWh(val) {
  return (Math.round(val * 10) / 10).toLocaleString('en-IN') + ' kWh';
}

/**
 * Short relative time: "2h ago", "3d ago"
 */
function timeAgo(isoStr) {
  if (!isoStr) return 'N/A';
  const diff = (Date.now() - new Date(isoStr).getTime()) / 1000;
  if (diff < 60)     return `${Math.round(diff)}s ago`;
  if (diff < 3600)   return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400)  return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86400)}d ago`;
}

// ── CSS animation for toast (injected once) ──────────────────────────────────
(function injectToastCSS() {
  if (document.getElementById('ww-toast-css')) return;
  const s = document.createElement('style');
  s.id = 'ww-toast-css';
  s.textContent = `@keyframes slideIn{from{opacity:0;transform:translateX(40px)}to{opacity:1;transform:none}}`;
  document.head.appendChild(s);
})();

// ── Exports (works with both module and script tag) ───────────────────────────
if (typeof window !== 'undefined') {
  window.WW = { Auth, authApi, energyApi, mlApi, adminApi, showToast, formatINR, formatKWh, timeAgo };
}
