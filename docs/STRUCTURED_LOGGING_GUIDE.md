# 📝 Guía de Structured Logging con structlog

**Implementado**: Octubre 6, 2025  
**Librería**: structlog 24.4.0  
**Estado**: ✅ Activo en producción

---

## 🎯 ¿Por Qué Structured Logging?

### Problemas con logs tradicionales:
```python
# ❌ Log tradicional (difícil de buscar/analizar)
logger.info(f"Proposal generated for project {project_id} by user {user_id}")
logger.error(f"Error: {e}")
```

**Desventajas:**
- Imposible buscar por campos específicos
- No se pueden generar métricas automáticas
- Formato inconsistente
- Difícil integración con herramientas de observability

### Solución con structured logging:
```python
# ✅ Structured log (contextual, searchable, métricas automáticas)
logger.info(
    "proposal_generated",
    proposal_id=str(proposal.id),
    project_id=str(project_id),
    user_id=str(user_id),
    duration_seconds=duration,
    tokens_used=tokens
)
```

**Ventajas:**
- ✅ Búsqueda exacta: `grep proposal_id=123 logs/`
- ✅ Métricas automáticas por campo
- ✅ Formato JSON consistente
- ✅ Integración directa con Datadog, Grafana, CloudWatch

---

## 🚀 Configuración Actual

### En `app/main.py`:

```python
import structlog

if settings.ENVIRONMENT == "production":
    # Producción: JSON output para agregación de logs
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),  # ← JSON
    ]
else:
    # Desarrollo: Colored output legible
    processors = [
        # ... mismos procesadores ...
        structlog.dev.ConsoleRenderer(),  # ← Coloreado
    ]

structlog.configure(
    processors=processors,
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
```

**Beneficio**: Logs legibles en desarrollo, JSON en producción.

---

## 📖 Guía de Uso

### 1. Importar en tu módulo

```python
import structlog

logger = structlog.get_logger(__name__)
```

**NO uses**: `import logging` ni `logging.getLogger()`  
**USA**: `import structlog` y `structlog.get_logger()`

---

### 2. Logs de Información (INFO)

**Cuándo usar**: Operaciones exitosas, hitos importantes.

```python
# ✅ CORRECTO: Event name + contexto estructurado
logger.info(
    "proposal_generated",  # Event name (snake_case)
    proposal_id=str(proposal.id),
    project_id=str(project_id),
    user_id=str(user_id),
    proposal_type="Technical",
    duration_seconds=45.2,
    tokens_used=15000,
    cost_usd=0.05
)
```

**Salida en desarrollo:**
```
2025-10-06T10:30:45 [info] proposal_generated
    proposal_id=550e8400-e29b-41d4-a716-446655440000
    project_id=660e8400-e29b-41d4-a716-446655440001
    user_id=770e8400-e29b-41d4-a716-446655440002
    duration_seconds=45.2
```

**Salida en producción (JSON):**
```json
{
  "event": "proposal_generated",
  "level": "info",
  "timestamp": "2025-10-06T10:30:45.123456Z",
  "logger": "app.services.proposal_service",
  "proposal_id": "550e8400-e29b-41d4-a716-446655440000",
  "project_id": "660e8400-e29b-41d4-a716-446655440001",
  "user_id": "770e8400-e29b-41d4-a716-446655440002",
  "duration_seconds": 45.2,
  "tokens_used": 15000,
  "cost_usd": 0.05
}
```

---

### 3. Logs de Advertencia (WARNING)

**Cuándo usar**: Situaciones anómalas pero recuperables.

```python
# ✅ CORRECTO
logger.warning(
    "using_legacy_relational_data",
    project_id=str(project.id),
    sections_count=5,
    source="relational",
    reason="no_jsonb_data_found"
)
```

**Ejemplo real del código:**
```python
if not jsonb_sections:
    logger.warning(
        "no_technical_data_found",
        project_id=str(project.id),
        source="none",
        action="returning_minimal_structure"
    )
```

---

### 4. Logs de Error (ERROR)

**Cuándo usar**: Errores capturados que impiden completar la operación.

