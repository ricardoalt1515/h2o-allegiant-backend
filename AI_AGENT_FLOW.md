# 🤖 Sistema de IA - Flujo de Generación de Propuestas

**Fecha:** 2025-09-30  
**Estado:** ✅ **Integrado y Listo**

---

## 🎯 Visión General

El sistema de IA genera propuestas técnicas profesionales basándose en los **datos técnicos estructurados** capturados en el frontend. A diferencia del sistema anterior (chatbot conversacional), este flujo trabaja con datos tabulares organizados en secciones y campos.

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                         FRONTEND                            │
│  Usuario completa datos técnicos en tablas estructuradas   │
│  (TechnicalSections → TechnicalFields)                      │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    │ POST /api/v1/ai/proposals/generate
                    │ {projectId, proposalType, preferences}
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    API ENDPOINT                             │
│  • Valida request                                           │
│  • Crea job ID                                              │
│  • Guarda en Redis: status="queued"                         │
│  • Retorna: {jobId, status, estimatedTime}                  │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    │ Trigger Background Task
                    ▼
┌─────────────────────────────────────────────────────────────┐
│              BACKGROUND WORKER                              │
│  ProposalService.generate_proposal_async()                  │
│                                                             │
│  1. Load Project + TechnicalSections                        │
│     ├─ Update: status="processing", progress=20%           │
│     └─ Query database for all technical data               │
│                                                             │
│  2. Serialize Technical Data                                │
│     ├─ Convert sections → structured dict                  │
│     ├─ Organize by section_id                              │
│     └─ Update: progress=30%                                │
│                                                             │
│  3. Call AI Agent                                           │
│     ├─ Update: progress=40%                                │
│     ├─ proposal_agent.run()                                │
│     │   ├─ Inject project context                          │
│     │   ├─ Inject technical data                           │
│     │   └─ Execute with OpenAI GPT-4                       │
│     └─ AI generates comprehensive proposal                 │
│                                                             │
│  4. Save Proposal to Database                               │
│     ├─ Update: progress=80%                                │
│     ├─ Create Proposal record                              │
│     ├─ Assign version (v1.0, v1.1, etc.)                   │
│     └─ Store markdown + structured data                    │
│                                                             │
│  5. Complete Job                                            │
│     ├─ Update: status="completed", progress=100%           │
│     └─ Set result with proposalId + preview                │
└─────────────────────────────────────────────────────────────┘
                    │
                    │ Frontend polls status
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                 STATUS POLLING                              │
│  GET /api/v1/ai/proposals/jobs/{jobId}                      │
│                                                             │
│  Every 2 seconds, frontend checks:                          │
│  • status: queued → processing → completed                 │
│  • progress: 0% → 40% → 80% → 100%                         │
│  • current_step: "Generating with AI..."                    │
│                                                             │
│  When completed:                                            │
│  • result.proposalId                                        │
│  • result.preview (summary, capex, opex)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Flujo de Datos Detallado

### 1. Input: Datos Técnicos Estructurados

El frontend envía datos organizados en secciones:

```json
{
  "project_info": {
    "name": "Planta Los Mochis",
    "client": "CAPA",
    "sector": "Municipal",
    "location": "Los Mochis, Sinaloa"
  },
  "technical_parameters": {
    "water-source": {
      "title": "Fuente de Agua",
      "fields": {
        "daily-flow": {
          "label": "Caudal diario",
          "value": "5000",
          "unit": "m³/día",
          "source": "manual"
        },
        "source-type": {
          "label": "Tipo de fuente",
          "value": "Río",
          "source": "manual"
        }
      }
    },
    "water-quality": {
      "title": "Calidad del Agua",
      "fields": {
        "tss": {
          "label": "Sólidos Suspendidos Totales",
          "value": "250",
          "unit": "mg/L",
          "source": "imported"
        },
        "turbidity": {
          "label": "Turbidez",
          "value": "45",
          "unit": "NTU",
          "source": "manual"
        }
      }
    }
  }
}
```

### 2. Processing: Serialización para IA

El servicio transforma los datos para el agente:

```python
def _serialize_technical_data(project, technical_sections):
    return {
        "project_info": {
            "name": project.name,
            "client": project.client,
            "sector": project.sector,
            "location": project.location,
            "budget": project.budget
        },
        "technical_parameters": {
            section.section_id: {
                "title": section.title,
                "fields": {
                    field.field_id: {
                        "label": field.label,
                        "value": field.value,
                        "unit": field.unit,
                        "source": field.source
                    }
                    for field in section.fields
                }
            }
            for section in technical_sections
        }
    }
```

