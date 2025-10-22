# 🔄 Compatibility Layer: Testing sin Migración

## 📊 Arquitectura Visual

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  <AITransparency />                                       │  │
│  │  - Proven Cases Tab                                       │  │
│  │  - Assumptions Tab                                        │  │
│  │  - Alternatives Tab                                       │  │
│  │  - Justification Tab                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
│                 GET /ai-metadata/{proposalId}                   │
└─────────────────────────────┬───────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                            │
│                                                                 │
│  proposals.py (API Endpoint)                                    │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ @router.get("/ai-metadata")                             │  │
│  │ async def get_proposal_ai_metadata():                   │  │
│  │     # ⭐ Compatibility layer                            │  │
│  │     ai_metadata = await ai_metadata_compat.get_metadata(│  │
│  │         proposal_id=id,                                 │  │
│  │         db_metadata=proposal.ai_metadata  # None si no  │  │
│  │     )                                     # hay columna │  │
│  │     return AIMetadataResponse(**ai_metadata)            │  │
│  └─────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
│  ai_metadata_compat.py (Compatibility Layer)                   │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ async def get_metadata():                               │  │
│  │     # Priority 1: Check PostgreSQL                      │  │
│  │     if db_metadata is not None:                         │  │
│  │         return db_metadata  ✅ (después de migration)   │  │
│  │                                                          │  │
│  │     # Priority 2: Check Redis                           │  │
│  │     if USE_TEMPORARY_STORAGE:                           │  │
│  │         redis_key = f"ai_metadata:proposal:{id}"        │  │
│  │         return await cache_service.get(redis_key)       │  │
│  │              ✅ (antes de migration)                     │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              ↓
       ┌──────────────────────┴──────────────────────┐
       ↓                                              ↓
┌─────────────────┐                          ┌─────────────────┐
│   PostgreSQL    │                          │      Redis      │
├─────────────────┤                          ├─────────────────┤
│ proposals       │                          │ ai_metadata:    │
│ ├─ id           │                          │ proposal:{id}   │
│ ├─ version      │                          │                 │
│ ├─ capex        │                          │ {               │
│ └─ ai_metadata  │ ❌ NULL (sin migration)  │   usage_stats   │
│    (no existe   │                          │   proven_cases  │
│     aún)        │                          │   assumptions   │
│                 │                          │   ...           │
│                 │                          │ }               │
│                 │                          │                 │
│                 │                          │ TTL: 7 días     │
└─────────────────┘                          └─────────────────┘
```

---

## 🔄 Flujo de Escritura (Generar Propuesta)

```
1. Usuario → Click "Generate Proposal"
           ↓
2. Frontend → POST /generate
           ↓
3. Backend → proposal_service.py
           ↓
4. AI Agent → Genera propuesta + ai_metadata dict
           ↓
5. Save to DB → INSERT INTO proposals (...) 
                ❌ SIN ai_metadata column
           ↓
6. 🔑 Compatibility Layer:
   ai_metadata_compat.save_metadata(proposal_id, ai_metadata)
           ↓
7. Redis → SET ai_metadata:proposal:{id} = {...}
           EXPIRE ai_metadata:proposal:{id} 604800  # 7 días
           ✅ SAVED

Resultado: 
✅ Proposal en PostgreSQL (sin ai_metadata)
✅ AI metadata en Redis (temporal)
✅ Frontend funciona perfecto
```

---

## 🔍 Flujo de Lectura (Ver AI Transparency)

```
1. Usuario → Navega a proposal detail page
           ↓
2. Frontend → <AITransparency /> mounts
           ↓
3. useEffect → GET /ai-metadata/{proposalId}
           ↓
4. Backend → get_proposal_ai_metadata()
           ↓
5. 🔑 Compatibility Layer:
   ai_metadata_compat.get_metadata(
       proposal_id=id,
       db_metadata=proposal.ai_metadata  # None (no column)
   )
           ↓
6. Check Priority 1 (PostgreSQL):
   if db_metadata is not None:  # False (no column)
       return db_metadata
           ↓
7. Check Priority 2 (Redis):
   if USE_TEMPORARY_STORAGE:  # True
       redis_key = f"ai_metadata:proposal:{id}"
       metadata = await cache_service.get(redis_key)
       return metadata  ✅ FOUND
           ↓
8. Validate with Pydantic:
   AIMetadataResponse(**metadata)
           ↓
9. Return → Frontend
           ↓
10. Frontend → Renderiza tabs con datos

