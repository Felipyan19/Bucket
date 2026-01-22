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
- `DELETE /files/{id}` → eliminar archivo

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

Eliminar:
```bash
curl -X DELETE http://localhost:2020/files/<id>
```

## Datos persistentes
Se guardan en un volumen Docker llamado `bucket_data`.
