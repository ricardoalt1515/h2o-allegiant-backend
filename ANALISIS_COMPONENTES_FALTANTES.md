# 📋 Análisis de Componentes Faltantes

**Fecha:** 2025-09-30  
**Backend Origen:** backend-chatbot  
**Backend Destino:** backend-h2o

---

## ✅ Lo que YA Tenemos Migrado

### Core & Database
- ✅ Config (settings con Pydantic)
- ✅ Database (SQLAlchemy async)
- ✅ Security (JWT + password hashing)
- ✅ Models (7 modelos completos)
- ✅ Schemas (20+ schemas Pydantic)

### AI System
- ✅ Proposal Agent (Pydantic-AI)
- ✅ Proven Cases Tool
- ✅ Data directory (casos probados)
- ✅ Prompt engineering

### Services
- ✅ Proposal Service (orchestration)
- ✅ Cache Service (Redis)
- ✅ Document Processor
- ✅ S3 Service
- ✅ Storage Service

### Visualization
- ✅ PDF Generator (WeasyPrint)
- ✅ Charts Generator (Plotly + Matplotlib)
- ✅ Process Diagrams

### API
- ✅ Auth endpoints (register, login)
- ✅ Projects CRUD
- ✅ Proposals AI generation
- ✅ Dependencies (JWT auth)

### Infrastructure
- ✅ Docker setup complete
- ✅ Alembic migrations
- ✅ Main.py con CORS

---

## 🔴 Componentes que FALTAN del Backend Anterior

### 1. **Middleware** 🔴 IMPORTANTE

#### Rate Limiting Middleware
**Archivo:** `backend-chatbot/app/middleware/rate_limit_middleware.py`

**Qué hace:**
- Implementa rate limiting con algoritmo Token Bucket
- 60 requests/minuto por usuario
- Burst size de 10
- Headers informativos (X-RateLimit-*)
- Cleanup automático de buckets viejos

**Necesario para:**
- Proteger contra abuso
- Limitar requests de IA (costosos)
- Headers de rate limit en responses

**Prioridad:** 🟡 MEDIA (útil en producción)

---

#### Auth Middleware  
**Archivo:** `backend-chatbot/app/middleware/auth_middleware.py`

**Qué hace:**
- Extrae y valida JWT tokens
- Añade `request.state.user` automáticamente
- Rutas públicas whitelist

**Necesario para:**
- Simplificar auth en endpoints
- No necesario si usamos Depends(get_current_user)

**Prioridad:** 🟢 BAJA (ya tenemos dependencies.py)

---

### 2. **Repository Pattern** 🟡 OPCIONAL

**Archivos:**
- `repositories/base.py` - CRUD genérico
- `repositories/user_repository.py`
- `repositories/conversation_repository.py`
- etc.

**Qué hace:**
- Capa de abstracción sobre SQLAlchemy
- Operaciones CRUD reutilizables
- Unit of Work pattern

**Necesario para:**
- Separación adicional de concerns
- Testing más fácil

**Prioridad:** 🟢 BAJA (optional, podemos usar SQLAlchemy directo)

**Nota:** En el nuevo backend usamos SQLAlchemy async directamente en los endpoints/services, que es más simple y directo.

---

### 3. **Password Reset** 🟡 ÚTIL

**Archivo:** `services/password_reset_service.py`

**Qué hace:**
- Generación de tokens de reset
- Envío de emails
- Validación de tokens
- Reset de contraseñas

**Endpoints faltantes:**
```python
POST /api/v1/auth/password-reset/request
POST /api/v1/auth/password-reset/confirm
```

**Necesario para:**
- UX completa de autenticación
- Usuarios que olvidan contraseña

**Prioridad:** 🟡 MEDIA (nice to have)

---

### 4. **File Upload Endpoints** 🔴 IMPORTANTE

**Archivo:** `routes/documents.py`

**Qué hace:**
- Upload de archivos (PDF, Excel, Word)
- Procesamiento con document_processor
- Análisis con IA (opcional)
- Almacenamiento en S3/local

