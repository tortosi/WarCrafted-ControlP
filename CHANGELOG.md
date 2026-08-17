# Changelog

Todas las modificaciones relevantes de este proyecto se documentan en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y este proyecto sigue [Versionado Semantico](https://semver.org/lang/es/).

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