### 3. AI Agent: Pydantic-AI

El agente utiliza **Pydantic-AI** con:

```python
proposal_agent = Agent(
    "openai:gpt-4o-mini",
    deps_type=ProjectContext,
    instructions=load_proposal_prompt(),  # Prompt profesional de ingeniería
    model_settings=ModelSettings(
        temperature=0.7,
        max_tokens=4000,
    ),
    retries=3,
)

# Inyección dinámica de contexto
@proposal_agent.instructions
def inject_project_context(ctx):
    return f"""
    PROJECT: {ctx.deps.project_name}
    CLIENT: {ctx.deps.client_name}
    SECTOR: {ctx.deps.sector}
    LOCATION: {ctx.deps.location}
    """

@proposal_agent.instructions
def inject_technical_data(ctx):
    return f"""
    TECHNICAL DATA:
    {json.dumps(ctx.deps.technical_data, indent=2)}
    """
```

### 4. Output: Propuesta Estructurada

El agente genera:

```json
{
  "markdown_content": "# Propuesta Técnica\n\n## Resumen Ejecutivo...",
  "technical_data": {
    "flow_rate_m3_day": 5000,
    "main_equipment": [
      {
        "type": "DAF System",
        "capacity_m3_day": 5500,
        "capex_usd": 45000,
        "power_consumption_kw": 12.5,
        "justification": "Optimal for TSS removal..."
      }
    ],
    "capex_usd": 150000,
    "annual_opex_usd": 25000,
    "treatment_efficiency": {
      "TSS": 95,
      "Turbidity": 98
    }
  }
}
```

---

## 🔄 Estados del Job

El job pasa por estos estados:

```
1. QUEUED
   ├─ progress: 0%
   ├─ current_step: "Initializing..."
   └─ Esperando worker

2. PROCESSING
   ├─ progress: 10% → "Loading project data..."
   ├─ progress: 20% → "Loading technical data..."
   ├─ progress: 30% → "Preparing for AI..."
   ├─ progress: 40% → "Generating with AI (1-2 min)..."
   ├─ progress: 80% → "Saving proposal..."
   └─ AI está trabajando

3. COMPLETED
   ├─ progress: 100%
   ├─ current_step: "Success!"
   ├─ result: {proposalId, preview}
   └─ Propuesta lista

4. FAILED
   ├─ progress: 0%
   ├─ current_step: "Failed"
   ├─ error: "Error message"
   └─ Job falló
```

---

## 📦 Componentes del Sistema

### 1. **Agente de IA** (`app/agents/proposal_agent.py`)

**Responsabilidades:**
- Recibir contexto del proyecto + datos técnicos
- Generar propuesta con OpenAI
- Estructurar respuesta

**Características:**
- ✅ Pydantic-AI para type safety
- ✅ Retry automático (3 intentos)
- ✅ Usage tracking (tokens, requests)
- ✅ Inyección dinámica de contexto
- ✅ Prompt profesional de ingeniería

### 2. **Servicio de Propuestas** (`app/services/proposal_service.py`)

**Responsabilidades:**
- Orquestar flujo completo
- Serializar datos técnicos
- Gestionar jobs en Redis
- Guardar propuestas en DB

**Métodos principales:**
```python
ProposalService.start_proposal_generation()
  → Crea job, retorna jobId

ProposalService.generate_proposal_async()
  → Ejecuta generación en background

ProposalService.get_job_status()
  → Retorna status del job
```

### 3. **Cache Service** (`app/services/cache_service.py`)

**Responsabilidades:**
- Almacenar status de jobs en Redis
- TTL de 1 hora
- Operaciones: set, get, delete

**Métodos:**
```python
cache_service.set_job_status(job_id, status, progress, ...)
cache_service.get_job_status(job_id)
```

### 4. **Prompt Template** (`app/prompts/proposal_prompt.md`)

Prompt profesional de ingeniería que define:
- Rol del agente (ingeniero experto)
- Estructura de la propuesta
- Principios de diseño
- Guidelines técnicos
- Formato de output

---

## 🚀 Cómo Funciona en Producción

### Request Inicial

```http
POST /api/v1/ai/proposals/generate
Authorization: Bearer {token}

{
  "project_id": "uuid-here",
  "proposal_type": "Technical",
  "preferences": {
    "focus_areas": ["cost-optimization", "sustainability"]
  }
}
```

