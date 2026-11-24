const passwordToggle = document.querySelector('[data-password-toggle]');
const passwordInput = document.getElementById(passwordToggle.getAttribute('aria-controls'));

passwordInput.spellcheck = false;
passwordInput.setAttribute('autocapitalize', 'none');
passwordInput.setAttribute('autocorrect', 'off');

passwordToggle.addEventListener('click', () => {
  const showPassword = passwordInput.type === 'password';
  passwordInput.type = showPassword ? 'text' : 'password';
  passwordToggle.setAttribute('aria-label', showPassword ? 'Ocultar senha' : 'Mostrar senha');
});

passwordToggle.hidden = false;
