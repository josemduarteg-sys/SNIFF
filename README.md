# SNIFF — instalación y entrega institucional

Sistema de planificación e indicadores con Django, Vue 3 y PostgreSQL.
La cooperativa instala el código y crea su propia base. No se necesitan datos
de demostración ni un respaldo del equipo de desarrollo para empezar.

El despliegue requiere configuración manual de dominio/IP, sistema operativo,
HTTPS, proxy, servidor de aplicaciones, almacenamiento y respaldos. Estos
parámetros debe definirlos el personal técnico institucional. Las instrucciones
no instalan servicios ni activan tareas automáticamente.

## 1. Requisitos

- Python 3.12 o superior compatible con las versiones de backend/requirements.txt.
  El desarrollo y las pruebas locales usan Python 3.13.
- PostgreSQL 14 o superior. Una cuenta administradora para crear la base; la
  aplicación usa después su propia cuenta con permisos sobre esa base.
- Node.js 22.18+ de la rama 22, o 24.11+ de la rama 24, con npm. Son requisitos
  del conjunto fijado en frontend/package-lock.json, no solo de Vue.
- Acceso al repositorio y a los repositorios de paquetes durante instalación.
- En producción: servidor HTTP, HTTPS y servidor WSGI compatibles con el sistema
  operativo elegido. No están incluidos ni instalados por este proyecto.

Conservar requirements.txt, package-lock.json, todas las migraciones y los
archivos __init__.py. No generar migraciones nuevas para instalar.

## 2. Obtener el código

En el servidor o estación de preparación, sustituyendo la URL autorizada:

~~~sh
git clone <URL_DEL_REPOSITORIO_SNIFF>
cd SNIFF
~~~

Este es un paso para el instalador; no publica cambios en GitHub.
No copiar venv, node_modules, .env, logs ni evidencias del equipo de desarrollo.

## 3. Crear PostgreSQL vacío

Desde psql, conectado como administrador a la base de mantenimiento, elegir los
nombres institucionales. Ejemplo de nombres, sin contraseña predeterminada:

~~~sql
CREATE ROLE sniff_app LOGIN;
\password sniff_app
CREATE DATABASE sniff_institucional OWNER sniff_app;
~~~

El comando interactivo \password pide la contraseña sin escribirla en este
documento. Configurar autenticación y acceso de red en PostgreSQL según las
políticas del servidor. La cuenta debe poder crear las tablas, índices y
secuencias en el esquema de su base; no necesita ser superusuario.
No apuntar esta instalación a la base sniff_db del equipo de desarrollo.

## 4. Backend: entorno y dependencias

Desde backend:

~~~sh
python -m venv venv
~~~

Activar en PowerShell:

~~~powershell
.\venv\Scripts\Activate.ps1
~~~

O en Linux:

~~~sh
. venv/bin/activate
~~~

Con el entorno activado:

~~~sh
python -m pip install -r requirements.txt
~~~

Si el entorno no dispone de ruedas binarias compatibles, revisar la plataforma
y las dependencias de compilación antes de instalar. No reutilizar el venv de
otra computadora.

## 5. Variables de entorno

Copiar backend/.env.example a backend/.env y editarlo en el servidor.
Las variables del proceso tienen prioridad sobre .env.

