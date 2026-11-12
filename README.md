# Práctica S2 - Ejecución reproducible con Docker y CRUD

**Materia:** Programación en la Nube (7-ITIL-A)  
**Universidad:** Universidad Internacional del Ecuador, sede Loja  
**Fecha de documentación:** 11/11/2026

## 1. Objetivo y relación con la práctica anterior

Reproducir dos servidores **Nginx** (`web_a`, `web_b`) publicados en los puertos **8080 y 8081**; un cliente Alpine (`client_a`) conectado a la red frontal y otro (`client_b`) inicialmente aislado en la red posterior. Este esquema parte de la práctica S2 documentada en `PN_S2_PE_INFORME.pdf` (05/11/2026).

**Ampliación de esta entrega:** el informe original solo mostraba Nginx, Alpine y redes. **No contenía API CRUD ni base de datos**. Para cumplir la nueva consigna se incorpora una API HTTP en Python, una base de datos SQLite persistente y una interfaz HTML compartida por ambos Nginx. No se atribuyen esos componentes al trabajo anterior.

## 2. Requisitos

- Docker Desktop (Windows, con motor Docker en funcionamiento) o Docker Engine en Linux.
- Docker Compose v2 (`docker compose version`).
- Git, si se desea clonar el repositorio.
- Navegador web o `curl` / `curl.exe` para las solicitudes CRUD.
- Puertos locales **8080** y **8081** disponibles (pueden cambiarse en `.env`).
- Solo para ejecutar las pruebas fuera de Docker: Python 3.10 o superior, sin dependencias externas.

Verificaciones iniciales:

```bash
docker --version
docker compose version
docker info
```

## 3. Estructura del proyecto

```text
practica_docker_crud/
├── .env.example           # Variables de ejemplo, sin claves reales
├── .gitignore             # Excluye .env, archivos SQLite y temporales
├── compose.yaml           # API, 2 Nginx, 2 Alpine, redes y volumen
├── README.md              # Este instructivo
├── api/
│   ├── Dockerfile         # Imagen Python de la API
│   ├── init_db.py         # Creación idempotente de tabla productos
│   └── server.py          # Endpoints CRUD
├── nginx/
│   └── default.conf       # Proxy HTTP /api/* hacia la API
├── web/
│   └── index.html         # Interfaz web sencilla para el CRUD
├── scripts/
│   └── verificar_local.py # Prueba real de API sin Docker
└── tests/
    └── test_crud.py       # Pruebas HTTP automatizadas
```

## 4. Obtener copia limpia y preparar variables

Desde el repositorio que se publique, clonar y entrar al directorio:

```bash
git clone URL_REAL_DEL_REPOSITORIO
cd practica_docker_crud
```

> **Importante:** `URL_REAL_DEL_REPOSITORIO` es un marcador de posición. Reemplazarlo por la URL real al publicar; no se proporcionó un repositorio existente con esta consigna. También se puede probar directamente desde la carpeta descargada en el ZIP.

**PowerShell (Windows):**

```powershell
Copy-Item .env.example .env
```

**Terminal Linux/macOS o Git Bash:**

```bash
cp .env.example .env
```

Contenido propuesto:

```dotenv
WEB_A_PORT=8080
WEB_B_PORT=8081
DB_PATH=/data/app.db
```

`DB_PATH` es una ruta **interna del contenedor API**, no una ruta de Windows. No hay contraseñas reales: SQLite funciona sin usuario ni clave. El archivo `.env` queda excluido de Git; `.env.example` sí debe subirse.

## 5. Construcción, inicialización, inicio y detención

En la raíz del proyecto:

```bash
# 1) Verificar configuración y construir imagen de la API
docker compose config
docker compose build

# 2) Inicializar tabla productos (idempotente)
docker compose run --rm api python init_db.py

# 3) Levantar todos los servicios en segundo plano
docker compose up -d

# 4) Revisar estado y registros
docker compose ps
docker compose logs --tail=40 api
```

La API también ejecuta `init_db()` al arrancar. Por eso el paso 2 **puede repetirse** sin borrar los datos. El volumen Docker conserva los productos entre reinicios.

Abrir ambos servicios:

- <http://localhost:8080> (`web_a`)
- <http://localhost:8081> (`web_b`)
- <http://localhost:8080/health> (API y base de datos disponibles)

Los dos Nginx comparten la **misma API y base de datos**. Un producto creado en el puerto 8080 se verá también en el puerto 8081.

Comandos de administración:

```bash
docker compose stop       # Detiene, mantiene contenedores y volumen
docker compose start      # Reanuda servicios existentes
docker compose down       # Elimina contenedores y redes, MANTIENE volumen
docker compose up -d      # Recrea o inicia después de down
# CUIDADO: el siguiente comando BORRA los productos guardados:
docker compose down -v
```

## 6. Consultas al CRUD (GET, POST, PUT y DELETE)

**Linux, macOS y Git Bash con `curl`:**

```bash
# Salud (GET)
curl -i http://localhost:8080/health

# Listar (GET)
curl -i http://localhost:8080/api/productos

# Crear (POST): devuelve HTTP 201 y el nuevo id
curl -i -X POST http://localhost:8080/api/productos -H 'Content-Type: application/json' -d '{"nombre":"Cuaderno","precio":2.50}'

# Consultar un producto (GET), reemplazar 1 por el id devuelto
curl -i http://localhost:8080/api/productos/1

# Actualizar (PUT)
curl -i -X PUT http://localhost:8080/api/productos/1 -H 'Content-Type: application/json' -d '{"nombre":"Libro","precio":4.00}'

# Borrar (DELETE)
curl -i -X DELETE http://localhost:8080/api/productos/1

# Verificar eliminacion: se espera HTTP 404
curl -i http://localhost:8080/api/productos/1
```

