# Manual de instalacion

## Requisitos previos

- **Python 3.11 o superior** (recomendado; funciona desde 3.10).
- Acceso de red a los puertos SOAP (por defecto `7878`) y a la base de datos MySQL/MariaDB de cada emulador que quieras monitorizar.
- En Linux: `python3-venv` y `python3-pip` (el instalador los requiere; instalalos con `sudo apt install python3-venv python3-pip` si faltan).
- En Windows: Python instalado desde [python.org](https://www.python.org/downloads/) con la opcion "Add python.exe to PATH" activada.

## Instalacion automatica

### Linux (Debian/Ubuntu)

```bash
git clone <url-del-repositorio>
cd WarCrafted-ControlP
./install.sh
```

El script:
1. Verifica que Python 3 este disponible.
2. Crea un entorno virtual en `.venv`.
3. Instala las dependencias de `requirements.txt`.
4. Crea `.env` a partir de `.env.example` (si no existe) y genera una `SECRET_KEY` aleatoria.
5. Crea la carpeta `data/` para la base de datos interna del panel.
6. Pide un usuario y contrasena para crear el administrador del panel.

### Windows

```bat
git clone <url-del-repositorio>
cd WarCrafted-ControlP
install.bat
```

El script realiza los mismos pasos que en Linux, adaptados a `cmd.exe`.

> En Windows, `set /p` no oculta la contrasena mientras se escribe. Si necesitas ocultarla, crea el usuario administrador manualmente despues con `python -m app.cli create-admin` desde una consola con el entorno virtual activado.

## Instalacion manual (paso a paso)

Si prefieres no usar los scripts, o necesitas mas control sobre el proceso:

```bash
# 1. Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate.bat

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Edita .env y define SECRET_KEY, las instancias de emulador, etc.

# 4. Crear el usuario administrador
python -m app.cli create-admin

# 5. Arrancar el panel
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Configuracion de `.env`

### Variables de aplicacion

| Variable | Descripcion | Valor por defecto |
|---|---|---|
| `APP_NAME` | Nombre mostrado en la interfaz | `WarCrafted-ControlP` |
| `APP_HOST` / `APP_PORT` | Host y puerto donde escucha el panel | `0.0.0.0` / `8000` |
| `SECRET_KEY` | Clave usada para firmar los tokens JWT | *(generada por el instalador)* |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duracion de la sesion | `120` |
| `COOKIE_SECURE` | Marca la cookie de sesion como `Secure` (requiere HTTPS) | `false` |
| `APP_DB_URL` | Cadena de conexion de la base de datos interna del panel | `sqlite:///./data/app.db` |

### Instancias de emulador

Cada instancia se define con variables numeradas usando el prefijo `INSTANCE_<N>_`, donde `<N>` es un numero entero (1, 2, 3...). Puedes definir tantas como necesites.

| Variable | Descripcion |
|---|---|
| `INSTANCE_<N>_ENABLED` | `true`/`false`, activa o desactiva la instancia sin borrarla |
| `INSTANCE_<N>_NAME` | Nombre mostrado en el panel |
| `INSTANCE_<N>_TYPE` | `azerothcore` o `playerbots` (tambien se aceptan variantes que contengan esas palabras, p. ej. `playerbots-acore`) |
| `INSTANCE_<N>_WORLD_PROCESS` | Nombre del proceso del worldserver a monitorizar |
| `INSTANCE_<N>_AUTH_PROCESS` | Nombre del proceso del authserver |
| `INSTANCE_<N>_START_CMD` | Ruta al ejecutable usado para iniciar el worldserver |
| `INSTANCE_<N>_WORKDIR` | Directorio de trabajo al ejecutar `START_CMD` |
| `INSTANCE_<N>_SOAP_HOST` / `SOAP_PORT` | Host y puerto del servicio SOAP |
| `INSTANCE_<N>_SOAP_USER` / `SOAP_PASS` | Credenciales de la cuenta GM habilitada para SOAP |
| `INSTANCE_<N>_DB_HOST` / `DB_PORT` | Host y puerto de la base de datos MySQL/MariaDB |
| `INSTANCE_<N>_DB_USER` / `DB_PASS` | Credenciales de solo lectura para la base de datos |
| `INSTANCE_<N>_DB_CHARACTERS` | Nombre de la base de datos `characters` del emulador |

Consulta `.env.example` para ver un ejemplo completo con dos instancias (una AzerothCore y una Playerbots).

> **Importante:** si dos instancias comparten el mismo `WORLD_PROCESS` (p.ej. ambas usan el binario `worldserver`), el panel las distingue por su `WORKDIR`. Define siempre `INSTANCE_<N>_WORKDIR` con la ruta absoluta y distinta de cada instalacion; si se omite, el panel no puede garantizar que "Iniciar"/"Detener" actuen solo sobre esa instancia.

### Habilitar el servicio SOAP en AzerothCore

En `worldserver.conf`, asegurate de tener:

```
SOAP.Enabled = 1
SOAP.IP = 127.0.0.1
SOAP.Port = 7878
```

La cuenta usada en `SOAP_USER`/`SOAP_PASS` debe tener nivel de GM suficiente (`GMLEVEL`) en la base de datos `auth`.

## Arranque

```bash
./run.sh          # Linux
run.bat           # Windows
```

Ambos scripts activan el entorno virtual, cargan `.env` y arrancan Uvicorn en el host/puerto configurados.

## Ejecucion como servicio (opcional, Linux con systemd)

Crea `/etc/systemd/system/warcrafted-controlp.service`:

```ini
[Unit]
Description=WarCrafted-ControlP
After=network.target

[Service]
Type=simple
WorkingDirectory=/ruta/a/WarCrafted-ControlP
ExecStart=/ruta/a/WarCrafted-ControlP/run.sh
Restart=on-failure
User=www-data

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now warcrafted-controlp
```

## Diagnostico de arranque

Si el boton "Iniciar" de una instancia falla, el panel devuelve el error exacto (binario no encontrado, proceso terminado al instante, etc.) tanto en el aviso del dashboard como en el log del servidor. Ademas, cada instancia escribe la salida de su proceso en `data/logs/<id-instancia>.log` (p. ej. `data/logs/instance-1.log`), util para ver por que `worldserver` no arranco.

## Solucion de problemas

| Sintoma | Posible causa |
|---|---|
| Las tarjetas muestran "-" en CPU/RAM | El proceso no esta en ejecucion, o `WORLD_PROCESS`/`WORKDIR` no coinciden con el proceso real |
| Una instancia aparece como tarjeta roja con un error | `INSTANCE_<N>_TYPE` no se pudo interpretar como `azerothcore` ni `playerbots`; revisa el valor en `.env` |
| Jugadores online no se actualiza | Credenciales o host de `DB_*` incorrectos, o el usuario MySQL no tiene permisos sobre la base `characters` |
| La consola GM devuelve error de conexion | El servicio SOAP no esta habilitado, el puerto esta bloqueado por firewall, o `SOAP_USER`/`SOAP_PASS` son incorrectos |
| "401 No autenticado" al recargar el panel | La sesion expiro (`ACCESS_TOKEN_EXPIRE_MINUTES`) o `SECRET_KEY` cambio; vuelve a iniciar sesion |
