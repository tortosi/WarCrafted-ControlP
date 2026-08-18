(function () {
  const instanceId = window.__INSTANCE_ID__;
  const win = document.getElementById('console-window');
  const header = document.getElementById('console-header');
  const MIN_WIDTH = 360;
  const MIN_HEIGHT = 240;

  function setInitialGeometry() {
    const parent = win.parentElement;
    const width = Math.min(900, parent.clientWidth - 32);
    const height = Math.min(560, parent.clientHeight - 32);
    win.style.width = `${width}px`;
    win.style.height = `${height}px`;
    win.style.left = `${Math.max(0, (parent.clientWidth - width) / 2)}px`;
    win.style.top = `${Math.max(0, (parent.clientHeight - height) / 2)}px`;
  }
  setInitialGeometry();

  const term = new Terminal({
    convertEol: true,
    fontSize: 14,
    theme: { background: '#000000' },
  });
  const fitAddon = new FitAddon.FitAddon();
  term.loadAddon(fitAddon);
  term.open(document.getElementById('terminal'));
  fitAddon.fit();

  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/console/${instanceId}`);

  let buffer = '';
  const history = [];
  let historyIndex = null;

  socket.addEventListener('open', () => {
    term.writeln('Conectando...');
  });

  socket.addEventListener('message', (event) => {
    term.write('\r\n' + event.data + '\r\n> ');
  });

  socket.addEventListener('close', (event) => {
    term.write(`\r\n[Conexion cerrada${event.code ? ' - codigo ' + event.code : ''}]`);
  });

  function setBuffer(text) {
    for (let i = 0; i < buffer.length; i++) term.write('\b \b');
    buffer = text;
    term.write(buffer);
  }

  term.write('> ');
  term.onKey(({ key, domEvent }) => {
    if (domEvent.key === 'Enter') {
      term.write('\r\n');
      if (buffer.trim()) {
        socket.send(buffer);
        if (history[history.length - 1] !== buffer) history.push(buffer);
      }
      buffer = '';
      historyIndex = null;
    } else if (domEvent.key === 'Backspace') {
      if (buffer.length > 0) {
        buffer = buffer.slice(0, -1);
        term.write('\b \b');
      }
    } else if (domEvent.key === 'ArrowUp') {
      if (history.length > 0) {
        historyIndex = historyIndex === null ? history.length - 1 : Math.max(0, historyIndex - 1);
        setBuffer(history[historyIndex]);
      }
    } else if (domEvent.key === 'ArrowDown') {
      if (historyIndex !== null) {
        if (historyIndex < history.length - 1) {
          historyIndex += 1;
          setBuffer(history[historyIndex]);
        } else {
          historyIndex = null;
          setBuffer('');
        }
      }
    } else if (key.length === 1) {
      buffer += key;
      term.write(key);
    }
  });

  let dragState = null;
  let resizeState = null;

  header.addEventListener('mousedown', (event) => {
    dragState = {
      startX: event.clientX,
      startY: event.clientY,
      startLeft: win.offsetLeft,
      startTop: win.offsetTop,
    };
    document.body.style.userSelect = 'none';
    event.preventDefault();
  });

  win.querySelectorAll('.resize-handle').forEach((handle) => {
    handle.addEventListener('mousedown', (event) => {
      resizeState = {
        dir: handle.dataset.dir,
        startX: event.clientX,
        startY: event.clientY,
        startWidth: win.offsetWidth,
        startHeight: win.offsetHeight,
        startLeft: win.offsetLeft,
        startTop: win.offsetTop,
      };
      document.body.style.userSelect = 'none';
      event.preventDefault();
      event.stopPropagation();
    });
  });

  window.addEventListener('mousemove', (event) => {
    if (dragState) {
      const dx = event.clientX - dragState.startX;
      const dy = event.clientY - dragState.startY;
      win.style.left = `${dragState.startLeft + dx}px`;
      win.style.top = `${dragState.startTop + dy}px`;
      return;
    }

    if (resizeState) {
      const dx = event.clientX - resizeState.startX;
      const dy = event.clientY - resizeState.startY;
      const { dir, startWidth, startHeight, startLeft, startTop } = resizeState;

      if (dir.includes('e')) {
        win.style.width = `${Math.max(MIN_WIDTH, startWidth + dx)}px`;
      }
      if (dir.includes('s')) {
        win.style.height = `${Math.max(MIN_HEIGHT, startHeight + dy)}px`;
      }
      if (dir.includes('w')) {
        const newWidth = Math.max(MIN_WIDTH, startWidth - dx);
        win.style.width = `${newWidth}px`;
        win.style.left = `${startLeft + (startWidth - newWidth)}px`;
      }
      if (dir.includes('n')) {
        const newHeight = Math.max(MIN_HEIGHT, startHeight - dy);
        win.style.height = `${newHeight}px`;
        win.style.top = `${startTop + (startHeight - newHeight)}px`;
      }
      fitAddon.fit();
    }
  });

  window.addEventListener('mouseup', () => {
    dragState = null;
    resizeState = null;
    document.body.style.userSelect = '';
  });

  window.addEventListener('resize', () => fitAddon.fit());
})();