| Variable | Uso |
|---|---|
| SECRET_KEY | Clave privada, aleatoria, propia de esta instalación. Obligatoria. |
| DEBUG | True solo para desarrollo; False al publicar. |
| DB_NAME, DB_USER, DB_PASSWORD | Base nueva, usuario y contraseña elegidos. |
| DB_HOST, DB_PORT | Dirección y puerto de PostgreSQL. |
| DB_SSLMODE | Opcional: política TLS de PostgreSQL; coordinar certificados. |
| ALLOWED_HOSTS | Hosts del backend separados por comas, sin esquema ni ruta. No usar * como solución de instalación. |
| CORS_ALLOWED_ORIGINS | Orígenes del navegador autorizados, con http/https y puerto cuando proceda; separados por comas. |
| CSRF_TRUSTED_ORIGINS | Orígenes confiables adicionales para formularios/sesión, por ejemplo el administrador Django detrás de un proxy. No desactiva CSRF. |
| STATIC_ROOT, MEDIA_ROOT | Rutas absolutas o relativas a backend. Por defecto staticfiles y media. |
| STATIC_URL, MEDIA_URL | Prefijos; por defecto /static/ y /media/. MEDIA_URL no habilita acceso público. |
| SECURE_SSL_REDIRECT | True al servir mediante HTTPS correctamente configurado. |
| SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE | True en HTTPS institucional. |
| TRUST_X_FORWARDED_PROTO | True solo si un proxy confiable elimina/reemplaza la cabecera y comunica el esquema real. |
| USE_X_FORWARDED_HOST | Solo si la arquitectura necesita y valida esa cabecera. Por defecto False. |
| SECURE_HSTS_SECONDS | 0 durante puesta en marcha; definir duración después de comprobar HTTPS. |
| SECURE_HSTS_INCLUDE_SUBDOMAINS, SECURE_HSTS_PRELOAD | False salvo decisión explícita que abarque todos los subdominios y los requisitos de preload. |
| DRF_NUM_PROXIES | Cantidad real de proxies de confianza; 0 sin proxy. |
| LIMITE_LOGIN_IP, LIMITE_LOGIN_USUARIO | Límites de intentos; valores de ejemplo incluidos. |
| LIMITE_RESTABLECIMIENTO_IP, LIMITE_RESTABLECIMIENTO_IDENTIFICADOR | Límites de solicitudes de restablecimiento. |
| SNIFF_LOAD_DOTENV | Opcional, False para impedir lectura de .env; útil para verificaciones aisladas. |

Una clave puede generarse en el servidor mediante un gestor de secretos o con:

~~~sh
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
~~~

Guardar el resultado únicamente en el entorno privado; no pegarlo en Git,
capturas, documentación ni reportes. Las opciones de HTTPS no crean certificados
ni configuran el proxy.

## 6. Crear estructura y catálogos

Con .env apuntando exclusivamente a la nueva base:

~~~sh
python manage.py check
python manage.py migrate
python manage.py cargar_catalogos
~~~

El orden es importante: primero todas las migraciones, después catálogos.
Las migraciones incluyen la configuración de cinco días y el estado Sin registro.
El comando crea los cuatro roles actuales, frecuencias, tipos de cálculo,
fuentes, estados y área inicial. No crea usuarios ni datos de demostración.

Se puede repetir cargar_catalogos sin duplicar registros. Los roles ya existentes
conservan estado, descripción y usuarios; Supervisor no se crea en una base
nueva y, si ya existía, no se borra ni se reactiva. Un Supervisor activo genera
aviso para revisión. Los roles heredados no se reasignan desde este comando:
la adaptación histórica pertenece a las migraciones.

El comando conserva su comportamiento previo de actualizar descripciones/estado
de las frecuencias conocidas y desactivar Diaria/Semanal si existían. Por eso
no usarlo como mantenimiento general sin revisar personalizaciones.

No ejecutar comandos de rangos de prueba o recalcular mediciones como requisito
de instalación. Los períodos y las metas se generan por el flujo normal cuando
corresponde; no requieren cargar mediciones de ejemplo.

## 7. Administrador inicial

~~~sh
python manage.py createsuperuser
~~~

Elegir usuario, correo solicitado por Django y contraseña institucional.
No hay contraseñas predeterminadas ni cuentas creadas por el repositorio.

Entrar en /admin/ y editar ese usuario:
1. Completar el campo propio correo de SNIFF con un correo institucional único.
   createsuperuser usa el campo heredado email; no completa automáticamente correo.
