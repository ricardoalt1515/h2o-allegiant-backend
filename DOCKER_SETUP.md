# 🐳 Docker Setup - H2O Allegiant Backend

Setup completo con Docker Compose. Todo pre-configurado y listo para usar.

---

## 🚀 Quick Start (3 pasos)

### 1. Agregar tu OpenAI API Key

```bash
# Crear .env con tu API key
echo "OPENAI_API_KEY=sk-tu-api-key-aqui" > .env
```

### 2. Iniciar todo con Docker Compose

```bash
docker-compose up --build
```

### 3. Ejecutar migraciones

En otra terminal (mientras los contenedores están corriendo):

```bash
# Ejecutar migraciones
docker-compose exec app alembic upgrade head

# O todo en un comando
docker-compose exec app sh -c "alembic upgrade head"
```

**¡Listo!** Backend corriendo en:
- 🌐 **API**: http://localhost:8000
- 📚 **Docs**: http://localhost:8000/api/v1/docs
- ❤️ **Health**: http://localhost:8000/health

---

## 📦 Lo que Incluye

```
docker-compose.yml
├── app (Backend FastAPI)
│   ├── Puerto: 8000
│   ├── Auto-reload: ✅
│   ├── Volumes: código + storage + logs
│   └── Depends: postgres + redis
│
├── postgres (PostgreSQL 14)
│   ├── Puerto: 5432
│   ├── Database: h2o_allegiant
│   ├── User: h2o_user
│   └── Volume: postgres_data (persistente)
│
└── redis (Redis 6)
    ├── Puerto: 6379
    ├── Volume: redis_data (persistente)
    └── Health check: ✅
```

---

## 🔧 Comandos Útiles

### Iniciar servicios
```bash
# Primera vez (con build)
docker-compose up --build

# Siguientes veces
docker-compose up

# En background
docker-compose up -d
```

### Ver logs
```bash
# Todos los servicios
docker-compose logs -f

# Solo backend
docker-compose logs -f app

# Solo base de datos
docker-compose logs -f postgres
```

### Detener servicios
```bash
# Detener (mantiene volúmenes)
docker-compose down

# Detener y eliminar volúmenes (⚠️ borra la DB)
docker-compose down -v
```

### Ejecutar comandos en el contenedor
```bash
# Shell en el contenedor
docker-compose exec app bash

# Ejecutar comando directo
docker-compose exec app python -c "print('Hello')"

# Ejecutar migraciones
docker-compose exec app alembic upgrade head

# Crear nueva migración
docker-compose exec app alembic revision --autogenerate -m "Add field"
```

### Reiniciar solo un servicio
```bash
docker-compose restart app
docker-compose restart postgres
docker-compose restart redis
```

### Ver estado de servicios
```bash
docker-compose ps
```

### Limpiar todo
```bash
# Detener y eliminar todo
docker-compose down -v

# Limpiar imágenes antiguas
docker image prune -a
```

---

## 🗄️ Database Management

### Acceder a PostgreSQL
```bash
# Dentro del contenedor
docker-compose exec postgres psql -U h2o_user -d h2o_allegiant

# Desde tu máquina (si tienes psql instalado)
psql -h localhost -U h2o_user -d h2o_allegiant
```

### Backup de la base de datos
```bash
# Crear backup
docker-compose exec postgres pg_dump -U h2o_user h2o_allegiant > backup.sql

# Restaurar backup
docker-compose exec -T postgres psql -U h2o_user h2o_allegiant < backup.sql
```

### Reset completo de la DB
```bash
# Detener todo
docker-compose down -v

# Iniciar de nuevo
docker-compose up -d

# Esperar 10 segundos
sleep 10

# Ejecutar migraciones
docker-compose exec app alembic upgrade head
```

---

## 🔐 Variables de Entorno

### Archivo `.env` (solo necesitas esto)
```bash
OPENAI_API_KEY=sk-tu-api-key-aqui
```

### Variables en `docker-compose.yml` (ya configuradas)

**Application:**
- `ENVIRONMENT=development`
- `DEBUG=true`
- `APP_NAME=H2O Allegiant API`

**Database:**
- `POSTGRES_USER=h2o_user`
- `POSTGRES_PASSWORD=h2o_password`
- `POSTGRES_SERVER=postgres`
- `POSTGRES_DB=h2o_allegiant`

**Redis:**
- `REDIS_HOST=redis`
- `REDIS_PORT=6379`

