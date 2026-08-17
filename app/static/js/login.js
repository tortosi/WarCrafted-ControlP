document.getElementById('login-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const errorEl = document.getElementById('login-error');
  errorEl.classList.add('hidden');

  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value;

  try {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      errorEl.textContent = data.detail || 'No se pudo iniciar sesion.';
      errorEl.classList.remove('hidden');
      return;
    }

    window.location.href = '/dashboard';
  } catch (err) {
    errorEl.textContent = 'Error de conexion con el servidor.';
    errorEl.classList.remove('hidden');
  }
});