2. Asignar el rol Administrador del sistema.
3. Confirmar estado e is_active activos. Mantener los permisos técnicos del
   superusuario solo en la cuenta administradora que los requiera.

Completar correo antes de crear otro superusuario, porque es único.
El superusuario sin rol permite el acceso técnico inicial a Django Admin,
pero el menú Vue exige el rol de aplicación correcto.

Desde la gestión de usuarios, crear las cuentas institucionales necesarias para
Administrador de planificación, Ejecutor operativo y Usuario de consulta.
La administración del sistema no sustituye los permisos de planificación.
No cambiar contraseñas mediante SQL ni compartir una contraseña predeterminada.

## 8. Desarrollo local

Con backend configurado, DEBUG=True y opciones HTTPS desactivadas:

~~~sh
python manage.py runserver
~~~

En otra terminal, desde frontend:

~~~sh
npm ci
npm run dev
~~~

Sin variable de frontend, desarrollo usa http://127.0.0.1:8000/api/.
Para otro backend, copiar frontend/.env.example a frontend/.env.local y ajustar
VITE_API_BASE_URL. Reiniciar Vite tras cambiarla.

runserver, el servidor de desarrollo de Vite y vite preview no son servidores
de producción.

## 9. Compilar y publicar

Antes de compilar, configurar VITE_API_BASE_URL en el entorno de compilación
o en frontend/.env.production.local:

~~~dotenv
VITE_API_BASE_URL=/api/
~~~

Usar /api/ si el servidor HTTP enruta ese prefijo al backend del mismo origen.
Si la API tiene otro origen, usar su URL completa terminada en /api/, y
autorizar el origen del frontend mediante CORS. No es necesario un dominio
concreto: se decide en el servidor institucional.

Desde frontend:

~~~sh
npm ci
npm run build
~~~

El resultado es frontend/dist. La variable se incorpora durante la compilación:
cambiar el .env del backend o del servidor después no modifica un bundle ya
generado. Volver a compilar tras cambiar la URL. Ninguna variable VITE_* es secreta.

Configurar el servidor HTTP para:
- Servir dist y devolver index.html para rutas de navegación SPA.
- Enrutar /api/ y /admin/ al servidor WSGI antes de aplicar ese fallback.
- Servir STATIC_URL desde STATIC_ROOT.
- No servir MEDIA_ROOT públicamente: las evidencias se descargan mediante
  endpoints Django autenticados. Respaldar esa carpeta como datos privados.

Desde backend, con las rutas institucionales configuradas:

~~~sh
python manage.py collectstatic --noinput
python manage.py check --deploy
~~~

La cuenta del backend debe poder escribir en MEDIA_ROOT y en logs; la cuenta que
ejecuta collectstatic necesita escritura en STATIC_ROOT. Conservar permisos
restrictivos en .env y respaldos.

Ejecutar config.wsgi:application mediante el servidor WSGI elegido e instalar
ese servidor dentro del entorno del servidor institucional. Como referencias:
Gunicorn en plataformas compatibles o Waitress en Windows; son opciones, no
dependencias instaladas automáticamente. Definir procesos, arranque, reinicio,
TLS, proxy y monitoreo con el equipo de infraestructura.

Ejemplos opcionales para ejecutar manualmente en el SERVIDOR, con venv activo;
elegir uno y ajustar dirección/puerto a la arquitectura. No ejecutarlos para
instalar servicios en la computadora de desarrollo:

Linux/plataforma compatible con Gunicorn:

~~~sh
python -m pip install gunicorn
gunicorn --bind 127.0.0.1:8000 config.wsgi:application
~~~

Windows/plataforma compatible con Waitress:

~~~powershell
python -m pip install waitress
waitress-serve --listen=127.0.0.1:8000 config.wsgi:application
~~~

