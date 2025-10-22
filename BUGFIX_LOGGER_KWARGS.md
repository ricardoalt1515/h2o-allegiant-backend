# 🐛 BUGFIX: Logger._log() got an unexpected keyword argument 'usage_tokens'

**Fecha:** 15 Octubre 2025, 12:06 PM  
**Severidad:** Medium (bloqueaba generación al final)  
**Tiempo de fix:** 1 minuto

---

## 🔴 ERROR

```python
TypeError: Logger._log() got an unexpected keyword argument 'usage_tokens'
```

**Ubicación:**
```python
File "/app/app/agents/proposal_agent.py", line 345, in generate_enhanced_proposal
    logger.info(
        "✅ Proposal generated successfully",
        usage_tokens=result.usage().total_tokens if result.usage() else None
    )
```

---

## 🔍 CAUSA

El logger estándar de Python (`logging.Logger`) **NO acepta kwargs adicionales**.

```python
# ❌ INCORRECTO (no funciona con logging estándar):
logger.info("Message", custom_key=value)

# ✅ CORRECTO:
logger.info(f"Message - custom_key: {value}")
```

**Nota:** Algunos loggers como `structlog` SÍ aceptan kwargs, pero el logger estándar NO.

---

## ✅ SOLUCIÓN

### ANTES (causaba error):
```python
logger.info(
    "✅ Proposal generated successfully",
    usage_tokens=result.usage().total_tokens if result.usage() else None
)
```

### DESPUÉS (funciona):
```python
# Log success with token usage
usage = result.usage()
if usage:
    logger.info(f"✅ Proposal generated successfully - Tokens used: {usage.total_tokens}")
else:
    logger.info("✅ Proposal generated successfully")
```

---

## 📊 BENEFICIOS DEL FIX

1. **Más legible** ✅
   - Mensaje claro: "Tokens used: 1234"
   - No necesita parsear JSON

2. **Más robusto** ✅
   - Maneja caso cuando `usage()` es None
   - No falla si estructura cambia

3. **Estándar Python** ✅
   - Compatible con cualquier logger
   - No depende de features específicas

---

## 🧪 VALIDACIÓN

### Output esperado:

```
✅ Proposal generated successfully - Tokens used: 15234
```

O si no hay usage:
```
✅ Proposal generated successfully
```

---

## 🎓 LECCIÓN APRENDIDA

### Python logging estándar:
```python
import logging
logger = logging.getLogger(__name__)

# ❌ NO funciona:
logger.info("Message", key=value)

# ✅ Funciona:
logger.info(f"Message - key: {value}")
logger.info("Message", extra={'key': value})  # Solo con extra dict
```

### Structlog (acepta kwargs):
```python
import structlog
logger = structlog.get_logger()

# ✅ Funciona:
logger.info("Message", key=value)
```

---

**Estado:** ✅ FIXED - Listo para re-testing
