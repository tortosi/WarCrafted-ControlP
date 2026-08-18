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
          <p class="text-gray-400 text-xs" title="Normalizado a 1 nucleo = 100%; un proceso multihilo puede superar el 100%.">CPU</p>
          <p class="font-medium">${server.cpu_percent != null ? server.cpu_percent + '%' : '-'}</p>
          ${server.cpu_percent_host != null ? `<p class="text-[10px] text-gray-400" title="Equivalente en % de la capacidad total del host, comparable con el CPU del host de arriba.">${server.cpu_percent_host}% host</p>` : ''}
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
      <div class="flex flex-col gap-2 mt-1">
        <div class="flex gap-2">
          <button data-action="start" data-id="${escapeHtml(server.id)}" data-name="${escapeHtml(server.name)}"
                  ${server.online ? 'disabled' : ''}
                  class="flex-1 text-xs py-1.5 rounded-lg border border-gray-200 dark:border-gray-800 ${server.online ? 'opacity-50 cursor-not-allowed' : 'hover:bg-gray-100 dark:hover:bg-gray-800'}">
            Iniciar
          </button>
          <button data-action="stop" data-id="${escapeHtml(server.id)}" data-name="${escapeHtml(server.name)}"
                  ${server.online ? '' : 'disabled'}
                  class="flex-1 text-xs py-1.5 rounded-lg border border-gray-200 dark:border-gray-800 ${server.online ? 'hover:bg-gray-100 dark:hover:bg-gray-800' : 'opacity-50 cursor-not-allowed'}">
            Detener
          </button>
        </div>
        <div class="flex gap-2">
          <a href="/console/${server.id}"
             class="flex-1 text-xs py-1.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-center">
            Consola
          </a>
          <button data-action="log" data-id="${escapeHtml(server.id)}" data-name="${escapeHtml(server.name)}"
                  class="flex-1 text-xs py-1.5 rounded-lg border border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-800">
            Logs
          </button>
        </div>
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

const logModal = document.getElementById('log-modal');
const logModalTitle = document.getElementById('log-modal-title');
const logModalSelect = document.getElementById('log-modal-select');
const logModalLiveBtn = document.getElementById('log-modal-live');
const logModalCopyBtn = document.getElementById('log-modal-copy');
const logModalDownloadBtn = document.getElementById('log-modal-download');
const logModalContent = document.getElementById('log-modal-content');

const LOG_CATEGORY_LABELS = {
  worldserver: 'Consola',
  server: 'Servidor',
  errors: 'Errores',
  playerbots: 'Playerbots',
  gm: 'GM',
  chat: 'Chat',
};

let logInstanceId = null;
let logInstanceName = null;
let logSocket = null;

function logCategoryLabel(category) {
  return LOG_CATEGORY_LABELS[category] || category;
}

function logRunLabel(run) {
  return `${logCategoryLabel(run.category)} — ${run.started_at.replace('_', ' ')}`;
}

function appendLogLine(line) {
  const atBottom = logModalContent.scrollHeight - logModalContent.scrollTop - logModalContent.clientHeight < 40;
  logModalContent.textContent += (logModalContent.textContent ? '\n' : '') + line;
  if (atBottom) logModalContent.scrollTop = logModalContent.scrollHeight;
}

function stopLiveLog() {
  if (logSocket) {
    logSocket.close();
    logSocket = null;
  }
  logModalSelect.disabled = false;
  logModalLiveBtn.textContent = 'Ver en vivo';
  logModalLiveBtn.classList.remove('bg-brand-600', 'hover:bg-brand-700', 'text-white', 'border-transparent');
}

function startLiveLog() {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  logSocket = new WebSocket(`${protocol}://${window.location.host}/ws/servers/${logInstanceId}/logs`);
  logModalSelect.disabled = true;
  logModalLiveBtn.textContent = 'Detener vivo';
  logModalLiveBtn.classList.add('bg-brand-600', 'hover:bg-brand-700', 'text-white', 'border-transparent');
  logModalContent.textContent = '';

  logSocket.addEventListener('message', (event) => appendLogLine(event.data));
  logSocket.addEventListener('close', () => stopLiveLog());
}