**Response:**
```json
{
  "jobId": "job_abc123",
  "status": "queued",
  "estimatedTime": 120
}
```

### Polling del Status

```http
GET /api/v1/ai/proposals/jobs/job_abc123
```

**Response (Processing):**
```json
{
  "job_id": "job_abc123",
  "status": "processing",
  "progress": 45,
  "current_step": "Generating proposal with AI...",
  "result": null,
  "error": null
}
```

**Response (Completed):**
```json
{
  "job_id": "job_abc123",
  "status": "completed",
  "progress": 100,
  "current_step": "Proposal generated successfully!",
  "result": {
    "proposal_id": "uuid-proposal",
    "preview": {
      "executive_summary": "Sistema de tratamiento DAF + MBR...",
      "capex": 150000,
      "opex": 25000,
      "key_technologies": ["DAF", "MBR", "UV Disinfection"]
    }
  },
  "error": null
}
```

---

## 💡 Ventajas de Este Enfoque

### 1. **Datos Estructurados vs Chat**
```
❌ ANTES (Chatbot):
   "El usuario dijo que tiene un río con 250 mg/L de TSS..."
   → Parsing de lenguaje natural
   → Datos no estructurados
   → Menos preciso

✅ AHORA (Estructurado):
   {section: "water-quality", field: "tss", value: 250, unit: "mg/L"}
   → Datos estructurados
   → Type-safe
   → Muy preciso
```

### 2. **Rastreable y Auditable**
- Cada campo tiene `source` (manual, imported, ai)
- Historial de cambios en timeline
- Jobs con status tracking
- Usage metrics (tokens, tiempo)

### 3. **Escalable**
- Background workers pueden procesarse en paralelo
- Redis maneja múltiples jobs
- Cache con TTL para limpieza automática

### 4. **Type-Safe End-to-End**
```
Frontend (TypeScript)
  → TableSection, TableField
     ↓
Backend (Pydantic)
  → TechnicalSection, TechnicalField (SQLAlchemy)
     ↓
AI Agent (Pydantic-AI)
  → ProjectContext, structured data
     ↓
Output (Pydantic)
  → ProposalResponse, EquipmentSpec
```

---

## 🔧 Configuración Requerida

### Variables de Entorno

```bash
# OpenAI (REQUERIDO)
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=4000

# Redis (REQUERIDO para jobs)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Database (REQUERIDO)
POSTGRES_USER=h2o_user
POSTGRES_PASSWORD=your-password
POSTGRES_SERVER=localhost
POSTGRES_DB=h2o_allegiant
```

### Instalación de Dependencias

```bash
pip install pydantic-ai openai redis sqlalchemy asyncpg
```

---

## 📊 Métricas y Monitoreo

### Logs Generados

```
🚀 Started proposal generation job: job_abc123
🔍 Loading project: Planta Los Mochis
📊 Technical sections loaded: 5 sections, 23 fields
🧠 Generating proposal with AI...
✅ Proposal generated - Tokens: 12,450, Requests: 3
💾 Proposal saved: uuid-proposal (v1.0)
✅ Job completed in 87 seconds
```

### Usage Tracking

```python
usage_stats = {
    "total_tokens": 12450,
    "prompt_tokens": 8200,
    "completion_tokens": 4250,
    "total_requests": 3,
    "model_used": "gpt-4o-mini",
    "success": True
}
```

---

## 🎯 Próximos Pasos

### Fase Actual: ✅ Completado
- [x] Agente de IA configurado
- [x] Servicio de propuestas
- [x] Cache service (Redis)
- [x] Flujo completo implementado
- [x] Prompt profesional

### Fase Siguiente: ⏳ Por Hacer
- [ ] Crear endpoints API (auth, projects, proposals)
- [ ] Implementar background workers (Celery o FastAPI BackgroundTasks)
- [ ] Agregar generación de PDFs
- [ ] Agregar generación de charts
- [ ] Testing end-to-end

---

## 📚 Referencias

- **Pydantic-AI**: https://ai.pydantic.dev/
- **OpenAI API**: https://platform.openai.com/docs
- **FastAPI Background Tasks**: https://fastapi.tiangolo.com/tutorial/background-tasks/

---

**Estado:** ✅ Sistema de IA completamente integrado y listo para uso.

**Siguiente paso:** Implementar endpoints API para exponer esta funcionalidad al frontend.
