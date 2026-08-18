# Changelog

Todas las modificaciones relevantes de este proyecto se documentan en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y este proyecto sigue [Versionado Semantico](https://semver.org/lang/es/).

## [Sin publicar]

### Anadido
- Las tarjetas de instancia muestran tambien el % de CPU como capacidad del host (ademas del % por-proceso, normalizado a 1 nucleo = 100%), para que no parezca un error ver, p. ej., 179% de CPU en una instancia con el host al 68%.

## [0.3.0] - 2026-08-18

### Anadido
- Menu desplegable "Plugins" en la barra superior del panel: consume `GET /api/v1/plugins/` y enlaza los modulos que declaren `ui.has_ui: true` en su `manifest.json` (titulo, ruta e icono definidos por cada plugin).
- El loader de plugins expone metadatos de interfaz (`ui.has_ui`, `ui.title`, `ui.route`, `ui.icon`) y el core los publica mediante `app/api/plugins.py`.
- Tienda de Plugins (`/plugins/store`): conecta un Personal Access Token de GitHub (`POST /api/v1/plugins/setup-token`, guardado en `GITHUB_PLUGIN_TOKEN` dentro de `.env`), lista el catalogo del repo `WarCraftedCP-plugins` (`GET /api/v1/plugins/catalog`) marcando que modulos ya estan instalados y si hay version nueva, instala uno con un clic (`POST /api/v1/plugins/install/{nombre}`) y lo actualiza (`POST /api/v1/plugins/update/{nombre}`) fusionando la version nueva sobre la carpeta existente sin borrar datos que el plugin haya generado (backups, etc.). Todo se monta o remonta en caliente, sin reiniciar el panel. Requiere permisos de administrador.
- Autoactualizacion del propio panel (`GET /api/system/update-check`, `POST /api/system/update`, `POST /api/system/restart`): compara el archivo `VERSION` local contra el del repo `WarCrafted-ControlP` en GitHub, descarga y fusiona la version nueva sin tocar `.env`, `data/` ni los plugins instalados, reinstala `requirements.txt` en el mismo venv si cambio, y permite reiniciar el proceso para aplicar los cambios (requiere un supervisor externo como systemd `Restart=always` para volver a levantarse).

## [0.2.0] - 2026-08-18

### Corregido
- Independencia de procesos entre instancias: la deteccion ya no se basa solo en el nombre del binario (`WORLD_PROCESS`), sino en un PID propio por instancia mas coincidencia por `WORKDIR` (con `cmdline` como respaldo). Antes, dos instancias con el mismo binario `worldserver` podian detenerse mutuamente.
- Medicion de CPU siempre en 0%: `psutil.Process.cpu_percent()` se invocaba dentro de un bloque `oneshot()`, que cacheaba la lectura "antes" y anulaba la comparacion "despues". Ahora la medicion se hace fuera de ese bloque y refleja el consumo real.
- El listado de instancias (`/api/servers`) recarga el `.env` en cada peticion, de forma que anadir o editar una instancia se refleja en el dashboard sin reiniciar el panel.
- `INSTANCE_<N>_TYPE` admite variantes del valor esperado (p. ej. `playerbots-acore`) mediante coincidencia parcial; una instancia con un tipo realmente no reconocido ya no desaparece del dashboard, se muestra como tarjeta de error con el motivo.

### Anadido
- Historial de comandos en la consola GM: las flechas Arriba/Abajo navegan por los comandos enviados anteriormente (Xterm.js).
- Consola GM como panel flotante: cabecera arrastrable para moverla y bordes/esquinas para redimensionarla, con reajuste automatico de Xterm.js (`fitAddon.fit()`) en cada cambio de tamano.
- Los fallos de arranque o parada de una instancia devuelven el error exacto en la respuesta JSON y quedan registrados tanto en el log del servidor como en `data/logs/<instancia>.log`.

## [0.1.0] - 2026-08-18

### Anadido
- Estructura inicial del proyecto con backend FastAPI y frontend TailwindCSS.
- Autenticacion con usuario/contrasena, hash bcrypt y sesiones JWT en cookie httpOnly.
- Arquitectura modular de drivers de emulador (`BaseEmulatorDriver`) con implementaciones para AzerothCore estandar y AzerothCore + Playerbots.
- Gestion de multiples instancias configurables desde `.env`.
- Cliente SOAP para ejecucion de comandos GM.
- Consola interactiva en tiempo real via WebSocket + Xterm.js.
- Panel con tarjetas de estado de CPU, RAM y jugadores online, y estadisticas del host.
- Tema claro/oscuro intercambiable con persistencia en el navegador.
- Scripts de autoinstalacion multiplataforma (`install.sh`, `install.bat`) y de arranque (`run.sh`, `run.bat`).
- Documentacion inicial: README, INSTALL y USER_GUIDE.
- `.gitignore` estricto para proteger credenciales y excluir rastros de herramientas de IA.
