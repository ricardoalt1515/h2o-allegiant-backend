# 🐳 FastAPI Users Migration - Docker Workflow

## ✅ Preparación Completada

Los archivos están listos. FastAPI Users ya está en `requirements.txt` y se instalará automáticamente al reconstruir la imagen Docker.

---

## 🚀 Pasos de Migración (15 minutos)

### **Paso 1: Editar Migración Alembic** (2 min)

```bash
# Encontrar tu última migración
ls -lt alembic/versions/*.py | head -2

# Editar el archivo de migración
code alembic/versions/migrate_to_fastapi_users.py

# En línea 19, cambiar:
down_revision = None  # TODO

# Por el ID de tu última migración, ejemplo:
down_revision = '20251001_1407-0a96be64ebff'
```

---

### **Paso 2: Backup Base de Datos** (CRÍTICO) (3 min)

```bash
cd /Users/ricardoaltamirano/Developer/frontend/backend-h2o

# Asegúrate de que contenedores están corriendo
docker-compose ps

# Backup desde el contenedor Docker
docker-compose exec postgres pg_dump -U h2o_user h2o_allegiant > backup_antes_migracion_$(date +%Y%m%d).sql

# Verificar que el backup existe y tiene tamaño
ls -lh backup_*.sql
```

---

### **Paso 3: Reconstruir Imagen Docker** (3 min)

```bash
cd /Users/ricardoaltamirano/Developer/frontend/backend-h2o

# Detener contenedores actuales
docker-compose down

# Reconstruir imagen (instala FastAPI Users desde requirements.txt)
docker-compose build app

# Esto instala automáticamente:
# - fastapi-users[sqlalchemy]==13.0.0
# - fastapi-users-db-sqlalchemy==6.0.1
```

---

### **Paso 4: Iniciar Contenedores** (1 min)

```bash
# Iniciar todos los servicios
docker-compose up -d

# Verificar que todos están running
docker-compose ps

# Ver logs en tiempo real (opcional)
docker-compose logs -f app
```

---

### **Paso 5: Ejecutar Migración DENTRO del Contenedor** (2 min)

```bash
# Conectarse al contenedor de la app
docker-compose exec app bash

# ========================================
# DENTRO DEL CONTENEDOR:
# ========================================

# Ver estado actual de migraciones
alembic current

# Ver migraciones pendientes
alembic heads

# Ejecutar migración
alembic upgrade head

# Verificar que aplicó correctamente (debe mostrar: migrate_to_fastapi_users)
alembic current

# Salir del contenedor
exit
```

---

### **Paso 6: Verificar Base de Datos** (2 min)

```bash
# Conectar a PostgreSQL del contenedor
docker-compose exec postgres psql -U h2o_user -d h2o_allegiant

# ========================================
# DENTRO DE PostgreSQL:
# ========================================

# Ver estructura de tabla users
\d users

# ✅ Deberías ver estos cambios:
# - hashed_password (en vez de password_hash)
# - is_superuser (en vez de is_admin)
# - is_verified (nuevo campo)

# Verificar datos de usuarios
SELECT id, email, is_active, is_superuser, is_verified FROM users;

# Salir
\q
```

---

### **Paso 7: Probar Backend** (3 min)

```bash
# Ver logs en tiempo real
docker-compose logs -f app

# En otra terminal, probar endpoints:

# 1. Health check
curl http://localhost:8000/ping

# 2. Ver documentación interactiva
open http://localhost:8000/api/v1/docs

# 3. Probar nuevo endpoint de login
# Reemplazar con un email real de tu base de datos
curl -X POST http://localhost:8000/api/v1/auth/jwt/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=tu-email@ejemplo.com&password=tu-password"

# ✅ Deberías recibir:
# {
#   "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
#   "token_type": "bearer"
# }

# 4. Probar nuevo endpoint de logout
curl -X POST http://localhost:8000/api/v1/auth/jwt/logout \
  -H "Authorization: Bearer TU_TOKEN_AQUI"

# ✅ Deberías recibir: 204 No Content
```

---

## 🎯 Nuevos Endpoints Disponibles

