# WarCrafted-ControlP - Especificaciones del Proyecto

## 1. Objetivo General
Panel de control web modular, moderno y profesional para la gestión remota de múltiples emuladores de World of Warcraft (AzerothCore Estándar y AzerothCore + Playerbots).

## 2. Privacidad y Seguridad Git
- Archivo `.gitignore` estricto desde el inicio: ignorar `.env`, `.env.*`, `__pycache__/`, `.venv/`, `*.log` y cualquier rastro de credenciales.
- Variables de entorno centralizadas en `.env` (usando `.env.example` como plantilla).
- Autenticación segura mediante usuario/contraseña y tokens JWT.

## 3. Autoinstalación Multiplataforma
- `install.sh`: Script bash autoinstalable para Linux (Debian/Ubuntu).
- `install.bat`: Script autoinstalable para Windows.
- Creación automática de entorno virtual de Python (`.venv`) e instalación de `requirements.txt`.

## 4. Arquitectura Modular (Multi-Emulador)
- Drivers extensibles en `app/emulators/`:
  - `base.py`: Clase abstracta `BaseEmulatorDriver`con la interfaz común (estado de procesos, ejecución de comandos SOAP, consulta de estado DB).
  - `azerothcore.py`: Driver para AzerothCore Estándar.
  - `playerbots.py`: Driver adaptado a esquemas y comandos de Playerbots.
- Selección modular del emulador al configurar o instalar. El archivo de configuración .env permitirá definir y activar múltiples instancias/emuladores montados en el servidor.

## 5. Frontend y Temas
- Construido con TailwindCSS + HTML/JS.
- Soporte nativo para Tema Oscuro (Dark) y Tema Claro (Light) intercambiable con un clic.
- Consola interactiva en tiempo real mediante WebSockets (`Xterm.js`).
- Tarjetas de estado de CPU/RAM, jugadores online e integración con SOAP para comandos GM.

## 6. Documentación Requerida
- `README.md`: Descripción general.
- `INSTALL.md`: Manual de instalación detallado.
- `USER_GUIDE.md`: Manual de uso e instrucciones de la interfaz.
- `CHANGELOG.md`: Historial de versiones y cambios.