Resultado:
✅ Datos leídos de Redis
✅ Validados con Pydantic
✅ Frontend muestra UI completa
```

---

## ⚙️ Feature Flags

**Archivo:** `app/services/ai_metadata_compat.py`

```python
# ⭐ Control global del comportamiento
USE_TEMPORARY_STORAGE = True  # ← Cambia a False después de migration

# Antes de migration:
USE_TEMPORARY_STORAGE = True
  ↓
✅ Usa Redis para storage
✅ No requiere columna ai_metadata en BD
✅ Perfecto para testing

# Después de migration:
USE_TEMPORARY_STORAGE = False
  ↓
✅ Usa PostgreSQL para storage
✅ Lee de proposal.ai_metadata
✅ Production-ready
```

---

## 📊 Comparación de Estados

### **Estado 1: SIN Migration (AHORA)**

```
PostgreSQL proposals table:
┌──────────────┬──────────┬────────┐
│ id           │ version  │ capex  │
├──────────────┼──────────┼────────┤
│ abc-123      │ v1.0     │ 250000 │
│ def-456      │ v1.1     │ 300000 │
└──────────────┴──────────┴────────┘
❌ NO ai_metadata column

Redis:
┌────────────────────────────────┬─────────────────────┐
│ Key                            │ Value               │
├────────────────────────────────┼─────────────────────┤
│ ai_metadata:proposal:abc-123   │ {usage_stats: ...}  │
│ ai_metadata:proposal:def-456   │ {usage_stats: ...}  │
└────────────────────────────────┴─────────────────────┘
✅ Temporary storage (7 days TTL)

Frontend:
✅ Funciona perfecto
✅ Lee de Redis via API
✅ Todos los tabs funcionan
```

### **Estado 2: CON Migration (FUTURO)**

```
PostgreSQL proposals table:
┌──────────────┬──────────┬────────┬──────────────────┐
│ id           │ version  │ capex  │ ai_metadata      │
├──────────────┼──────────┼────────┼──────────────────┤
│ abc-123      │ v1.0     │ 250000 │ {usage_stats...} │ ✅
│ def-456      │ v1.1     │ 300000 │ {usage_stats...} │ ✅
└──────────────┴──────────┴────────┴──────────────────┘
✅ ai_metadata JSONB column

Redis:
┌────────────────────────────────┬────────┐
│ Key                            │ Value  │
├────────────────────────────────┼────────┤
│ (empty or optional cache)      │        │
└────────────────────────────────┴────────┘
❌ No longer needed (or used as cache)

Frontend:
✅ Funciona idéntico
✅ Lee de PostgreSQL via API
✅ Datos permanentes
```

---

## 🛠️ Archivos Modificados

### **Nuevos archivos:**
```
✅ app/services/ai_metadata_compat.py (400 líneas)
   └─ Compatibility layer completo

✅ TESTING_WITHOUT_MIGRATION.md
   └─ Guía completa de testing

✅ COMPATIBILITY_LAYER_SUMMARY.md (este archivo)
   └─ Resumen visual
```

### **Archivos modificados:**
```
✅ app/services/proposal_service.py
   ANTES:
   proposal.ai_metadata = ai_metadata  # Guardaba en BD
   
   AHORA:
   # proposal.ai_metadata = ai_metadata  # Comentado
   await ai_metadata_compat.save_metadata(id, ai_metadata)  # Redis

✅ app/api/v1/proposals.py
   ANTES:
   return proposal.ai_metadata  # Leía de BD
   
   AHORA:
   ai_metadata = await ai_metadata_compat.get_metadata(
       proposal_id=id,
       db_metadata=getattr(proposal, 'ai_metadata', None)
   )
   return ai_metadata  # Lee de Redis o BD
```

---

## 🚀 Quick Start Commands

```bash
# 1. Asegúrate de que Redis esté corriendo
redis-cli ping
# Response: PONG

# 2. Reinicia backend para cargar cambios
cd backend-h2o
uvicorn app.main:app --reload

# 3. Genera una propuesta desde frontend
# (o usa curl, ver TESTING_WITHOUT_MIGRATION.md)

# 4. Verifica que se guardó en Redis
redis-cli KEYS "ai_metadata:*"
# Response: 
# 1) "ai_metadata:proposal:abc-123-def-456"

# 5. Ve el contenido
redis-cli GET "ai_metadata:proposal:abc-123-def-456"
# Response: JSON completo con usage_stats, proven_cases, etc.