**Windows PowerShell (evita conflictos de comillas entre PowerShell y `curl.exe`):**

```powershell
$base = 'http://localhost:8080/api/productos'
Invoke-RestMethod -Method Get -Uri 'http://localhost:8080/health'
Invoke-RestMethod -Method Get -Uri $base
$creado = Invoke-RestMethod -Method Post -Uri $base -ContentType 'application/json' -Body (@{nombre='Cuaderno';precio=2.5} | ConvertTo-Json -Compress)
$id = $creado.id
Invoke-RestMethod -Method Get -Uri "$base/$id"
Invoke-RestMethod -Method Put -Uri "$base/$id" -ContentType 'application/json' -Body (@{nombre='Libro';precio=4} | ConvertTo-Json -Compress)
Invoke-RestMethod -Method Delete -Uri "$base/$id"
```

Respuestas esperadas: `200` en lecturas, edición y eliminación correctas; `201` al crear; `400` con datos incorrectos; y `404` para un ID inexistente. Los ID pueden variar porque la base de datos persiste entre ejecuciones. En PowerShell, un código `404` provoca una excepción de `Invoke-RestMethod`, lo cual es esperado cuando el producto fue eliminado.

## 7. Pruebas de redes Docker y Alpine

`client_a` y ambos Nginx están en `lab_front`. `client_b` está solo en `lab_back` al principio. A diferencia del laboratorio original, Compose agrega un prefijo al nombre real de las redes.

```bash
# Comprobar contenedores y redes
docker compose ps
docker network ls

# cliente A -> ambos servidores (se espera HTML)
docker compose exec client_a wget -T 3 -qO- http://web_a:80
docker compose exec client_a wget -T 3 -qO- http://web_b:80

# cliente B inicialmente aislado: se espera error 'bad address'
docker compose exec client_b wget -T 3 -qO- http://web_a:80

# Conectar client_b a la red frontal sin recrearlo
docker network connect practica-nube-crud_lab_front $(docker compose ps -q client_b)

# Ahora debe responder la página Nginx
docker compose exec client_b wget -T 3 -qO- http://web_a:80

# Consultar conexiones de la red
docker network inspect practica-nube-crud_lab_front
```

> El primer `wget` de `client_b` **debe fallar**: ese resultado muestra el aislamiento entre redes. Si el nombre ya resuelve, comprobar si se conectó antes a `lab_front`. Para volver al estado inicial, ejecutar `docker compose down` seguido de `docker compose up -d`. No asumir las IP internas, porque pueden cambiar.

## 8. Problemas frecuentes: causa y corrección

| Error / situación | Causa | Corrección |
|---|---|---|
| `wget: bad address 'web_a:80'` desde `client_b` | El contenedor está aislado en `lab_back`; no comparte red con Nginx. **Ocurrió en el informe base.** | `docker network connect practica-nube-crud_lab_front $(docker compose ps -q client_b)` y repetir `wget`. |
| `bind: address already in use` / puerto ocupado | Ya hay otro proceso o contenedor en 8080/8081. **Caso preventivo.** | Modificar `WEB_A_PORT=8090` o `WEB_B_PORT=8091` en `.env`; ejecutar `docker compose up -d`. |
| `Cannot connect to the Docker daemon` | Docker Desktop/Engine no está iniciado. **Caso preventivo.** | Iniciar Docker Desktop o servicio Docker; validar con `docker info`. |
| `no such service` al ejecutar Compose | Comando ejecutado fuera de la carpeta del proyecto. **Caso preventivo.** | Entrar a la carpeta que contiene `compose.yaml`. |
| La base aparece vacía después de detener | Se ejecutó `docker compose down -v`, que elimina el volumen. **Riesgo preventivo.** | Evitar `-v` si se necesitan conservar datos. |

## 9. Verificación desde una copia limpia

Prueba de referencia para quien reciba el repositorio:

1. Clonar una copia nueva, sin reutilizar archivos `.env` ni volúmenes creados antes.
2. Copiar `.env.example` a `.env`; ejecutar `docker compose config`, `build`, `run --rm api python init_db.py` y `up -d`.
3. Acceder a 8080/8081, probar CRUD, verificar el mismo producto en ambas interfaces.
4. Comprobar el aislamiento de `client_b` y conectar la red como indica la sección 7.
5. Registrar capturas o salidas de `docker compose ps`, `docker compose logs api`, `curl`, `wget` y `docker network inspect`.
6. Detener con `docker compose down`.

Adicionalmente, para probar únicamente la API sin Docker:

```bash
python scripts/verificar_local.py
python -m unittest discover -s tests -v
```

Las verificaciones locales **no sustituyen** la comprobación real del despliegue de Docker. En el informe de entrega se distingue expresamente qué se pudo comprobar y qué queda pendiente.

## 10. Alcance y seguridad

Ejemplo académico para ejecución **local**, no producción. Se publica solo en `127.0.0.1`, no incorpora autenticación, TLS ni endurecimiento de producción. No exponer el servicio a Internet. No subir `.env` ni archivos `.db` al repositorio.

**Referencia de base:** `PN_S2_PE_INFORME.pdf`, práctica S2 del 05/11/2026, secciones sobre imágenes Nginx/Alpine, redes `lab_front`/`lab_back`, puertos 8080/8081 y error de resolución de nombres.