Estos comandos no crean un servicio persistente. El equipo institucional debe
fijar la versión del servidor elegido y configurar su arranque supervisado.
El enlace de ejemplo es privado para un proxy local; otro diseño requiere
ajustar interfaz, firewall y confianza de cabeceras.

Corregir las advertencias de check --deploy según la arquitectura. HSTS con
subdominios y preload no debe activarse solo para silenciar avisos. La caché
actual de límites es local por proceso; varios workers requieren evaluar una
caché compartida. No habilitar cabeceras de proxy si se puede llegar al backend
por una ruta que permita falsificarlas.

## 10. Verificación y operación

- Comprobar check, migraciones aplicadas y los cuatro roles activos.
- Iniciar sesión con cada perfil y verificar separación de permisos.
- Crear un plan de validación y recorrer autorización de KPI y registro de
  medición en un período permitido.
- Verificar evidencias autenticadas, reportes PDF y rutas al recargar Vue.
- Revisar zona horaria America/Guatemala y persistencia de media.
- Definir respaldo coordinado de PostgreSQL y media; ensayar restauración.
- No copiar datos de demostración ni cuentas personales para inicializar.

Los plazos y reglas C2 no se cambian en esta preparación de instalación.
Para períodos iniciados desde 01/11/2026 rigen cinco días hábiles y ampliación
hasta diez hábiles totales; los anteriores conservan el cómputo calendario.

## 11. Tareas automáticas (configuración posterior)

Consultar [TAREAS_PROGRAMADAS.md](backend/docs/TAREAS_PROGRAMADAS.md).
La entrega NO activa tareas. Solo después de validar datos, respaldos y una
simulación en el servidor institucional, configurar ejecución diaria a las
00:15 de Guatemala, la cuenta de servicio y la captura de logs. Si el servidor
usa otra zona horaria, ajustar el programador: la variable TZ de Django no
cambia por sí sola la hora de disparo de cron.

## 12. Pruebas y límites de validación

Las pruebas SQLite se ejecutan sin .env ni conexión a PostgreSQL:

~~~sh
python manage.py test apps.indicadores.tests_instalacion --settings=config.settings_pruebas_aisladas --noinput
~~~

Desde frontend: npm test y npm run build.

Estas pruebas no certifican migraciones ni bloqueos de PostgreSQL. Para
aceptación institucional, usar una base PostgreSQL VACÍA, independiente,
creada para validación; apuntar un entorno privado separado a ella, ejecutar
migrate, cargar_catalogos dos veces y comprobar roles y administrador.
No hacerlo sobre sniff_db ni usar --fake. La revisión de entrega informa
por separado si pudo realizarse esa prueba.

## 13. Archivos privados y publicación

Versionar código, migraciones, requisitos, lockfile, ejemplos sin valores
secretos y documentación. No publicar .env, contraseñas, tokens, claves TLS,
respaldos, evidencias ni logs. .gitignore no retira secretos ya publicados:
si ocurriera una exposición, rotarlos y coordinar la revisión del historial.
No se requiere publicar dist: puede compilarse en el proceso de entrega.


### Resultado de la preparación local (26/10/2026)

- 239 pruebas backend aprobadas en SQLite en memoria; incluyen inicialización
  doble de catálogos, administrador con credencial generada solo en la prueba,
  configuración y regresiones de plazos, C2, Dashboard, D2 y D5.
- 95 pruebas frontend aprobadas y compilación con URL de API alternativa
  comprobada en el bundle. Se regeneró después el bundle con configuración normal.
- check --deploy comprobado sin conexión a datos, con configuración HTTPS de
  prueba: permanecen W005 (HSTS para subdominios) y W021 (preload), desactivados
  deliberadamente hasta que infraestructura confirme su alcance.
- PostgreSQL vacío: NO verificado. La cuenta disponible no tiene permiso
  CREATEDB. No se migró ninguna base existente ni se modificó sniff_db.
  Debe completarse esta validación en una base temporal autorizada.
