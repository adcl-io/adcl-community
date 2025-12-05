# ADCL Bedrock Agent Driver Spec

## 1) Objectives

1. Add Bedrock as a first-class model driver without forking the orchestrator logic.  
2. Keep the JSON backend contract stable so agents, UI, and teams don’t care which model runs them.  
3. Support multiple Bedrock models (Anthropic, Llama, Titan, Cohere, etc.) with per-model overrides for params and tokenization.  
4. Ship with sane defaults, logging, quotas, and error mapping that won’t torch a weekend.  

---

## 2) Architecture Overview

1. New MCP server: `mcp_servers/bedrock`  
   - Single responsibility: translate ADCL’s JSON requests into Bedrock `InvokeModel` calls and translate responses back.  
   - Exposes a small HTTP API with streamable option later.  

2. Orchestrator integration  
   - Treat Bedrock like any other MCP. Orchestrator selects the driver based on agent config (`model_driver`).  
   - No driver logic inside the frontend.  

3. Agent definitions  
   - Extend JSON agent schema to allow `model_driver=bedrock` and a `model_id`.  
   - Optional per-model parameters (`max_tokens`, `temperature`, `top_p`, `stop_sequences`).  

4. Security and IAM  
   - Instance role or short-lived keys via environment.  
   - Policy with least privilege: `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream` for listed model IDs.  

---

## 3) HTTP API (MCP Server)

Base URL: `http://mcp-bedrock:7010`

### POST /v1/invoke

**Request**
```json
{
  "model_id": "anthropic.claude-3-5-sonnet-20240620-v1:0",
  "prompt": "string",
  "messages": [
    {"role": "system", "content": "string"},
    {"role": "user", "content": "string"}
  ],
  "params": {
    "max_tokens": 1024,
    "temperature": 0.2,
    "top_p": 0.95,
    "stop_sequences": ["</done>"]
  },
  "metadata": {
    "agent_id": "security-analyst",
    "task_id": "abc-123",
    "trace_id": "uuid"
  }
}
```

**Response**
```json
{
  "model_id": "anthropic.claude-3-5-sonnet-20240620-v1:0",
  "output_text": "string",
  "tokens": {
    "input": 123,
    "output": 456,
    "total": 579
  },
  "finish_reason": "stop|length|content_filter|unknown",
  "latency_ms": 1234,
  "raw": { "bedrock_response_snippet": {} }
}
```

### POST /v1/invoke-stream (phase 2)
- Server-sent events or chunked JSON stream with same envelope plus incremental deltas.

### GET /health
- Return 200 with driver version and model registry snapshot.

---

## 4) Backend Contracts (JSON-first)

### Agent Definition Extension
```json
{
  "id": "security-analyst",
  "name": "Security Analyst",
  "model_driver": "bedrock",
  "model_id": "anthropic.claude-3-5-sonnet-20240620-v1:0",
  "params": {
    "max_tokens": 1024,
    "temperature": 0.2,
    "top_p": 0.95
  },
  "tools": ["file.read", "nmap.scan"]
}
```

- Default driver remains Claude if not specified.  
- Unsupported model IDs return a typed error visible in UI.  
- Teams can mix drivers across agents.

---

## 5) Parameter Normalization

Normalize per model:
1. Common inputs: `max_tokens`, `temperature`, `top_p`, `stop_sequences`.  
2. Guardrails:
   - Clip temperature [0,2], top_p (0,1], max_tokens to provider cap minus margin.  
   - Validate `stop_sequences` size and chars.  
3. Token accounting:
   - Prefer provider-reported; fallback to estimate with tokenizer libs.

---

## 6) Error Model

**Mappings**
- `auth_error`: credentials or region mismatch.  
- `quota_exceeded`: rate/concurrency limit.  
- `bad_request`: invalid params/model_id.  
- `content_blocked`: Bedrock content filters.  
- `provider_error`: 5xx from Bedrock.  
- `timeout`: client-side timeout.

**Error Response**
```json
{
  "error": {
    "type": "quota_exceeded",
    "message": "rate limit reached",
    "provider_code": "ThrottlingException",
    "retry_after_ms": 2000
  }
}
```

---

## 7) Security and IAM

