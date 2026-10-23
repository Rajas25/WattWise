/* ══════════════════════════════════════════════════════
   LANDING PAGE JAVASCRIPT
   WattWise — Building Energy Waste Detective
   ══════════════════════════════════════════════════════ */
'use strict';

document.addEventListener('DOMContentLoaded', () => {

  /* ─── NAV: scroll behaviour ─────────────────────────────────────────── */
  const nav = document.getElementById('main-nav');
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 24);
    // Highlight active section
    const sections = ['how-it-works','features','analytics','about'];
    const scrollY = window.scrollY + 80;
    sections.forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      const link = document.querySelector(`.nav-link[href="#${id}"]`);
      if (!link) return;
      const { top, bottom } = el.getBoundingClientRect();
      link.classList.toggle('active', top + window.scrollY <= scrollY && bottom + window.scrollY > scrollY);
    });
  }, { passive: true });

  /* ─── Mobile hamburger ───────────────────────────────────────────────── */
  const hamburger = document.getElementById('nav-hamburger');
  const mobileMenu = document.getElementById('nav-mobile-menu');
  if (hamburger && mobileMenu) {
    hamburger.addEventListener('click', () => {
      const open = mobileMenu.classList.toggle('open');
      hamburger.classList.toggle('open', open);
      hamburger.setAttribute('aria-expanded', open);
    });
    // Close on mobile link click
    mobileMenu.querySelectorAll('a').forEach(a => {
      a.addEventListener('click', () => {
        mobileMenu.classList.remove('open');
        hamburger.classList.remove('open');
        hamburger.setAttribute('aria-expanded', 'false');
      });
    });
  }

  /* ─── Smooth scroll for anchors ─────────────────────────────────────── */
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const target = document.querySelector(a.getAttribute('href'));
      if (!target) return;
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });

  /* ─── Hero Preview Chart (mini canvas) ──────────────────────────────── */
  const canvas = document.getElementById('previewChart');
  if (canvas) drawPreviewChart(canvas);

  /* ─── Staggered animation on scroll ─────────────────────────────────── */
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('animate-in');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

  document.querySelectorAll('.problem-card, .step-card, .feature-card, .module-card, .metric-highlight')
    .forEach(el => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(24px)';
      el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
      observer.observe(el);
    });

  // CSS class to trigger animation
  const styleTag = document.createElement('style');
  styleTag.textContent = `.animate-in { opacity: 1 !important; transform: none !important; }`;
  document.head.appendChild(styleTag);
});

/* ── Mini canvas line chart for hero preview ──────────────────────────── */
function drawPreviewChart(canvas) {
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;

  // Simulated 48-hour actual vs predicted
  const pts = 48;
  const actual    = [];
  const predicted = [];
  const waste     = [];

  let rng = mulberry32(123);
  for (let i = 0; i < pts; i++) {
    const hr = i % 24;
    const base = 30 + Math.sin((hr - 6) * Math.PI / 12) * 18;
    const pred = base + (rng() - 0.5) * 4;
    let act = pred + (rng() - 0.5) * 6;
    let isWaste = false;

    // Inject some waste events
    if ((i === 2 || i === 26 || i === 35) && hr < 6) {
      act += 18 + rng() * 12;
      isWaste = true;
    }
    actual.push(+act.toFixed(1));
    predicted.push(+pred.toFixed(1));
    waste.push(isWaste ? act : null);
  }

  const maxV = Math.max(...actual, ...predicted) + 5;
  const minV = Math.min(...actual, ...predicted) - 5;

  function xPos(i) { return (i / (pts - 1)) * W; }
  function yPos(v) { return H - ((v - minV) / (maxV - minV)) * H; }

  ctx.clearRect(0, 0, W, H);

  // Fill area under predicted
  ctx.beginPath();
  ctx.moveTo(xPos(0), yPos(predicted[0]));
  for (let i = 1; i < pts; i++) ctx.lineTo(xPos(i), yPos(predicted[i]));
  ctx.lineTo(W, H); ctx.lineTo(0, H); ctx.closePath();
  ctx.fillStyle = 'rgba(168,218,220,0.12)';
  ctx.fill();

  // Predicted line
  ctx.beginPath();
  ctx.strokeStyle = '#457B9D';
  ctx.lineWidth = 1.5;
  ctx.setLineDash([5, 3]);
  ctx.moveTo(xPos(0), yPos(predicted[0]));
  for (let i = 1; i < pts; i++) ctx.lineTo(xPos(i), yPos(predicted[i]));
  ctx.stroke();
  ctx.setLineDash([]);

  // Actual line
  ctx.beginPath();
  ctx.strokeStyle = '#1D3557';
  ctx.lineWidth = 2;
  ctx.moveTo(xPos(0), yPos(actual[0]));
  for (let i = 1; i < pts; i++) ctx.lineTo(xPos(i), yPos(actual[i]));
  ctx.stroke();

  // Waste markers
  waste.forEach((v, i) => {
    if (v === null) return;
    ctx.beginPath();
    ctx.arc(xPos(i), yPos(v), 5, 0, Math.PI * 2);
    ctx.fillStyle = '#DC2626';
    ctx.fill();
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 1.5;
    ctx.stroke();
  });
}

function mulberry32(seed) {
  return function() {
    seed |= 0; seed = seed + 0x6D2B79F5 | 0;
    let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