async function loadSelectedLog() {
  if (!logInstanceId || !logModalSelect.value) return;
  logModalContent.textContent = 'Cargando...';
  try {
    const response = await fetch(`/api/servers/${logInstanceId}/logs/${encodeURIComponent(logModalSelect.value)}`);
    if (!response.ok) {
      logModalContent.textContent = 'No se pudo cargar este archivo de log.';
      return;
    }
    const data = await response.json();
    logModalContent.textContent = data.content || '(archivo vacio)';
  } catch (err) {
    logModalContent.textContent = 'Error de conexion al cargar el log.';
  }
}

async function openLogModal(id, name) {
  logInstanceId = id;
  logInstanceName = name;
  logModalTitle.textContent = `Logs — ${name}`;
  logModalContent.textContent = 'Cargando...';
  logModalSelect.innerHTML = '';
  logModal.classList.remove('hidden');

  try {
    const response = await fetch(`/api/servers/${id}/logs`);
    const runs = response.ok ? await response.json() : [];
    if (!runs.length) {
      logModalContent.textContent = 'Todavia no hay logs guardados para esta instancia.';
      return;
    }
    logModalSelect.innerHTML = runs
      .map((run) => `<option value="${escapeHtml(run.filename)}">${escapeHtml(logRunLabel(run))}</option>`)
      .join('');
    await loadSelectedLog();
  } catch (err) {
    logModalContent.textContent = 'Error de conexion al listar los logs.';
  }
}

function closeLogModal() {
  stopLiveLog();
  logInstanceId = null;
  logInstanceName = null;
  logModal.classList.add('hidden');
}

logModalSelect.addEventListener('change', () => {
  if (logSocket) stopLiveLog();
  loadSelectedLog();
});

logModalLiveBtn.addEventListener('click', () => {
  if (logSocket) {
    stopLiveLog();
    loadSelectedLog();
  } else {
    startLiveLog();
  }
});

logModalCopyBtn.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(logModalContent.textContent);
    const original = logModalCopyBtn.textContent;
    logModalCopyBtn.textContent = 'Copiado';
    setTimeout(() => { logModalCopyBtn.textContent = original; }, 1500);
  } catch (err) {
    showFeedback('No se pudo copiar el log al portapapeles.', true);
  }
});

logModalDownloadBtn.addEventListener('click', () => {
  const filename = logModalSelect.value || `${logInstanceName || 'log'}.txt`;
  const blob = new Blob([logModalContent.textContent], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename.endsWith('.log') ? filename.replace(/\.log$/, '.txt') : `${filename}.txt`;
  link.click();
  URL.revokeObjectURL(url);
});

document.getElementById('log-modal-close').addEventListener('click', closeLogModal);
logModal.addEventListener('click', (event) => {
  if (event.target === logModal) closeLogModal();
});

gridEl.addEventListener('click', async (event) => {
  const button = event.target.closest('button[data-action]');
  if (!button) return;
  const { action, id, name } = button.dataset;
  if (action === 'log') {
    openLogModal(id, name);
    return;
  }
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

async function checkUpdates() {
  const badge = document.getElementById('store-update-badge');
  let count = 0;
  const parts = [];

  try {
    const response = await fetch('/api/v1/plugins/catalog');
    if (response.ok) {
      const data = await response.json();
      if (data.configured) {
        const updates = data.plugins.filter((plugin) => plugin.update_available);
        if (updates.length) {
          count += updates.length;
          parts.push(`${updates.length} plugin(s)`);
        }
      }
    }
  } catch (err) {
    // la tienda no es critica para el dashboard; se ignora en silencio
  }

  try {
    const response = await fetch('/api/system/update-check');
    if (response.ok) {
      const data = await response.json();
      if (data.configured && data.update_available) {
        count += 1;
        parts.push('el panel principal');
      }
    }
  } catch (err) {
    // idem
  }

  if (count) {
    badge.textContent = count;
    badge.title = `Hay actualizaciones disponibles: ${parts.join(' y ')}`;
    badge.classList.remove('hidden');
  }
}

refreshStats();
refreshServers();
loadPluginsMenu();
checkUpdates();
setInterval(refreshStats, 5000);
setInterval(refreshServers, 5000);
