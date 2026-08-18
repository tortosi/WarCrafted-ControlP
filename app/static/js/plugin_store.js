const feedbackEl = document.getElementById('action-feedback');
const emptyStateEl = document.getElementById('empty-state');
const gridEl = document.getElementById('catalog-grid');
const tokenStatusEl = document.getElementById('token-status');
const tokenModal = document.getElementById('token-modal');
const tokenInput = document.getElementById('token-input');
const tokenModalError = document.getElementById('token-modal-error');
let feedbackTimeout = null;

function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return String(text).replace(/[&<>"']/g, (char) => map[char]);
}

function showFeedback(message, isError) {
  clearTimeout(feedbackTimeout);
  feedbackEl.textContent = message;
  feedbackEl.classList.remove('hidden');
  feedbackEl.className = isError
    ? 'text-sm rounded-lg px-4 py-3 whitespace-pre-wrap bg-red-50 text-red-700 border border-red-200 dark:bg-red-900/30 dark:text-red-200 dark:border-red-800'
    : 'text-sm rounded-lg px-4 py-3 whitespace-pre-wrap bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-200 dark:border-emerald-800';
  feedbackTimeout = setTimeout(() => feedbackEl.classList.add('hidden'), 8000);
}

function openTokenModal() {
  tokenInput.value = '';
  tokenModalError.classList.add('hidden');
  tokenModal.classList.remove('hidden');
  tokenInput.focus();
}

function closeTokenModal() {
  tokenModal.classList.add('hidden');
}

function pluginCard(plugin) {
  const actionHtml = plugin.installed
    ? '<span class="text-xs px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-200">Instalado</span>'
    : `<button data-action="install" data-slug="${escapeHtml(plugin.slug)}"
               class="text-xs px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white">
         Instalar
       </button>`;

  return `
    <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 flex flex-col gap-3" data-card="${escapeHtml(plugin.slug)}">
      <div class="flex items-start justify-between gap-2">
        <div>
          <h3 class="font-medium">${escapeHtml(plugin.name)}</h3>
          <p class="text-xs text-gray-400">v${escapeHtml(plugin.version)}</p>
        </div>
      </div>
      <p class="text-sm text-gray-500 dark:text-gray-400 flex-1">${escapeHtml(plugin.description) || 'Sin descripcion.'}</p>
      <div class="flex items-center justify-between" data-slot="action">
        ${actionHtml}
      </div>
    </div>`;
}

async function loadCatalog() {
  try {
    const response = await fetch('/api/v1/plugins/catalog');
    if (response.status === 401) {
      window.location.href = '/login';
      return;
    }
    if (!response.ok) {
      showFeedback('No se pudo cargar el catalogo de plugins.', true);
      return;
    }
    const data = await response.json();

    tokenStatusEl.classList.remove('hidden');
    if (data.configured) {
      tokenStatusEl.textContent = 'Token conectado';
      tokenStatusEl.className = 'text-xs px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-200';
    } else {
      tokenStatusEl.textContent = 'Sin token';
      tokenStatusEl.className = 'text-xs px-2.5 py-1 rounded-full bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400';
    }

    if (!data.configured) {
      emptyStateEl.classList.remove('hidden');
      gridEl.classList.add('hidden');
      return;
    }

    emptyStateEl.classList.add('hidden');
    gridEl.classList.remove('hidden');
    gridEl.innerHTML = data.plugins.length
      ? data.plugins.map(pluginCard).join('')
      : '<p class="text-sm text-gray-500 dark:text-gray-400 col-span-full">No hay plugins publicados en el repositorio.</p>';
  } catch (err) {
    showFeedback('Error de conexion al cargar el catalogo.', true);
  }
}

async function installPlugin(slug, button) {
  const card = gridEl.querySelector(`[data-card="${CSS.escape(slug)}"]`);
  const actionSlot = card ? card.querySelector('[data-slot="action"]') : null;
  const originalHtml = actionSlot ? actionSlot.innerHTML : '';
  button.disabled = true;
  button.textContent = 'Instalando...';

  try {
    const response = await fetch(`/api/v1/plugins/install/${encodeURIComponent(slug)}`, { method: 'POST' });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      showFeedback(`No se pudo instalar "${slug}": ${data.detail || 'error desconocido'}`, true);
      if (actionSlot) actionSlot.innerHTML = originalHtml;
      return;
    }

    showFeedback(`Plugin "${data.plugin.name}" instalado correctamente.`, false);
    if (actionSlot) {
      const openLink = data.plugin.has_ui && data.plugin.route
        ? `<a href="${escapeHtml(data.plugin.route)}" class="text-xs text-brand-600 hover:underline">Abrir</a>`
        : '';
      actionSlot.innerHTML = `
        <span class="text-xs px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-200">Instalado</span>
        ${openLink}`;
    }
  } catch (err) {
    showFeedback(`Error de conexion al instalar "${slug}".`, true);
    if (actionSlot) actionSlot.innerHTML = originalHtml;
  }
}

gridEl.addEventListener('click', (event) => {
  const button = event.target.closest('button[data-action="install"]');
  if (!button) return;
  installPlugin(button.dataset.slug, button);
});

document.getElementById('token-btn').addEventListener('click', openTokenModal);
document.getElementById('empty-state-connect-btn').addEventListener('click', openTokenModal);
document.getElementById('token-modal-cancel').addEventListener('click', closeTokenModal);
tokenModal.addEventListener('click', (event) => {
  if (event.target === tokenModal) closeTokenModal();
});

document.getElementById('token-modal-save').addEventListener('click', async () => {
  const token = tokenInput.value.trim();
  if (!token) {
    tokenModalError.textContent = 'Introduce un token.';
    tokenModalError.classList.remove('hidden');
    return;
  }

  const saveBtn = document.getElementById('token-modal-save');
  saveBtn.disabled = true;
  saveBtn.textContent = 'Verificando...';
  tokenModalError.classList.add('hidden');

  try {
    const response = await fetch('/api/v1/plugins/setup-token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      tokenModalError.textContent = data.detail || 'No se pudo verificar el token.';
      tokenModalError.classList.remove('hidden');
      return;
    }
    closeTokenModal();
    showFeedback('Token de GitHub guardado correctamente.', false);
    await loadCatalog();
  } catch (err) {
    tokenModalError.textContent = 'Error de conexion al guardar el token.';
    tokenModalError.classList.remove('hidden');
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = 'Guardar';
  }
});

loadCatalog();