**Endpoints faltantes:**
```python
POST   /api/v1/projects/{id}/files          # Upload file
GET    /api/v1/projects/{id}/files          # List files
GET    /api/v1/projects/{id}/files/{fileId} # Get file info
DELETE /api/v1/projects/{id}/files/{fileId} # Delete file
GET    /api/v1/files/{fileId}/download      # Download file
```

**Necesario para:**
- Usuarios suben documentos técnicos
- Importar datos de Excel
- Almacenar análisis de agua

**Prioridad:** 🔴 ALTA

---

### 5. **Technical Data Endpoints** 🔴 CRÍTICO

**Archivo:** Necesita crearse (no existía en chatbot)

**Endpoints faltantes:**
```python
GET    /api/v1/projects/{id}/technical-data           # Get all sections
GET    /api/v1/projects/{id}/technical-data/{section} # Get section
PATCH  /api/v1/projects/{id}/technical-data           # Update fields
POST   /api/v1/projects/{id}/technical-data/validate  # Validate completeness
POST   /api/v1/projects/{id}/technical-data/import    # Import from file
```

**Necesario para:**
- Frontend edita tablas técnicas
- Guardar datos capturados
- Validar completitud antes de generar propuesta

**Prioridad:** 🔴 CRÍTICA (core feature)

---

### 6. **Timeline/Activity Log** 🟡 ÚTIL

**Endpoints faltantes:**
```python
GET  /api/v1/projects/{id}/timeline  # Get activity log
POST /api/v1/projects/{id}/timeline  # Add manual event
```

**Qué hace:**
- Log de actividades del proyecto
- "Usuario X editó technical data"
- "Propuesta v1.0 generada"
- "Archivo subido"

**Necesario para:**
- Audit trail
- Mostrar historial en frontend
- Debugging

**Prioridad:** 🟡 MEDIA

---

### 7. **Diagnostic/Admin Endpoints** 🟢 OPCIONAL

**Archivo:** `routes/diagnostic.py`

**Qué hace:**
- Health checks detallados
- Database connection test
- Redis connection test
- S3 connection test

**Prioridad:** 🟢 BAJA (nice to have para ops)

---

### 8. **Feedback System** 🟢 OPCIONAL

**Archivo:** `routes/feedback.py`

**Qué hace:**
- Usuarios califican propuestas
- Feedback para mejorar IA
- Analytics

**Prioridad:** 🟢 BAJA (futuro)

---

### 9. **Workflows** 🟢 OPCIONAL

**Archivo:** `workflows/simple_proposal_workflow.py`

**Qué hace:**
- LangGraph workflow
- Multi-step proposal generation
- State management

**Nota:** Ya tenemos el workflow en proposal_service.py, más simple y directo.

**Prioridad:** 🟢 BAJA (no necesario)

---

### 10. **Email Service** 🟡 ÚTIL

**Qué hace:**
- Enviar emails (password reset, notifications)
- Templates de emails
- SMTP configuration

**Necesario para:**
- Password reset
- Notificaciones de propuestas listas
- Onboarding

**Prioridad:** 🟡 MEDIA

---

### 11. **Logging Configuration** 🟡 ÚTIL

**Archivo:** `core/logging_config.py`

**Qué hace:**
- Configuración centralizada de logging
- Formatters custom
- File + Console handlers
- Log rotation

**Prioridad:** 🟡 MEDIA (actualmente usamos logging básico)

---

## 📊 Resumen de Prioridades

### 🔴 CRÍTICO (Hacer Ya)
1. **Technical Data Endpoints** - Core feature del sistema
2. **File Upload Endpoints** - Usuarios necesitan subir docs

### 🟡 IMPORTANTE (Hacer Pronto)
3. **Rate Limiting Middleware** - Protección contra abuso
4. **Password Reset** - UX completa
5. **Timeline Endpoints** - Audit trail
6. **Email Service** - Notificaciones
7. **Logging Config** - Mejor debugging

### 🟢 OPCIONAL (Nice to Have)
8. **Repository Pattern** - Ya tenemos SQLAlchemy directo
9. **Auth Middleware** - Ya tenemos Dependencies
10. **Diagnostic Endpoints** - Para ops avanzado
11. **Feedback System** - Futuro
12. **Workflows** - Ya tenemos service layer

