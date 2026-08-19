(function () {
  // Carga en segundo plano el script opcional de cada plugin activo que lo
  // declare (manifest.json -> ui.background_script), en todas las paginas
  // del panel. Es la unica forma que tiene un plugin de correr codigo fuera
  // de su propia vista (p.ej. para vigilar el estado de las instancias y
  // disparar notificaciones aunque el usuario este en el Dashboard).
  fetch('/api/v1/plugins/')
    .then((response) => (response.ok ? response.json() : []))
    .then((plugins) => {
      plugins
        .filter((plugin) => plugin.background_script)
        .forEach((plugin) => {
          const script = document.createElement('script');
          script.src = plugin.background_script;
          document.body.appendChild(script);
        });
    })
    .catch(() => {
      // sin sesion iniciada o sin plugins activos; no es critico
    });
})();
