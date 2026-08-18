const statsEl = document.getElementById('system-stats');
const gridEl = document.getElementById('servers-grid');
const feedbackEl = document.getElementById('action-feedback');
let feedbackTimeout = null;

function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return String(text).replace(/[&<>"']/g, (char) => map[char]);
}

function showFeedback(message, isError) {
  clearTimeout(feedbackTimeout);
  feedbackEl.textContent = message;
  feedbackEl.className = isError
    ? 'text-sm rounded-lg px-4 py-3 whitespace-pre-wrap bg-red-50 text-red-700 border border-red-200 dark:bg-red-900/30 dark:text-red-200 dark:border-red-800'
    : 'text-sm rounded-lg px-4 py-3 whitespace-pre-wrap bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-200 dark:border-emerald-800';
  feedbackTimeout = setTimeout(() => feedbackEl.classList.add('hidden'), 8000);
}

function statCard(label, value, sub) {
  return `
    <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
      <p class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">${label}</p>
      <p class="text-2xl font-semibold mt-1">${value}</p>
      ${sub ? `<p class="text-xs text-gray-400 mt-1">${sub}</p>` : ''}
    </div>`;
}

function serverCard(server) {
  if (server.error) {
    return `
      <div class="bg-white dark:bg-gray-900 rounded-xl border border-red-200 dark:border-red-900 p-4 flex flex-col gap-2">
        <div class="flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded-full bg-red-500"></span>
          <h3 class="font-medium">${escapeHtml(server.name)}</h3>
        </div>
        <p class="text-xs text-red-600 dark:text-red-400">${escapeHtml(server.error)}</p>
      </div>`;
  }

  const dotColor = server.online ? 'bg-emerald-500' : 'bg-gray-400';
  const typeLabel = server.type === 'playerbots' ? 'Playerbots' : 'AzerothCore';
  return `
    <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 flex flex-col gap-3">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded-full ${dotColor}"></span>
          <h3 class="font-medium">${escapeHtml(server.name)}</h3>
        </div>
        <span class="text-xs px-2 py-0.5 rounded-full bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-100">${typeLabel}</span>
      </div>
      <div class="grid grid-cols-3 gap-2 text-center text-sm">
        <div>
          <p class="text-gray-400 text-xs">CPU</p>
          <p class="font-medium">${server.cpu_percent != null ? server.cpu_percent + '%' : '-'}</p>
        </div>
        <div>
          <p class="text-gray-400 text-xs">RAM</p>
          <p class="font-medium">${server.memory_mb != null ? server.memory_mb + ' MB' : '-'}</p>
        </div>
        <div>
          <p class="text-gray-400 text-xs">Jugadores</p>
          <p class="font-medium">${server.players_online != null ? server.players_online : '-'}</p>
        </div>
      </div>
      <div class="flex gap-2 mt-1">
        <button data-action="start" data-id="${escapeHtml(server.id)}" data-name="${escapeHtml(server.name)}"
                class="flex-1 text-xs py-1.5 rounded-lg border border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-800">
          Iniciar
        </button>
        <button data-action="stop" data-id="${escapeHtml(server.id)}" data-name="${escapeHtml(server.name)}"
                class="flex-1 text-xs py-1.5 rounded-lg border border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-800">
          Detener
        </button>
        <a href="/console/${server.id}"
           class="flex-1 text-xs py-1.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-center">
          Consola
        </a>
      </div>
    </div>`;
}

async function refreshStats() {
  try {
    const response = await fetch('/api/system/stats');
    if (!response.ok) return;
    const data = await response.json();
    statsEl.innerHTML = [
      statCard('CPU del host', data.cpu_percent + '%'),
      statCard('Memoria', data.memory_percent + '%', `${data.memory_used_mb} / ${data.memory_total_mb} MB`),
      statCard('Disco', data.disk_percent + '%'),
    ].join('');
  } catch (err) {
    // se reintenta en el siguiente ciclo de refresco
  }
}

async function refreshServers() {
  try {
    const response = await fetch('/api/servers');
    if (response.status === 401) {
      window.location.href = '/login';
      return;
    }
    if (!response.ok) return;
    const servers = await response.json();
    gridEl.innerHTML = servers.length
      ? servers.map(serverCard).join('')
      : '<p class="text-sm text-gray-500 dark:text-gray-400">No hay instancias configuradas en el .env.</p>';
  } catch (err) {
    // se reintenta en el siguiente ciclo de refresco
  }
}

gridEl.addEventListener('click', async (event) => {
  const button = event.target.closest('button[data-action]');
  if (!button) return;
  const { action, id, name } = button.dataset;
  const actionLabel = action === 'start' ? 'iniciar' : 'detener';
  button.disabled = true;
  try {
    const response = await fetch(`/api/servers/${id}/${action}`, { method: 'POST' });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      showFeedback(`No se pudo ${actionLabel} "${name}": ${data.detail || 'error desconocido'}`, true);
    } else if (data.detail) {
      showFeedback(`${name}: ${data.detail}`, data.success === false);
    }
    await refreshServers();
  } catch (err) {
    showFeedback(`Error de conexion al intentar ${actionLabel} "${name}".`, true);
  } finally {
    button.disabled = false;
  }
});

document.getElementById('logout-btn').addEventListener('click', async () => {
  await fetch('/api/auth/logout', { method: 'POST' });
  window.location.href = '/login';
});

const pluginsMenuBtn = document.getElementById('plugins-menu-btn');
const pluginsMenu = document.getElementById('plugins-menu');

function pluginMenuItem(plugin) {
  const icon = plugin.icon ? `<i class="fa-solid ${escapeHtml(plugin.icon)} w-4 text-center text-gray-400"></i>` : '';
  return `
    <a href="${escapeHtml(plugin.route)}" class="flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-800">
      ${icon}
      ${escapeHtml(plugin.title)}
    </a>`;
}

async function loadPluginsMenu() {
  try {
    const response = await fetch('/api/v1/plugins/');
    if (!response.ok) {
      pluginsMenu.innerHTML = '<p class="px-3 py-2 text-sm text-gray-400">No se pudo cargar los plugins</p>';
      return;
    }
    const pluginsList = await response.json();
    const withUi = pluginsList.filter((plugin) => plugin.has_ui && plugin.route);
    pluginsMenu.innerHTML = withUi.length
      ? withUi.map(pluginMenuItem).join('')
      : '<p class="px-3 py-2 text-sm text-gray-400">Sin plugins con interfaz</p>';
  } catch (err) {
    pluginsMenu.innerHTML = '<p class="px-3 py-2 text-sm text-gray-400">No se pudo cargar los plugins</p>';
  }
}

pluginsMenuBtn.addEventListener('click', (event) => {
  event.stopPropagation();
  pluginsMenu.classList.toggle('hidden');
});
document.addEventListener('click', () => pluginsMenu.classList.add('hidden'));

async function checkPluginUpdates() {
  const badge = document.getElementById('store-update-badge');
  try {
    const response = await fetch('/api/v1/plugins/catalog');
    if (!response.ok) return;
    const data = await response.json();
    if (!data.configured) return;
    const updates = data.plugins.filter((plugin) => plugin.update_available);
    if (updates.length) {
      badge.textContent = updates.length;
      badge.classList.remove('hidden');
    }
  } catch (err) {
    // la tienda no es critica para el dashboard; se ignora en silencio
  }
}

refreshStats();
refreshServers();
loadPluginsMenu();
checkPluginUpdates();
setInterval(refreshStats, 5000);
setInterval(refreshServers, 5000);
