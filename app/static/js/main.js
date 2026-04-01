/*
  JS global de UI:
  1) auto-cierre de mensajes flash,
  2) animaciones de entrada (reveal),
  3) ayudas de login (relleno rapido + toggle de password).
*/

(() => {
  // ------------------------------
  // 1) Auto-cierre de alerts
  // ------------------------------
  const alerts = document.querySelectorAll('.alert');
  if (alerts.length > 0) {
    window.setTimeout(() => {
      alerts.forEach((alertEl) => {
        alertEl.style.transition = 'opacity 0.35s ease, transform 0.35s ease';
        alertEl.style.opacity = '0';
        alertEl.style.transform = 'translateY(-4px)';
        window.setTimeout(() => alertEl.remove(), 360);
      });
    }, 5200);
  }

  // ------------------------------
  // 2) Efecto reveal al entrar en viewport
  // ------------------------------
  const revealTargets = Array.from(document.querySelectorAll('.page > *, .panel, .kpi, .rel-card, .tc'));
  if (revealTargets.length === 0) return;

  revealTargets.forEach((el, idx) => {
    el.classList.add('reveal');
    el.style.transitionDelay = `${Math.min(idx * 28, 260)}ms`;
  });

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('reveal-on');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.08 }
  );

  revealTargets.forEach((el) => observer.observe(el));
})();

(() => {
  // ------------------------------
  // 3) Helpers de login
  // ------------------------------
  const emailInput = document.querySelector('#email');
  const passInput = document.querySelector('#password');
  if (!emailInput || !passInput) return;

  // Botones de acceso rapido por rol demo.
  document.querySelectorAll('.js-fill-user').forEach((btn) => {
    btn.addEventListener('click', () => {
      emailInput.value = btn.dataset.email || '';
      passInput.value = 'servicia2026';
      passInput.focus();
    });
  });

  // Mostrar/ocultar password para evitar errores de captura.
  const toggleBtn = document.querySelector('.js-toggle-pass');
  if (!toggleBtn) return;

  toggleBtn.addEventListener('click', () => {
    const isHidden = passInput.type === 'password';
    passInput.type = isHidden ? 'text' : 'password';
    toggleBtn.textContent = isHidden ? 'Ocultar' : 'Mostrar';
  });
})();
