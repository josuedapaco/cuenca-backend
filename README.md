# Cuenca Coffee Shop — backend

API en Python/FastAPI para el sitio cuencany.com.

## Desarrollo

Python 3.11 o superior.

~~~sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
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

El [Dockerfile](Dockerfile) escucha en **8000** y ejecuta como usuario UID 1000.

Variables:

- DATABASE_PATH=/app/data/cuenca.sqlite
- PUBLIC_ORIGINS=https://cuencany.com,https://www.cuencany.com
- ADMIN_API_KEY: clave aleatoria configurada en el servidor.

Monta un volumen persistente en **/app/data**. El frontend, en su propio contenedor Nginx (8080), redirige /api al backend por DNS interno. No necesitas exponer la base de datos ni un dominio separado para la API.

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