1. Credentials: instance profile or env vars (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`).  
2. IAM policy:
   - Actions: `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`.  
   - Resource: specific model ARNs.  
3. Network: internal-only container comms, outbound HTTPS to AWS only.

---

## 8) Observability

1. **Structured Logs (JSON)**
   - `trace_id`, `task_id`, `agent_id`, `model_id`, `latency_ms`, `status`, `tokens.total`.  
   - Redact prompts unless `REDACT_PROMPTS=false`.  

2. **Metrics**
   - `bedrock_invocations_total{model_id,status}`  
   - `bedrock_latency_ms_bucket`  
   - `bedrock_tokens_total{direction}`  
   - `bedrock_throttles_total`  

3. **Tracing**
   - Optional `traceparent` passthrough.

---

## 9) Quotas, Retries, Backoff

- Token bucket limiter per model.  
- Exponential backoff (max 3 tries, cap 2s).  
- Request timeout 30s default, longer for streaming.  

---

## 10) Containerization

**Dockerfile**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bedrock_mcp_server.py .
ENV UVICORN_WORKERS=1 PORT=7010
CMD ["python", "bedrock_mcp_server.py"]
```

**requirements.txt**
```
fastapi
uvicorn[standard]
boto3
httpx
orjson
```

**docker-compose.yml**
```yaml
  mcp-bedrock:
    build: ./mcp_servers/bedrock
    ports:
      - "7010:7010"
    environment:
      - AWS_REGION=${AWS_REGION:-us-east-1}
      - REDACT_PROMPTS=true
      - BEDROCK_QPS=5
      - BEDROCK_CONCURRENCY=2
    depends_on:
      - orchestrator
```

---

## 11) Orchestrator Wiring

- Add to `registries.conf` or `AUTO_INSTALL_MCPS`.  
- Tag service as `driver=bedrock`.  
- When `model_driver=bedrock`, orchestrator posts JSON to `/v1/invoke`.  

---

## 12) UI Integration

- Add dropdown for `model_driver` (claude, bedrock).  
- Show `model_id` and param fields when bedrock selected.  
- Validate ranges client-side.  
- Save config directly to `/app/agent-definitions/*.json`.

---

## 13) Test Plan

1. **Unit** – parameter normalization, error mapping.  
2. **Integration** – invoke real Bedrock API, validate response schema.  
3. **Regression** – run existing MCPs in parallel.  
4. **Load Smoke** – 100 sequential calls @ 2 concurrency, record p95 latency.  
5. **Security** – no secret logs, IAM scope validation.

---

## 14) Backward Compatibility

- Optional adoption per agent.  
- Stable JSON contract.  
- Same response envelope as other drivers.

---

## 15) Operational Playbook

**Config**
- `AWS_REGION`, `BEDROCK_QPS`, `BEDROCK_CONCURRENCY`, `REDACT_PROMPTS`.

**Runbooks**
- Throttling: reduce concurrency, check AWS quotas.  
- Latency: inspect p95, test alternate model IDs.  

**Dashboards**
- Errors by type, cost proxy (tokens.total), latency histograms.

---

## 16) Risks and Mitigations

1. Parameter mismatches — maintain per-model shim table.  
2. Cost spikes — add soft caps per agent/task.  
3. Token gaps — flag `estimated=true`.  
4. Vendor outages — implement circuit breaker on repeated failures.

---

## 17) Roadmap Follow-ons

1. Streaming endpoint support.  
2. Model discovery API.  
3. Cost budgets per agent.  
4. Benchmark suite for cross-model comparison.

---

## 18) Definition of Done

1. Service builds and runs under Compose.  
2. Agent executes with `model_driver=bedrock` successfully.  
3. Logs/metrics emitted, secrets redacted.  
4. Retry/backoff validated.  
5. Minimal UI edits complete.

---

## Views

**Neutral**
- Clean driver boundary, stable JSON contracts, no orchestrator refactor.  

**Devil’s Advocate**
- Inconsistent Bedrock parameters and token counts may obscure behavior.  
- Rate limits under load could cause visible jitter without tuned backoff.  

**Encouraging**
- Enables multi-model flexibility, cost/latency tradeoffs per agent, and marginalizes TPMs everywhere.  