---

## 🎯 Recomendación de Implementación

### Fase 1: Crítico (Siguiente)
```
1. Technical Data Endpoints       [2-3 horas]
2. File Upload Endpoints          [2-3 horas]
```

### Fase 2: Importante (Esta Semana)
```
3. Rate Limiting Middleware       [1 hora]
4. Timeline Endpoints             [1 hora]
5. Password Reset                 [2 horas]
```

### Fase 3: Nice to Have (Cuando haya tiempo)
```
6. Email Service                  [2 horas]
7. Logging Config                 [1 hora]
8. Diagnostic Endpoints           [1 hora]
```

---

## 💡 Notas Sobre Diferencias de Arquitectura

### Backend Chatbot vs Nuevo Backend

**Chatbot (Anterior):**
- Repository pattern en todas partes
- Middleware para auth
- Conversaciones como entidad principal
- Chat history como contexto

**Nuevo Backend (Actual):**
- SQLAlchemy async directo (más simple)
- Dependencies para auth (más FastAPI-idiomatic)
- Projects como entidad principal
- Technical data estructurada

### ¿Necesitamos los Repositories?

**NO necesariamente.** El patrón Repository es útil en aplicaciones grandes con:
- Múltiples fuentes de datos
- Testing muy extensivo
- Lógica de datos compleja

Para nuestro caso:
- SQLAlchemy async ya es una abstracción
- Testing se puede hacer con fixtures
- La lógica está en Services

**Conclusión:** Repository pattern es opcional. Podemos agregarlo después si crece la complejidad.

---

## 📝 Endpoints que Crear AHORA

### 1. Technical Data

```python
# app/api/v1/technical_data.py

@router.get("/{project_id}/technical-data")
async def get_technical_data(project_id: UUID, current_user: CurrentUser, db: AsyncSession):
    """Get all technical sections and fields for a project"""
    pass

@router.patch("/{project_id}/technical-data")
async def update_technical_data(project_id: UUID, updates: TechnicalDataUpdate, current_user: CurrentUser, db: AsyncSession):
    """Update multiple fields at once"""
    pass

@router.post("/{project_id}/technical-data/validate")
async def validate_completeness(project_id: UUID, current_user: CurrentUser, db: AsyncSession):
    """Validate if data is complete enough for proposal generation"""
    pass
```

### 2. Files

```python
# app/api/v1/files.py

@router.post("/{project_id}/files")
async def upload_file(project_id: UUID, file: UploadFile, current_user: CurrentUser, db: AsyncSession):
    """Upload a file to project"""
    pass

@router.get("/{project_id}/files")
async def list_files(project_id: UUID, current_user: CurrentUser, db: AsyncSession):
    """List all files for project"""
    pass

@router.delete("/{project_id}/files/{file_id}")
async def delete_file(project_id: UUID, file_id: UUID, current_user: CurrentUser, db: AsyncSession):
    """Delete a file"""
    pass

@router.get("/files/{file_id}/download")
async def download_file(file_id: UUID, current_user: CurrentUser, db: AsyncSession):
    """Download a file (presigned URL or stream)"""
    pass
```

---

## 🎉 Conclusión

**Ya tenemos el 80% del backend funcional:**
- ✅ Sistema de IA completo
- ✅ Auth y projects
- ✅ Propuestas con IA
- ✅ PDF y charts
- ✅ Docker setup

**Falta el 20% para completar:**
- 🔴 Technical Data endpoints (CRÍTICO)
- 🔴 File upload endpoints (CRÍTICO)
- 🟡 Rate limiting y otras features (IMPORTANTE)

**Tiempo estimado para completar:**
- Crítico: 4-6 horas
- Importante: 6-8 horas
- Total: 10-14 horas

**Estado actual: Backend funcional al 80% y listo para empezar a usar.** 🚀

---

**¿Quieres que cree los endpoints críticos ahora?** 
- Technical Data
- File Upload
