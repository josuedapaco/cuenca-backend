# Cuenca Coffee Shop — backend

API en Python/FastAPI para el sitio cuencany.com.

## Desarrollo

Python 3.11 o superior.

~~~sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
PUBLIC_ORIGINS=http://localhost:5173,http://127.0.0.1:5173 uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
~~~

python -m pytest -q verifica el catálogo completo, validación de consultas, persistencia SQLite, acceso administrativo y protección de origen.

## API

| Método | Ruta | Función |
| --- | --- | --- |
| GET | /api/health | Estado del servicio y acceso a SQLite |
| GET | /api/menu | Carta bilingüe de 191 opciones |
| GET | /api/restaurant | Datos de contacto confirmados |
| POST | /api/catering | Guardar consulta de eventos con consentimiento |
| GET | /api/admin/catering | Consultas recientes; requiere Bearer token |

El formulario de catering no confirma pedidos ni reservas. Guarda los datos para revisión y coordinación telefónica; no envía correos ni mensajes porque no se proporcionó un receptor.

ADMIN_API_KEY protege la consulta administrativa. Si no está configurada, el acceso administrativo permanece cerrado. Nunca incluyas esa clave en el frontend.

Las solicitudes se limitan a 5 por hora por IP para esta instancia. Es un límite en memoria, no un sistema distribuido; para mayor tráfico aplica también límites en el proxy. El cuerpo de POST se limita a 16 KB. CORS y la validación de origen usan PUBLIC_ORIGINS.

## Docker / EasyPanel

El [Dockerfile](Dockerfile) escucha en **84** y ejecuta como usuario UID 1000.

Variables:

- DATABASE_PATH=/app/data/cuenca.sqlite
- PUBLIC_ORIGINS=https://cuencany.com,https://www.cuencany.com
- ADMIN_API_KEY: clave aleatoria configurada en el servidor.

Monta un volumen persistente en **/app/data**. El frontend, en su propio contenedor Nginx (84), redirige /api al backend por DNS interno. No necesitas exponer la base de datos ni un dominio separado para la API.

Build Path /; Dockerfile Dockerfile. Conecta GitHub al repositorio privado josuedapaco/cuenca-backend, rama main.

## Menú y datos del restaurante

app/menu.json contiene nombres, traducciones, tamaños y precios del dossier del propietario. Están los 141 platos originales numerados y sus complementos. Precios faltantes se representan con una lista vacía y el frontend muestra “Consultar”.

Actualiza también el archivo de respaldo public/menu.json en cuenca-frontend si modificas el catálogo. No se inventaron horarios generales, tiempos al aeropuerto, opiniones ni condiciones de entrega.

## Consultar consultas guardadas

Desde una terminal con la clave configurada:

~~~sh
curl -H "Authorization: Bearer $ADMIN_API_KEY" https://cuencany.com/api/admin/catering
~~~

Datos personales guardados: nombre, teléfono, correo opcional, fecha, invitados, platos, notas, idioma y fecha de registro. Haz copias de SQLite y conserva su volumen entre despliegues.

## Asistente de carta OpenAI

`POST /api/chat` recibe `message` (2–500 caracteres), `history` (hasta tres preguntas previas de máximo 500 caracteres) y `language` (`es`/`en`). Usa Responses API con Structured Outputs. El modelo solo puede seleccionar hasta tres IDs del catálogo: nombres y precios se recuperan del JSON del servidor; no se publica texto libre del modelo. Los IDs desconocidos o duplicados se rechazan. No inventa precios faltantes ni ofrece pedidos o reservas. Preferencias y presupuestos se proporcionan al selector; la selección sigue siendo probabilística. Para alergias o restricciones dietéticas se deriva a consulta telefónica sin recomendar seguridad alimentaria.

En EasyPanel → backcuencany → Environment añade:
```env
OPENAI_API_KEY=TU_CLAVE_SOLO_EN_EL_SERVIDOR
OPENAI_MODEL=gpt-4.1-mini
CHAT_HOURLY_LIMIT=10
CHAT_DAILY_LIMIT=100
```
Guarda y despliega el backend. No añadas la clave al frontend, a GitHub ni a variables `VITE_`. Una clave ausente devuelve 503 y la web informa que el asistente aún no está disponible. Modelo configurable; debe soportar Responses API y Structured Outputs.

Los límites se guardan en SQLite y sobreviven a reinicios: diez llamadas por IP/hora y cien llamadas por día para toda la instancia por defecto. Si el proxy no transmite una IP fiable se aplica un límite compartido más conservador. Máximo tres llamadas concurrentes y tiempo de espera limitado. Configura también límites de gasto en tu proyecto OpenAI. Una llamada fallida cuenta para el límite.

Las preguntas y hasta tres preguntas previas se envían a OpenAI con `store:false`. No se guardan conversaciones en la base local ni se envían consultas privadas de catering. El usuario ve una nota y debe evitar datos personales; `store:false` no sustituye las políticas de retención del proveedor. No se publica el detalle de errores del proveedor.

Pruebas: `python -m pytest -q`. La integración con OpenAI se verifica con transporte simulado; una prueba real requiere que el propietario configure su clave en el servidor.
