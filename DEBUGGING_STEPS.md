# 🔍 Pasos para Debuggear el Polling

## Paso 1: Verificar en el Navegador

1. **Abre Chrome/Firefox DevTools** (F12)
2. **Ve a la tab "Network"**
3. **Filtra por:** `jobs`
4. **Genera una propuesta** desde el frontend
5. **Observa qué requests se hacen**

### ¿Qué buscar?

#### ✅ Si el request se hace:
```
Request URL: http://localhost:8000/api/v1/ai/proposals/jobs/job_abc123
Status Code: 200 OK
Response: {
  "job_id": "job_abc123",
  "status": "processing",
  "progress": 40,
  ...
}
```
→ **Problema:** Frontend no procesa la respuesta correctamente

#### ❌ Si el request falla con 404:
```
Request URL: http://localhost:8000/api/v1/ai/proposals/jobs/job_abc123
Status Code: 404 Not Found
```
→ **Problema:** Endpoint no registrado o path incorrecto

#### ❌ Si el request NO se hace:
```
(No aparece nada en Network tab)
```
→ **Problema:** Frontend no está iniciando el polling

#### ❌ Si hay error de CORS:
```
Access to fetch at 'http://localhost:8000/api/v1/ai/proposals/jobs/...' 
from origin 'http://localhost:3000' has been blocked by CORS policy
```
→ **Problema:** CORS no configurado correctamente

---

## Paso 2: Verificar en Console del Navegador

1. **Abre Console tab**
2. **Busca errores** mientras genera propuesta
3. **Busca logs** de:
   - `pollProposalStatus`
   - `getJobStatus`
   - Cualquier error de red

### Errores Comunes:

#### Error 1: "Job not found"
```javascript
Error: Job not found or expired
```
→ Job ID no se guardó en Redis o expiró

#### Error 2: "Cannot read property X of undefined"
```javascript
TypeError: Cannot read property 'progress' of undefined
```
→ Estructura de respuesta no coincide

#### Error 3: Network error
```javascript
Failed to fetch
```
→ Backend no responde o CORS

---

## Paso 3: Verificar Backend Logs

```bash
# Ver logs en tiempo real
docker compose logs -f app

# Buscar específicamente:
# 1. Job creation
grep "Started proposal generation job"

# 2. Job status queries
grep "GET /api/v1/ai/proposals/jobs/"

# 3. Redis operations
grep "Redis"
```

### ¿Qué buscar?

#### ✅ Si ves esto:
```
✅ Started proposal generation job: job_abc123
✅ Proposal generated successfully
```
Pero NO ves:
```
GET /api/v1/ai/proposals/jobs/job_abc123
```
→ **Frontend NO está haciendo polling**

#### ✅ Si ves:
```
GET /api/v1/ai/proposals/jobs/job_abc123
404 Not Found
```
→ **Endpoint no está registrado correctamente**

---

## Paso 4: Verificar Redis

```bash
# Entrar a Redis
docker exec -it $(docker ps -q -f name=redis) redis-cli

# Ver todos los jobs
KEYS "job:*"

# Ver un job específico (reemplaza JOB_ID)
GET "job:job_abc123"

# Ver TTL (tiempo restante)
TTL "job:job_abc123"
```

### ¿Qué buscar?

- **Si no hay keys:** Job no se guardó en Redis
- **Si TTL = -2:** Job expiró
- **Si TTL > 0:** Job existe y es válido

---

## Paso 5: Test Manual con curl

```bash
# 1. Login
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test@example.com","password":"password123"}' \
  | jq -r '.access_token')

echo "Token: $TOKEN"

# 2. Generar propuesta
JOB_RESPONSE=$(curl -X POST http://localhost:8000/api/v1/ai/proposals/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"project_id":"YOUR_PROJECT_ID","proposal_type":"Technical"}')

echo "Job Response: $JOB_RESPONSE"

# 3. Extraer job_id
JOB_ID=$(echo $JOB_RESPONSE | jq -r '.job_id')
echo "Job ID: $JOB_ID"

# 4. Polling manual (ejecuta varias veces)
curl -X GET "http://localhost:8000/api/v1/ai/proposals/jobs/$JOB_ID" \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.'
```

### ¿Qué buscar?

- **Primera llamada:** `{"status": "queued", "progress": 0}`
- **Segunda llamada:** `{"status": "processing", "progress": 40}`
- **Última llamada:** `{"status": "completed", "progress": 100, "result": {...}}`

---

## 📊 Resultados Esperados

### ✅ CASO CORRECTO:
```
Network Tab:
  POST /ai/proposals/generate → 202 Accepted → {job_id: "job_abc"}
  GET /ai/proposals/jobs/job_abc → 200 OK → {status: "processing", progress: 20}
  GET /ai/proposals/jobs/job_abc → 200 OK → {status: "processing", progress: 40}
  ...
  GET /ai/proposals/jobs/job_abc → 200 OK → {status: "completed", progress: 100}

Console:
  (Sin errores)

Backend Logs:
  Started proposal generation job: job_abc
  AI metadata saved
  Proposal generated successfully
```

### ❌ CASO INCORRECTO (lo que está pasando ahora):
```
Network Tab:
  POST /ai/proposals/generate → 202 Accepted → {job_id: "job_abc"}
  (Nada más...)

Console:
  (Posibles errores)

Frontend UI:
  "Initializing... 0%" (stuck)
```

---

## 🎯 Próximo Paso

**Ejecuta Paso 1 ahora:**
1. Abre DevTools
2. Tab Network
3. Genera propuesta
4. **Toma screenshot de Network tab**
5. **Comparte screenshot**

Eso me dirá exactamente qué está pasando! 🚀