### **Autenticación:**
```bash
# Login (CAMBIÓ de /auth/login a /auth/jwt/login)
POST /api/v1/auth/jwt/login

# Logout (NUEVO - ahora funciona correctamente)
POST /api/v1/auth/jwt/logout
```

### **Registro:**
```bash
# Register (sin cambios)
POST /api/v1/auth/register
```

### **Perfil:**
```bash
# Get current user (sin cambios)
GET /api/v1/auth/me

# Update profile (sin cambios)
PATCH /api/v1/auth/me

# Delete account (NUEVO)
DELETE /api/v1/auth/me
```

### **Password Reset (NUEVO):**
```bash
# Request reset
POST /api/v1/auth/forgot-password

# Reset with token
POST /api/v1/auth/reset-password
```

### **Email Verification (NUEVO):**
```bash
# Request verification token
POST /api/v1/auth/request-verify-token

# Verify email
POST /api/v1/auth/verify
```

---

## 🐛 Troubleshooting Docker

### **Error: "Cannot connect to Docker daemon"**
```bash
# Iniciar Docker Desktop
open -a Docker

# Esperar a que inicie y reintentar
docker-compose ps
```

### **Error: "Port 8000 already in use"**
```bash
# Ver qué está usando el puerto
lsof -i :8000

# Detener el proceso
kill -9 <PID>

# O cambiar puerto en docker-compose.yml
ports:
  - "8001:8000"  # Local:Container
```

### **Error: "Migration failed"**
```bash
# Ver logs detallados
docker-compose logs app

# Conectarse al contenedor para debug
docker-compose exec app bash

# Ver estado de Alembic
alembic history
alembic current

# Ver archivo de migración
cat alembic/versions/migrate_to_fastapi_users.py
```

### **Error: "Module 'fastapi_users' not found"**
```bash
# Verificar que se instaló en la imagen
docker-compose exec app pip list | grep fastapi-users

# Si no aparece, reconstruir imagen sin cache
docker-compose build --no-cache app
```

### **Revertir Migración si algo sale mal:**
```bash
# Conectarse al contenedor
docker-compose exec app bash

# Revertir migración (DENTRO del contenedor)
alembic downgrade -1

# Salir
exit

# Restaurar backup
docker-compose exec -T postgres psql -U h2o_user -d h2o_allegiant < backup_antes_migracion_20251002.sql
```

---

## 📊 Verificación Completa

### **Checklist Backend:**
- [ ] Contenedores corriendo (`docker-compose ps`)
- [ ] Migración aplicada (`alembic current` muestra `migrate_to_fastapi_users`)
- [ ] Tabla users actualizada (campos: `hashed_password`, `is_superuser`, `is_verified`)
- [ ] Health check funciona (`curl http://localhost:8000/ping`)
- [ ] Login funciona (`POST /api/v1/auth/jwt/login`)
- [ ] Logout funciona (`POST /api/v1/auth/jwt/logout`)
- [ ] Docs accesibles (`http://localhost:8000/api/v1/docs`)

### **Logs a Revisar:**
```bash
# Ver logs de inicio
docker-compose logs app | grep "✅"

# Deberías ver:
# ✅ Registered JWT auth router: /auth/jwt/login, /auth/jwt/logout
# ✅ Registered register router: /auth/register
# ✅ Registered users router: /auth/me
# ✅ Registered password reset router
# ✅ Registered email verification router
# ✅ All API routes registered
# ✅ Application started successfully
```

---

## 🎉 ¡Listo!

El backend está migrado a FastAPI Users. Próximo paso:
- **Actualizar frontend** para usar los nuevos endpoints (ver `MIGRACION_FASTAPI_USERS.md`)

---

## 📝 Comandos Útiles

```bash
# Ver logs en tiempo real
docker-compose logs -f app

# Reiniciar solo el contenedor app
docker-compose restart app

# Reconstruir y reiniciar
docker-compose up -d --build app

# Ver todos los contenedores
docker-compose ps

# Conectarse al contenedor app
docker-compose exec app bash

# Conectarse a PostgreSQL
docker-compose exec postgres psql -U h2o_user -d h2o_allegiant

# Ver logs de errores solamente
docker-compose logs app | grep -i error

# Detener todo
docker-compose down

# Detener y eliminar volúmenes (CUIDADO: borra la DB)
docker-compose down -v
```
