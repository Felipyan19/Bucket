# Mini Bucket (FastAPI)

Microservicio en Python con FastAPI que simula un bucket básico: subir, listar, descargar y eliminar archivos. 
Permite expiración opcional: si envías el campo `exp` (en segundos) el archivo se elimina automáticamente cuando vence; si no lo envías, queda indefinido.

## Requisitos
- Docker + Docker Compose

## Levantar el servicio
```bash
docker compose up --build
```

El servicio queda en `http://localhost:2020`.

## Swagger / Documentación interactiva
FastAPI expone documentación automática:
- Swagger UI: `http://localhost:2020/docs`
- ReDoc: `http://localhost:2020/redoc`

## Endpoints
- `POST /files` → subir archivo (multipart/form-data)
  - Campos:
    - `file` (obligatorio)
    - `exp` (opcional, segundos)
- `GET /files` → listar archivos
- `GET /files/{id}` → descargar archivo
- `GET /files/by-name/{titulo}` → listar archivos por título (mismo nombre)
- `GET /files/by-name/{titulo}/download` → descargar por título (usa el más reciente)
- `DELETE /files/{id}` → eliminar archivo
- `DELETE /files/by-name/{titulo}` → eliminar por título (borra todos los que coinciden)

## Ejemplos con curl
Subir sin expiración:
```bash
curl -F "file=@/ruta/archivo.pdf" http://localhost:2020/files
```

Subir con expiración (por ejemplo 60 segundos):
```bash
curl -F "file=@/ruta/archivo.pdf" -F "exp=60" http://localhost:2020/files
```

Listar:
```bash
curl http://localhost:2020/files
```

Descargar:
```bash
curl -L -o archivo.pdf http://localhost:2020/files/<id>
```

Listar por título:
```bash
curl http://localhost:2020/files/by-name/archivo.pdf
```

Descargar por título (más reciente):
```bash
curl -L -o archivo.pdf http://localhost:2020/files/by-name/archivo.pdf/download
```

Eliminar:
```bash
curl -X DELETE http://localhost:2020/files/<id>
```

Eliminar por título (borra todos los que coinciden):
```bash
curl -X DELETE http://localhost:2020/files/by-name/archivo.pdf
```

## Datos persistentes
Se guardan en un volumen Docker llamado `bucket_data`.
