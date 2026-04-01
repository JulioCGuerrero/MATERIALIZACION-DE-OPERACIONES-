(() => {
  const alerts = document.querySelectorAll('.alert');
  if (alerts.length === 0) return;

  window.setTimeout(() => {
    alerts.forEach((alertEl) => {
      alertEl.style.transition = 'opacity 0.4s ease';
      alertEl.style.opacity = '0';
      window.setTimeout(() => alertEl.remove(), 420);
    });
  }, 5500);
})();