**Security:**
- `SECRET_KEY=dev-secret-key...` (cambiar en producción)

**Storage:**
- `USE_LOCAL_STORAGE=true`
- `LOCAL_STORAGE_PATH=/app/storage`

---

## 🧪 Testing

### Probar Health Check
```bash
curl http://localhost:8000/health
```

### Probar registro de usuario
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123",
    "first_name": "Test",
    "last_name": "User"
  }'
```

### Abrir Swagger Docs
```
http://localhost:8000/api/v1/docs
```

---

## 📊 Volúmenes Persistentes

Los datos persisten entre reinicios:

```
postgres_data/     # Base de datos PostgreSQL
redis_data/        # Cache Redis
storage/           # Archivos subidos
logs/              # Logs de la aplicación
```

Para eliminar los volúmenes:
```bash
docker-compose down -v
```

---

## 🔄 Workflow de Desarrollo

### 1. Desarrollo Normal
```bash
# Iniciar servicios
docker-compose up

# Editar código en tu editor
# Los cambios se reflejan automáticamente (auto-reload)

# Ver logs para debugging
docker-compose logs -f app
```

### 2. Agregar Dependencias
```bash
# Editar requirements.txt o pyproject.toml

# Rebuild
docker-compose up --build
```

### 3. Cambios en la Base de Datos
```bash
# Editar modelos en app/models/

# Crear migración
docker-compose exec app alembic revision --autogenerate -m "Descripción"

# Aplicar migración
docker-compose exec app alembic upgrade head
```

---

## 🐛 Troubleshooting

### Error: "Port 8000 already in use"
```bash
# Encontrar proceso usando el puerto
lsof -ti:8000

# Matar el proceso
kill -9 $(lsof -ti:8000)

# O cambiar el puerto en docker-compose.yml
ports:
  - "8001:8000"  # Usar puerto 8001 externamente
```

### Error: "database does not exist"
```bash
# Recrear base de datos
docker-compose down -v
docker-compose up -d
sleep 10
docker-compose exec app alembic upgrade head
```

### Error: "Redis connection refused"
```bash
# Verificar que Redis esté corriendo
docker-compose ps redis

# Ver logs de Redis
docker-compose logs redis

# Reiniciar Redis
docker-compose restart redis
```

### Error: OpenAI API
```bash
# Verificar que la API key esté configurada
docker-compose exec app env | grep OPENAI

# Agregar API key
echo "OPENAI_API_KEY=sk-tu-key" > .env
docker-compose restart app
```

### Contenedor no inicia
```bash
# Ver logs completos
docker-compose logs app

# Verificar healthchecks
docker-compose ps

# Entrar al contenedor para debugging
docker-compose run --rm app bash
```

---

## 🚀 Producción

Para producción, crear `docker-compose.prod.yml`:

```yaml
services:
  app:
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - SECRET_KEY=${SECRET_KEY}  # Desde .env secreto
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    command:
      [
        "gunicorn",
        "app.main:app",
        "--workers", "4",
        "--worker-class", "uvicorn.workers.UvicornWorker",
        "--bind", "0.0.0.0:8000",
        "--log-level", "info",
        "--timeout", "180",
      ]
```

Usar con:
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up
```

---

## 📋 Checklist Pre-Deploy

- [ ] `.env` con `OPENAI_API_KEY` configurado
- [ ] Base de datos iniciada y migraciones aplicadas
- [ ] Redis corriendo y accesible
- [ ] Health check retorna 200: http://localhost:8000/health
- [ ] Swagger docs accesible: http://localhost:8000/api/v1/docs
- [ ] Puedes crear usuario y hacer login
- [ ] Storage directory tiene permisos correctos

---

## 🎉 Ventajas de Docker Setup

✅ **No necesitas instalar nada** (solo Docker)  
✅ **Mismo ambiente para todos** (dev, staging, prod)  
✅ **Base de datos aislada** (no conflictos con otros proyectos)  
✅ **Auto-reload** durante desarrollo  
✅ **Un comando para iniciar todo** (`docker-compose up`)  
✅ **Fácil de resetear** (`docker-compose down -v`)  
✅ **Logs centralizados** (`docker-compose logs`)  

---

¿Necesitas ayuda? Revisa:
- `docker-compose logs -f app` - Ver qué está pasando
- `docker-compose ps` - Ver estado de servicios
- http://localhost:8000/api/v1/docs - Probar endpoints

¡Happy coding! 🚀