```python
# ✅ CORRECTO: Incluye exc_info=True para stack trace
try:
    result = await risky_operation()
except Exception as e:
    logger.error(
        "operation_failed",
        exc_info=True,  # ← Stack trace automático
        project_id=str(project_id),
        error_type=type(e).__name__,
        error_message=str(e),
        operation="risky_operation"
    )
    raise
```

**Ejemplo real del código:**
```python
except ProposalGenerationError as e:
    logger.error(
        "proposal_generation_failed",
        exc_info=True,
        project_id=str(project_id),
        job_id=job_id,
        error_type=type(e).__name__,
        error_message=str(e)
    )
```

**Beneficio de `exc_info=True`:**
- Captura automáticamente el stack trace completo
- Lo serializa como JSON en producción
- Fácil de buscar por tipo de error

---

### 5. Logs con Métricas de Performance

**Patrón común**: Medir duración de operaciones.

```python
import time

start_time = time.time()

# ... operación ...

logger.info(
    "operation_completed",
    operation="generate_proposal",
    duration_seconds=round(time.time() - start_time, 2),
    tokens_used=15000,
    cost_usd=0.05
)
```

**Ejemplo real del código:**
```python
start_time = time.time()
proposal_output, usage_stats = await generate_enhanced_proposal(...)
generation_duration = time.time() - start_time

logger.info(
    "ai_proposal_generated",
    project_id=str(project_id),
    job_id=job_id,
    duration_seconds=round(generation_duration, 2),
    tokens_used=usage_stats.get('total_tokens', 0),
    model=usage_stats.get('model_used', 'unknown'),
    cost_usd=usage_stats.get('cost_estimate', 0)
)
```

---

## 🔍 Búsqueda y Análisis de Logs

### Buscar por campo específico:

```bash
# Buscar todas las propuestas del proyecto X
grep "project_id=550e8400" logs/app.log

# Buscar errores de un tipo específico
grep "error_type=ValidationError" logs/app.log

# Buscar operaciones lentas (>60 segundos)
grep -E "duration_seconds=[6-9][0-9]|duration_seconds=[0-9]{3}" logs/app.log
```

### En producción (JSON):

```bash
# Con jq (parser JSON)
cat logs/app.log | jq 'select(.event == "proposal_generated")'
cat logs/app.log | jq 'select(.duration_seconds > 60)'
cat logs/app.log | jq 'select(.error_type == "OpenAIError")'
```

---

## 📊 Métricas Automáticas

Con logs estructurados, puedes generar métricas fácilmente:

### Contar propuestas por tipo:
```bash
grep "proposal_generated" logs/app.log | grep -o "proposal_type=[^,]*" | sort | uniq -c
```

### Calcular promedio de duración:
```bash
grep "proposal_generated" logs/app.log | \
  grep -o "duration_seconds=[0-9.]*" | \
  cut -d= -f2 | \
  awk '{sum+=$1; count++} END {print sum/count}'
```

### Total de tokens consumidos (costo):
```bash
grep "tokens_used" logs/app.log | \
  grep -o "tokens_used=[0-9]*" | \
  cut -d= -f2 | \
  awk '{sum+=$1} END {print sum}'
```

---

## 🎨 Convenciones de Nombres

### Event Names (primer parámetro):
- **snake_case** siempre
- **Verbos en pasado** para acciones completadas: `proposal_generated`, `user_registered`
- **Verbos en presente** para estados: `loading_data`, `processing_request`

```python
# ✅ CORRECTO
logger.info("proposal_generated", ...)
logger.info("loading_technical_data", ...)
logger.error("validation_failed", ...)

# ❌ INCORRECTO
logger.info("ProposalGenerated", ...)  # No usar PascalCase
logger.info("generate_proposal", ...)  # Presente, no pasado
logger.info("Proposal generated", ...)  # Espacios, no snake_case
```

### Campos de contexto:
- **UUIDs**: Siempre convertir a string con `str(uuid)`
- **Duraciones**: Usar `duration_seconds` (float redondeado)
- **Timestamps**: Usar ISO 8601 con `.isoformat()`
- **Booleanos**: `has_*`, `is_*`, `should_*`