# 6. Abre frontend y verifica UI
# http://localhost:3000/project/{id}/proposals/{proposalId}
# Scroll a "AI Transparency & Reasoning"
# ✅ Deberías ver tabs con datos!
```

---

## 🎯 Cuando Aplicar Migration

### **Aplica migration SI:**
- ✅ UX validado por stakeholders
- ✅ 10+ propuestas generadas exitosamente
- ✅ Performance aceptable
- ✅ Frontend funciona en todos los browsers
- ✅ Mobile responsive OK
- ✅ Tests pasan (pytest)
- ✅ Feedback positivo de usuarios

### **NO apliques migration SI:**
- ❌ Hay bugs en generación
- ❌ UX necesita cambios
- ❌ Performance issues
- ❌ Schema de ai_metadata puede cambiar
- ❌ Stakeholders no aprobaron

---

## 🔄 Proceso de Migración (Cuando Estés Listo)

### **Paso 1: Backup**
```bash
# Backup de PostgreSQL
pg_dump h2o_allegiant > backup_pre_migration.sql

# Backup de Redis (opcional)
redis-cli SAVE
cp /var/lib/redis/dump.rdb redis_backup.rdb
```

### **Paso 2: Apply Migration**
```bash
cd backend-h2o
alembic upgrade head
# ✅ Crea columna ai_metadata en proposals
```

### **Paso 3: Migrate Data**
```python
# Migra datos de Redis → PostgreSQL
python scripts/migrate_redis_to_db.py
# Output: Migrated: {'migrated': 15, 'failed': 0, 'skipped': 2}
```

### **Paso 4: Update Code**
```python
# En app/services/ai_metadata_compat.py
USE_TEMPORARY_STORAGE = False  # Era True

# En app/services/proposal_service.py (línea 338)
# Descomentar:
ai_metadata=ai_metadata,  # ✅ Guarda en BD

# Eliminar líneas 345-348:
# from app.services.ai_metadata_compat import ai_metadata_compat
# await ai_metadata_compat.save_metadata(...)  # Ya no necesario
```

### **Paso 5: Deploy & Verify**
```bash
# Reinicia backend
uvicorn app.main:app --reload

# Genera nueva propuesta
# Verifica que se guarda en BD (no Redis)
psql h2o_allegiant -c "SELECT id, ai_metadata FROM proposals LIMIT 1;"

# Verifica frontend
# http://localhost:3000/project/.../proposals/...
# ✅ Debería funcionar idéntico
```

### **Paso 6: Cleanup (Opcional)**
```bash
# Limpia Redis
redis-cli DEL $(redis-cli KEYS "ai_metadata:*")

# O mantén Redis como cache (recomendado para performance)
```

---

## 📈 Métricas de Éxito

**Durante testing (Redis):**
- ✅ Latencia API <100ms
- ✅ 100% uptime
- ✅ 0 data loss (en 7 días)
- ✅ Validación Pydantic: 0 errors

**Después de migration (PostgreSQL):**
- ✅ Latencia API <150ms
- ✅ Data permanente
- ✅ Backups diarios
- ✅ Queries SQL disponibles

---

## ❓ FAQ

### **P: ¿Puedo usar ambos (Redis + PostgreSQL)?**
**R:** Sí! Después de la migration, puedes usar Redis como cache:
```python
# Priority 1: Redis (cache)
# Priority 2: PostgreSQL (source of truth)
```

### **P: ¿Qué pasa si Redis se cae durante testing?**
**R:** El sistema sigue funcionando, solo no habrá AI transparency para propuestas nuevas. Propuestas antiguas con metadata en Redis ya guardada siguen accesibles.

### **P: ¿Puedo cambiar el TTL de 7 días?**
**R:** Sí, edita `TEMPORARY_STORAGE_TTL` en `ai_metadata_compat.py`:
```python
TEMPORARY_STORAGE_TTL = timedelta(days=30)  # 30 días
```

### **P: ¿Cómo sé si la migration está aplicada?**
**R:** Corre esto:
```python
from app.services.ai_metadata_compat import check_migration_status
import asyncio
print(asyncio.run(check_migration_status()))
# Output: {'migration_applied': True/False, ...}
```

### **P: ¿Puedo revertir después de aplicar migration?**
**R:** Sí:
```bash
alembic downgrade -1  # Revert migration
# Pero perderás ai_metadata guardados en BD
```

---

## 🎉 Conclusión

**Ahora tienes:**
- ✅ Sistema funcionando SIN cambios en BD
- ✅ Testing completo posible
- ✅ Path claro a production
- ✅ Rollback fácil si necesario
- ✅ Mismo UX que versión final

**Flujo recomendado:**
1. Testa 1-2 semanas con Redis
2. Valida UX con usuarios
3. Si todo OK → Aplica migration
4. Si hay issues → Itera sin migration

**¡Éxito!** 🚀
