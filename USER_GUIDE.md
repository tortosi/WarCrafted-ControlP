# Manual de usuario

## Acceso al panel

Abre en tu navegador la direccion donde este publicado el panel (por ejemplo `http://localhost:8000` en una instalacion local). Se mostrara la pantalla de inicio de sesion.

Introduce el usuario y contrasena creados durante la instalacion (o con `python -m app.cli create-admin`). Tras iniciar sesion, la sesion se mantiene mediante una cookie segura durante el tiempo definido en `ACCESS_TOKEN_EXPIRE_MINUTES` (por defecto, 2 horas).

## Tema claro / oscuro

En la esquina superior derecha de cualquier pantalla encontraras un boton con un icono de luna/sol. Al pulsarlo, cambia entre tema claro y oscuro; la preferencia se guarda en el navegador y se recuerda en tu proxima visita.

## Panel principal (dashboard)

Al iniciar sesion accedes al panel principal, dividido en dos zonas:

### Estadisticas del host

Tres tarjetas en la parte superior muestran el estado general del servidor donde corre el panel:

- **CPU del host**: porcentaje de uso de CPU.
- **Memoria**: porcentaje de uso y detalle en MB usados/totales.
- **Disco**: porcentaje de uso del disco principal.

Estos datos se actualizan automaticamente cada 5 segundos.

### Instancias de emulador

Cada instancia configurada en `.env` aparece como una tarjeta con:

- **Indicador de estado**: punto verde si el proceso esta en ejecucion, gris si esta detenido.
- **Tipo de emulador**: etiqueta "AzerothCore" o "Playerbots".
- **CPU / RAM**: consumo del proceso `worldserver` de esa instancia.
- **Jugadores**: numero de personajes conectados. En instancias Playerbots, las cuentas de bots se excluyen del conteo para reflejar solo jugadores humanos.

Cada tarjeta incluye tres acciones:

| Boton | Accion |
|---|---|
| **Iniciar** | Lanza el proceso `worldserver` usando el comando configurado en `INSTANCE_<N>_START_CMD`. No hace nada si ya esta en ejecucion. |
| **Detener** | Envia un apagado controlado via SOAP (`server shutdown`); si el servicio SOAP no responde, intenta detener el proceso directamente. |
| **Consola** | Abre la consola GM interactiva de esa instancia. |

## Consola GM

La consola reproduce una terminal (basada en Xterm.js) conectada por WebSocket al panel. Cada linea que escribas y envies con **Enter** se ejecuta como comando GM contra el servicio SOAP de la instancia, y la respuesta del servidor se muestra a continuacion.

Ejemplos de comandos utiles:

```
server info
account set gmlevel <usuario> 3 -1
kick <personaje>
announce Mensaje para todo el servidor
```

Si el servicio SOAP no esta disponible, la consola mostrara un mensaje de error indicando el motivo (credenciales invalidas, conexion rechazada, etc.).

Para volver al panel principal, usa el enlace "← Panel" en la parte superior de la pantalla de consola.

## Cerrar sesion

Pulsa **Cerrar sesion** en la parte superior del panel para invalidar la cookie de sesion y volver a la pantalla de inicio de sesion.

## Buenas practicas de seguridad

- Cambia la contrasena de administrador periodicamente con `python -m app.cli create-admin` (crea el usuario si no existe, o actualiza la contrasena si ya existe).
- No compartas el archivo `.env`; contiene la clave de firma de sesiones y las credenciales SOAP/DB de tus emuladores.
- Si publicas el panel fuera de tu red local, hazlo detras de un proxy HTTPS y activa `COOKIE_SECURE=true` en `.env`.