```python
# ✅ CORRECTO
logger.info(
    "data_loaded",
    project_id=str(project.id),  # UUID → str
    duration_seconds=round(duration, 2),  # Float redondeado
    timestamp=datetime.utcnow().isoformat(),  # ISO 8601
    has_ai_metadata=True,  # Boolean explícito
    filled_fields=15,  # Números sin unidad si es obvio
    completeness_percent=75.5  # Porcentajes con _percent
)
```

---

## 🔧 Integración con Observability Tools

### Datadog

```python
# Los logs JSON se envían automáticamente a Datadog
# Buscar en Datadog con queries como:
@event:proposal_generated @duration_seconds:>60
@error_type:OpenAIError
@proposal_type:Technical
```

### Grafana + Loki

```promql
# Query en Loki
{job="h2o-backend"} | json | event="proposal_generated" | duration_seconds > 60
```

### CloudWatch Insights

```sql
fields @timestamp, proposal_id, duration_seconds
| filter event = "proposal_generated"
| stats avg(duration_seconds) by proposal_type
```

---

## 📋 Checklist para Nuevos Logs

Antes de agregar un log, verifica:

- [ ] ¿El event name es **snake_case**?
- [ ] ¿Incluye **contexto suficiente** (IDs, duración, estado)?
- [ ] ¿Los UUIDs están convertidos a **string**?
- [ ] ¿Los errores incluyen **exc_info=True**?
- [ ] ¿Es **INFO, WARNING o ERROR** apropiado?
- [ ] ¿Ayudará a **debuggear** problemas en producción?

---

## 🎯 Ejemplos Completos

### Ejemplo 1: Operación con duración

```python
import time
import structlog

logger = structlog.get_logger(__name__)

async def process_data(project_id: UUID, user_id: UUID):
    start_time = time.time()
    
    logger.info(
        "data_processing_started",
        project_id=str(project_id),
        user_id=str(user_id)
    )
    
    try:
        result = await heavy_operation()
        
        logger.info(
            "data_processing_completed",
            project_id=str(project_id),
            user_id=str(user_id),
            duration_seconds=round(time.time() - start_time, 2),
            records_processed=len(result)
        )
        return result
        
    except Exception as e:
        logger.error(
            "data_processing_failed",
            exc_info=True,
            project_id=str(project_id),
            user_id=str(user_id),
            error_type=type(e).__name__,
            error_message=str(e),
            duration_seconds=round(time.time() - start_time, 2)
        )
        raise
```

### Ejemplo 2: Log con métricas de AI

```python
logger.info(
    "ai_request_completed",
    model="gpt-4o-mini",
    prompt_tokens=500,
    completion_tokens=1500,
    total_tokens=2000,
    cost_usd=0.02,
    duration_seconds=3.5,
    response_quality="high"
)
```

### Ejemplo 3: Log con decisión del sistema

```python
if use_cache:
    logger.info(
        "cache_hit",
        cache_key=cache_key,
        ttl_remaining=300
    )
else:
    logger.info(
        "cache_miss",
        cache_key=cache_key,
        reason="expired"
    )
```

---

## 🚀 Migración de Logs Existentes

### Antes (logging tradicional):
```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"✅ Proposal {proposal.id} generated in {duration}s")
logger.error(f"Error: {e}")
```

### Después (structlog):
```python
import structlog
logger = structlog.get_logger(__name__)

logger.info(
    "proposal_generated",
    proposal_id=str(proposal.id),
    duration_seconds=duration
)
logger.error(
    "operation_failed",
    exc_info=True,
    error_type=type(e).__name__
)
```

---

## 📚 Referencias

- [structlog Documentation](https://www.structlog.org/en/stable/)
- [JSON Logging Best Practices](https://betterstack.com/community/guides/logging/json-logging/)
- [Observability Best Practices 2025](https://www.datadoghq.com/blog/logging-best-practices/)

---

**¡Happy Logging! 🎉**
