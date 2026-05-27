/* ─────────────────────────────────────────────────────
   KERALA LOTTERY ANALYZER — main.js
───────────────────────────────────────────────────── */

// ── LOTTERY BALL PARTICLE CANVAS ─────────────────────
const canvas  = document.getElementById('bg-canvas');
const ctx     = canvas.getContext('2d');
let particles = [];
let animId;

function resize() {
  canvas.width  = window.innerWidth;
  canvas.height = window.innerHeight;
}

class Particle {
  constructor() { this.reset(); }
  reset() {
    this.x     = Math.random() * canvas.width;
    this.y     = canvas.height + 60;
    this.r     = 10 + Math.random() * 22;
    this.vx    = (Math.random() - 0.5) * 0.5;
    this.vy    = -(0.3 + Math.random() * 0.7);
    this.alpha = 0.04 + Math.random() * 0.1;
    this.n     = Math.floor(Math.random() * 60) + 1;
    this.hue   = 40 + Math.random() * 20;  // gold range
    this.spin  = (Math.random() - 0.5) * 0.02;
    this.angle = Math.random() * Math.PI * 2;
  }
  update() {
    this.x     += this.vx;
    this.y     += this.vy;
    this.angle += this.spin;
    if (this.y < -60) this.reset();
  }
  draw() {
    ctx.save();
    ctx.globalAlpha = this.alpha;
    ctx.translate(this.x, this.y);
    ctx.rotate(this.angle);

    // Ball body
    const grad = ctx.createRadialGradient(-this.r * 0.3, -this.r * 0.3, 0, 0, 0, this.r);
    grad.addColorStop(0, `hsla(${this.hue + 20}, 100%, 90%, 1)`);
    grad.addColorStop(0.5, `hsla(${this.hue}, 90%, 60%, 1)`);
    grad.addColorStop(1, `hsla(${this.hue - 10}, 80%, 30%, 1)`);

    ctx.beginPath();
    ctx.arc(0, 0, this.r, 0, Math.PI * 2);
    ctx.fillStyle = grad;
    ctx.fill();

    // Shine
    ctx.beginPath();
    ctx.arc(-this.r * 0.28, -this.r * 0.28, this.r * 0.28, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(255,255,255,0.4)';
    ctx.fill();

    // Number
    ctx.fillStyle = `rgba(50, 25, 0, 0.75)`;
    ctx.font      = `bold ${this.r * 0.85}px Cinzel, serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(this.n, 0, 1);

    ctx.restore();
  }
}

function initParticles() {
  const count = Math.min(30, Math.floor(window.innerWidth / 45));
  particles   = [];
  for (let i = 0; i < count; i++) {
    const p = new Particle();
    p.y = Math.random() * canvas.height;  // Spread on load
    particles.push(p);
  }
}

function animLoop() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  particles.forEach(p => { p.update(); p.draw(); });
  animId = requestAnimationFrame(animLoop);
}

resize();
initParticles();
animLoop();

window.addEventListener('resize', () => {
  resize();
  initParticles();
});

// ── HAMBURGER MENU ────────────────────────────────────
const hamburger  = document.getElementById('hamburger');
const navLinks   = document.getElementById('nav-links');

if (hamburger && navLinks) {
  hamburger.addEventListener('click', () => {
    navLinks.classList.toggle('open');
    const spans = hamburger.querySelectorAll('span');
    spans[0].style.transform = navLinks.classList.contains('open') ? 'rotate(45deg) translateY(7px)'  : '';
    spans[1].style.opacity   = navLinks.classList.contains('open') ? '0' : '1';
    spans[2].style.transform = navLinks.classList.contains('open') ? 'rotate(-45deg) translateY(-7px)' : '';
  });
}

// ── 3D TILT EFFECT ────────────────────────────────────
function applyTilt(el) {
  el.addEventListener('mousemove', (e) => {
    const rect   = el.getBoundingClientRect();
    const cx     = rect.left + rect.width  / 2;
    const cy     = rect.top  + rect.height / 2;
    const dx     = (e.clientX - cx) / (rect.width  / 2);
    const dy     = (e.clientY - cy) / (rect.height / 2);
    const rotX   = dy * -8;
    const rotY   = dx *  8;
    el.style.transform = `perspective(800px) rotateX(${rotX}deg) rotateY(${rotY}deg) translateZ(8px)`;
  });
  el.addEventListener('mouseleave', () => {
    el.style.transform = '';
    el.style.transition = 'transform 0.5s cubic-bezier(0.25,0.8,0.25,1)';
    setTimeout(() => { el.style.transition = ''; }, 500);
  });
}

document.querySelectorAll('.glass-card, .action-card, .predict-card, .stat-card').forEach(applyTilt);

// ── AUTO-DISMISS FLASH MESSAGES ───────────────────────
document.querySelectorAll('.flash').forEach(f => {
  f.addEventListener('click', () => f.remove());
  setTimeout(() => f.remove(), 5000);
});

// ── ANIMATE FREQ BARS ─────────────────────────────────
const bars = document.querySelectorAll('.freq-bar-fill');
if (bars.length) {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        const target = e.target.dataset.width;
        e.target.style.width = target + '%';
        observer.unobserve(e.target);
      }
    });
  }, { threshold: 0.2 });
  bars.forEach(b => { b.style.width = '0%'; observer.observe(b); });
}

// ── NUMBER BADGE HOVER SOUND (optional visual pulse) ──
document.querySelectorAll('.number-badge').forEach(b => {
  b.addEventListener('mouseenter', () => {
    b.style.transform = 'scale(1.25) rotate(10deg)';
  });
  b.addEventListener('mouseleave', () => {
    b.style.transform = '';
  });
});

// ── HERO ORB COUNTER ──────────────────────────────────
const orbNum = document.getElementById('orb-number');
if (orbNum) {
  const target = parseInt(orbNum.dataset.target) || 0;
  let current  = 0;
  const step   = Math.ceil(target / 60);
  const timer  = setInterval(() => {
    current = Math.min(current + step, target);
    orbNum.textContent = current;
    if (current >= target) clearInterval(timer);
  }, 30);
}

// ── SMOOTH SCROLL REVEAL ──────────────────────────────
const fadeEls = document.querySelectorAll('.fade-in');
if ('IntersectionObserver' in window) {
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.style.animationPlayState = 'running';
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.1 });
  fadeEls.forEach(el => {
    el.style.animationPlayState = 'paused';
    io.observe(el);
  });
}

// ── COPY NUMBERS TO CLIPBOARD ─────────────────────────
document.querySelectorAll('[data-copy]').forEach(btn => {
  btn.addEventListener('click', () => {
    const text = btn.dataset.copy;
    navigator.clipboard.writeText(text).then(() => {
      const orig = btn.textContent;
      btn.textContent = '✓ Copied!';
      btn.style.color = '#00f564';
      setTimeout(() => {
        btn.textContent = orig;
        btn.style.color = '';
      }, 2000);
    });
  });
});

// ── ACTIVE NAV LINK ───────────────────────────────────
const currentPath = window.location.pathname;
document.querySelectorAll('.nav-links a').forEach(a => {
  if (a.getAttribute('href') === currentPath) a.classList.add('active');
});
