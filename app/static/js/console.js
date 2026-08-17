(function () {
  const instanceId = window.__INSTANCE_ID__;
  const term = new Terminal({
    convertEol: true,
    fontSize: 14,
    theme: { background: '#000000' },
  });
  const fitAddon = new FitAddon.FitAddon();
  term.loadAddon(fitAddon);
  term.open(document.getElementById('terminal'));
  fitAddon.fit();
  window.addEventListener('resize', () => fitAddon.fit());

  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/console/${instanceId}`);

  let buffer = '';

  socket.addEventListener('open', () => {
    term.writeln('Conectando...');
  });

  socket.addEventListener('message', (event) => {
    term.write('\r\n' + event.data + '\r\n> ');
  });

  socket.addEventListener('close', (event) => {
    term.write(`\r\n[Conexion cerrada${event.code ? ' - codigo ' + event.code : ''}]`);
  });

  term.write('> ');
  term.onKey(({ key, domEvent }) => {
    if (domEvent.key === 'Enter') {
      term.write('\r\n');
      if (buffer.trim()) socket.send(buffer);
      buffer = '';
    } else if (domEvent.key === 'Backspace') {
      if (buffer.length > 0) {
        buffer = buffer.slice(0, -1);
        term.write('\b \b');
      }
    } else if (key.length === 1) {
      buffer += key;
      term.write(key);
    }
  });
})();
