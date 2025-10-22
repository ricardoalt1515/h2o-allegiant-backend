# 🔍 Análisis Completo: Frontend ↔ Backend Connection

## ✅ Verificaciones Realizadas

### 1. **Backend Routes** ✅
```python
# app/main.py línea 310-314
app.include_router(
    proposals.router,
    prefix=f"{settings.API_V1_PREFIX}/ai/proposals",
    tags=["AI Proposals"],
)
```

**Prefix:** `/api/v1/ai/proposals`

**Endpoints registrados:**
- `POST /api/v1/ai/proposals/generate` → Genera propuesta
- `GET /api/v1/ai/proposals/jobs/{job_id}` → Polling de status

---

### 2. **Frontend API Calls** ✅
```typescript
// lib/api/proposals.ts

// Endpoint 1: Generate
ProposalsAPI.generateProposal(request)
→ apiClient.post('/ai/proposals/generate', {...})

// Endpoint 2: Get Status
ProposalsAPI.getJobStatus(jobId)
→ apiClient.get(`/ai/proposals/jobs/${jobId}`)
```

**Base URL:** `http://localhost:8000/api/v1` (desde client.ts línea 19)

**URLs finales:**
- ✅ `http://localhost:8000/api/v1/ai/proposals/generate`
- ✅ `http://localhost:8000/api/v1/ai/proposals/jobs/{job_id}`

**COINCIDEN PERFECTAMENTE** 🎉

---

### 3. **CORS Configuration** ✅
```python
# app/main.py línea 94-99
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Frontend Origin:** `http://localhost:3000` (debe estar en `settings.cors_origins_list`)

---

### 4. **Schema Mapping (snake_case ↔ camelCase)** ✅

#### Backend Response (Python):
```python
class ProposalJobStatus(BaseSchema):
    job_id: str           # → "jobId" en JSON
    status: str
    progress: int
    current_step: str     # → "currentStep" en JSON
    result: Optional[ProposalJobResult]
    error: Optional[str]
```

#### Frontend Interface (TypeScript):
```typescript
interface ProposalJobStatus {
  jobId: string          // ✅ Coincide
  status: string         // ✅ Coincide
  progress: number       // ✅ Coincide
  currentStep: string    // ✅ Coincide
  result?: {...}         // ✅ Coincide
  error?: string         // ✅ Coincide
}
```

**BaseSchema** con `alias_generator=to_camel_case` convierte automáticamente:
- `job_id` → `jobId` ✅
- `current_step` → `currentStep` ✅

**MAPPING CORRECTO** 🎉

---

### 5. **Response Flow**

#### POST /generate Response:
```python
# Backend devuelve:
return ProposalJobStatus(
    job_id=job_id,
    status="queued",
    progress=0,
    current_step="Initializing...",
    result=None,
    error=None,
)
```

#### Serializado a JSON (por BaseSchema):
```json
{
  "jobId": "job_abc123",
  "status": "queued",
  "progress": 0,
  "currentStep": "Initializing...",
  "result": null,
  "error": null
}
```

#### Frontend recibe y usa:
```typescript
const initialStatus = await ProposalsAPI.generateProposal(request)
// initialStatus.jobId ✅
// initialStatus.currentStep ✅

await pollProposalStatus(initialStatus.jobId, {...})
```

**FLUJO CORRECTO** 🎉

---

### 6. **GET /jobs/{job_id} Response:**

```python
# Backend endpoint:
async def get_job_status(job_id: str, current_user: CurrentUser):
    status_data = await ProposalService.get_job_status(job_id)
    
    if not status_data:
        raise HTTPException(404, detail="Job not found")
    
    return ProposalJobStatus(**status_data)
```

**¿Qué devuelve `ProposalService.get_job_status()`?**
```python
# proposal_service.py línea 380-390
@staticmethod
async def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    return await cache_service.get_job_status(job_id)
```

**¿Qué devuelve `cache_service.get_job_status()`?**
```python
# cache_service.py línea 184-194
async def get_job_status(self, job_id: str) -> Optional[dict]:
    return await self.get(f"job:{job_id}")
```

**Devuelve un dict directo desde Redis.**

---

## ⚠️ PROBLEMA IDENTIFICADO

### **El Issue:**

`cache_service.get_job_status()` devuelve un **dict** con snake_case keys:
```python
{
    "job_id": "job_abc123",
    "status": "processing",
    "progress": 40,
    "current_step": "Analyzing...",
    ...
}
```

PERO, cuando se pasa a `ProposalJobStatus(**status_data)`:
```python
return ProposalJobStatus(**status_data)
```

**Pydantic espera snake_case en Python**, que luego convierte a camelCase en JSON.

**El problema:** Si `status_data` tiene snake_case keys, está OK.
Pero si tiene camelCase keys (porque se guardó mal), falla.

---

## 🔍 Verificación Necesaria

### **¿Cómo se guarda en Redis?**

```python
# cache_service.py línea 145-182
async def set_job_status(
    self,
    job_id: str,
    status: str,
    progress: int,
    current_step: str,
    result: Optional[dict] = None,
    error: Optional[str] = None,
    ttl: int = 3600,
) -> bool:
    job_data = {
        "job_id": job_id,            # ✅ snake_case
        "status": status,
        "progress": progress,
        "current_step": current_step, # ✅ snake_case
    }
    
    if result:
        job_data["result"] = result
    if error:
        job_data["error"] = error
    
    return await self.set(f"job:{job_id}", job_data, ttl=ttl)
```

**Se guarda con snake_case keys** ✅

---

## 🎯 POSIBLE CAUSA RAÍZ

### **Hipótesis 1: Result field format mismatch**

Cuando se completa el job:
```python
# proposal_service.py línea 356-364
result={
    "proposal_id": str(proposal.id),
    "preview": {
        "executive_summary": proposal.executive_summary,
        "capex": proposal.capex,
        "opex": proposal.opex,
        "key_technologies": [],
    },
}
```

**Usa snake_case:** `proposal_id`, `executive_summary`, etc.

**Frontend espera camelCase:**
```typescript
result?: {
  proposalId: string  // ← Espera camelCase
  preview: {
    executiveSummary: string  // ← Espera camelCase
    ...
  }
}
```

**AQUÍ ESTÁ EL PROBLEMA!** 🔴

El campo `result` se guarda como dict en Redis **sin pasar por Pydantic**, 
entonces **no se convierte a camelCase**.

---

## ✅ SOLUCIÓN

### **Opción A: Crear Pydantic models para result (Correcto)**

```python
# En cache_service.py línea 356
from app.schemas.proposal import ProposalJobResult, ProposalPreview

# Convertir dict a Pydantic model
result_model = ProposalJobResult(
    proposal_id=proposal.id,
    preview=ProposalPreview(
        executive_summary=proposal.executive_summary,
        capex=proposal.capex,
        opex=proposal.opex,
        key_technologies=[],
    )
)

# Guardar como dict serializado
result={
    "proposal_id": str(result_model.proposal_id),
    "preview": result_model.preview.model_dump(by_alias=True),
}
```

### **Opción B: Usar camelCase manualmente en el dict (Rápido)**

```python
# En proposal_service.py línea 356
result={
    "proposalId": str(proposal.id),  # ← camelCase
    "preview": {
        "executiveSummary": proposal.executive_summary,  # ← camelCase
        "capex": proposal.capex,
        "opex": proposal.opex,
        "keyTechnologies": [],  # ← camelCase
    },
}
```

---

## 📊 Resumen

| Aspecto | Estado | Notas |
|---------|--------|-------|
| Backend routes | ✅ Correcto | Prefix correcto |
| Frontend API calls | ✅ Correcto | URLs coinciden |
| CORS | ✅ Correcto | Configurado |
| Schema mapping | ✅ Correcto | BaseSchema funciona |
| POST /generate response | ✅ Correcto | Pydantic serializa bien |
| GET /jobs response | ⚠️ Parcial | Main fields OK |
| **Result field** | ❌ **PROBLEMA** | **No usa camelCase** |

---

## 🚀 Fix a Aplicar

Ver archivo: `FIX_RESULT_FIELD.md`
