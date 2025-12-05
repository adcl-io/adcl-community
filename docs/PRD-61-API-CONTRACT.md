# PRD-61: API Contract for Workflow UI Improvements

**Issue:** PRD-61 - Update Workflow UI - Planning & Implementation  
**Created:** 2025-11-03  
**Updated:** 2025-11-04  
**Status:** Planning Phase

---

## Implementation Status

### ✅ Implemented (Existing - No Changes Needed)
- `POST /workflows/execute` - Execute workflow (non-streaming)
- `WS /ws/execute/{session_id}` - Execute workflow (streaming)
- `GET /workflows/examples` - List example workflows
- `GET /workflows/examples/{filename}` - Get example workflow
- `GET /mcp/servers` - List MCP servers
- `GET /mcp/servers/{name}/tools` - List MCP tools

**Note:** MCP endpoints work fine as-is. No format changes required.

### ❌ Not Implemented (Phase 1.4 - Required)
- `POST /workflows` - Save workflow
- `GET /workflows` - List saved workflows
- `GET /workflows/{id}` - Get workflow by ID
- `PUT /workflows/{id}` - Update workflow
- `DELETE /workflows/{id}` - Delete workflow

**Note:** These endpoints are **required** for Phase 1.4 to maintain the "no hidden state" principle. All workflow data must be stored server-side.

### ❌ Not Implemented (Phase 3.1)
- `GET /workflows/templates` - List workflow templates
- `GET /workflows/templates/{id}` - Get workflow template

### 🔮 Future (Phase 4 - Registry Integration)
- Migrate workflows to `registry/workflows/` structure
- Use `GET /registries/catalog?type=workflow` instead of `/workflows/templates`
- Add `POST /registries/install/workflow/{workflow_id}` for installation
- Deprecate `/workflows/examples` endpoints
- Add workflow signing and verification

**Note:** Phase 4 will align workflows with the registry paradigm used by MCPs, teams, and triggers. This provides versioning, signing, and consistent package management.

---

## Overview

This document defines the API contract for backend changes required to support the workflow UI improvements. The contract is divided into three sections:

1. **Current Endpoints** - Exist but need format updates
2. **New Endpoints (Phase 1.4)** - Workflow CRUD operations
3. **New Endpoints (Phase 3.1)** - Template management

---

## New Endpoints (Phase 1.4)

### Save Workflow

```http
POST /workflows
Content-Type: application/json

{
  "name": "My Workflow",
  "description": "Optional description",
  "workflow": {
    "nodes": [...],
    "edges": [...]
  }
}
```

**Response:**
```json
{
  "id": "wf_20251103_230000_abc123",
  "name": "My Workflow",
  "created": "2025-11-03T23:00:00Z",
  "modified": "2025-11-03T23:00:00Z"
}
```

**Status Codes:**
- `201 Created` - Workflow saved successfully
- `400 Bad Request` - Invalid workflow data
- `500 Internal Server Error` - Server error

---

### List Workflows

```http
GET /workflows
```

**Query Parameters:**
- `limit` (optional): Max number of workflows to return (default: 50)
- `offset` (optional): Pagination offset (default: 0)
- `sort` (optional): Sort field (name, created, modified) (default: modified)
- `order` (optional): Sort order (asc, desc) (default: desc)

**Response:**
```json
{
  "workflows": [
    {
      "id": "wf_20251103_230000_abc123",
      "name": "My Workflow",
      "description": "Optional description",
      "created": "2025-11-03T23:00:00Z",
      "modified": "2025-11-03T23:00:00Z",
      "node_count": 5,
      "edge_count": 4
    }
  ],
  "total": 10,
  "limit": 50,
  "offset": 0
}
```

**Status Codes:**
- `200 OK` - Workflows retrieved successfully
- `500 Internal Server Error` - Server error

---

### Get Workflow

```http
GET /workflows/{id}
```

**Response:**
```json
{
  "id": "wf_20251103_230000_abc123",
  "name": "My Workflow",
  "description": "Optional description",
  "created": "2025-11-03T23:00:00Z",
  "modified": "2025-11-03T23:00:00Z",
  "workflow": {
    "nodes": [...],
    "edges": [...]
  }
}
```

**Status Codes:**
- `200 OK` - Workflow retrieved successfully
- `404 Not Found` - Workflow not found
- `500 Internal Server Error` - Server error

---

### Update Workflow

```http
PUT /workflows/{id}
Content-Type: application/json

{
  "name": "Updated Workflow Name",
  "description": "Updated description",
  "workflow": {
    "nodes": [...],
    "edges": [...]
  }
}
```

**Response:**
```json
{
  "id": "wf_20251103_230000_abc123",
  "name": "Updated Workflow Name",
  "modified": "2025-11-03T23:05:00Z"
}
```

**Status Codes:**
- `200 OK` - Workflow updated successfully
- `404 Not Found` - Workflow not found
- `400 Bad Request` - Invalid workflow data
- `500 Internal Server Error` - Server error

---

### Delete Workflow

```http
DELETE /workflows/{id}
```

**Response:**
```json
{
  "success": true,
  "id": "wf_20251103_230000_abc123"
}
```

**Status Codes:**
- `200 OK` - Workflow deleted successfully
- `404 Not Found` - Workflow not found
- `500 Internal Server Error` - Server error

---

## New Endpoints (Phase 3.1)

### List Workflow Templates

```http
GET /workflows/templates
```

**Query Parameters:**
- `category` (optional): Filter by category (security, development, data-processing)

**Response:**
```json
{
  "templates": [
    {
      "id": "security-scan",
      "name": "Security Scan",
      "description": "Comprehensive security scanning workflow",
      "category": "security",
      "tags": ["security", "nmap", "vulnerability"],
      "node_count": 8,
      "edge_count": 7,
      "preview_image": "/templates/security-scan.png"
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Templates retrieved successfully
- `500 Internal Server Error` - Server error

---

### Get Workflow Template

```http
GET /workflows/templates/{id}
```

**Response:**
```json
{
  "id": "security-scan",
  "name": "Security Scan",
  "description": "Comprehensive security scanning workflow",
  "category": "security",
  "tags": ["security", "nmap", "vulnerability"],
  "workflow": {
    "nodes": [...],
    "edges": [...]
  }
}
```

**Status Codes:**
- `200 OK` - Template retrieved successfully
- `404 Not Found` - Template not found
- `500 Internal Server Error` - Server error

---

## Backend Implementation

### File Storage Structure

```
workflows/
├── user/                           # User-created workflows
│   ├── wf_20251103_230000_abc123.json
│   ├── wf_20251103_230100_def456.json
│   └── ...
└── templates/                      # Workflow templates
    ├── security-scan.json
    ├── code-review.json
    ├── data-pipeline.json
    └── api-integration.json
```

### Workflow File Format

```json
{
  "id": "wf_20251103_230000_abc123",
  "name": "My Workflow",
  "description": "Optional description",
  "created": "2025-11-03T23:00:00Z",
  "modified": "2025-11-03T23:00:00Z",
  "workflow": {
    "nodes": [
      {
        "id": "node-1",
        "type": "mcp_call",
        "mcp_server": "agent",
        "tool": "think",
        "params": {
          "prompt": "What is MCP?"
        }
      }
    ],
    "edges": [
      {
        "source": "node-1",
        "target": "node-2"
      }
    ]
  }
}
```

### Backend Code Changes

**File:** `backend/app/main.py`

```python
from pathlib import Path
import json
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException

# Workflow storage directory
WORKFLOWS_DIR = Path("workflows/user")
TEMPLATES_DIR = Path("workflows/templates")

# Ensure directories exist
WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


# Models
class WorkflowMetadata(BaseModel):
    id: str
    name: str
    description: Optional[str] = ""
    created: str
    modified: str
    node_count: int = 0
    edge_count: int = 0


class WorkflowSaveRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    workflow: WorkflowDefinition


class WorkflowUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    workflow: Optional[WorkflowDefinition] = None


# Endpoints
@app.post("/workflows", response_model=WorkflowMetadata)
async def save_workflow(request: WorkflowSaveRequest):
    """Save a new workflow"""
    # Generate workflow ID
    workflow_id = f"wf_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    
    # Create workflow data
    workflow_data = {
        "id": workflow_id,
        "name": request.name,
        "description": request.description,
        "created": datetime.now().isoformat(),
        "modified": datetime.now().isoformat(),
        "workflow": request.workflow.dict()
    }
    
    # Save to file
    workflow_file = WORKFLOWS_DIR / f"{workflow_id}.json"
    with open(workflow_file, "w") as f:
        json.dump(workflow_data, f, indent=2)
    
    return WorkflowMetadata(
        id=workflow_id,
        name=request.name,
        description=request.description,
        created=workflow_data["created"],
        modified=workflow_data["modified"],
        node_count=len(request.workflow.nodes),
        edge_count=len(request.workflow.edges)
    )


@app.get("/workflows")
async def list_workflows(
    limit: int = 50,
    offset: int = 0,
    sort: str = "modified",
    order: str = "desc"
):
    """List all saved workflows"""
    workflows = []
    
    # Read all workflow files
    for workflow_file in WORKFLOWS_DIR.glob("*.json"):
        with open(workflow_file) as f:
            data = json.load(f)
            workflows.append(WorkflowMetadata(
                id=data["id"],
                name=data["name"],
                description=data.get("description", ""),
                created=data["created"],
                modified=data["modified"],
                node_count=len(data["workflow"]["nodes"]),
                edge_count=len(data["workflow"]["edges"])
            ))
    
    # Sort workflows
    reverse = (order == "desc")
    workflows.sort(key=lambda w: getattr(w, sort), reverse=reverse)
    
    # Paginate
    total = len(workflows)
    workflows = workflows[offset:offset + limit]
    
    return {
        "workflows": workflows,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@app.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get a specific workflow"""
    workflow_file = WORKFLOWS_DIR / f"{workflow_id}.json"
    
    if not workflow_file.exists():
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    with open(workflow_file) as f:
        return json.load(f)


@app.put("/workflows/{workflow_id}")
async def update_workflow(workflow_id: str, request: WorkflowUpdateRequest):
    """Update an existing workflow"""
    workflow_file = WORKFLOWS_DIR / f"{workflow_id}.json"
    
    if not workflow_file.exists():
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Load existing workflow
    with open(workflow_file) as f:
        data = json.load(f)
    
    # Update fields
    if request.name:
        data["name"] = request.name
    if request.description is not None:
        data["description"] = request.description
    if request.workflow:
        data["workflow"] = request.workflow.dict()
    
    data["modified"] = datetime.now().isoformat()
    
    # Save updated workflow
    with open(workflow_file, "w") as f:
        json.dump(data, f, indent=2)
    
    return {
        "id": workflow_id,
        "name": data["name"],
        "modified": data["modified"]
    }


@app.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """Delete a workflow"""
    workflow_file = WORKFLOWS_DIR / f"{workflow_id}.json"
    
    if not workflow_file.exists():
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow_file.unlink()
    
    return {"success": True, "id": workflow_id}


@app.get("/workflows/templates")
async def list_templates(category: Optional[str] = None):
    """List workflow templates"""
    templates = []
    
    for template_file in TEMPLATES_DIR.glob("*.json"):
        with open(template_file) as f:
            data = json.load(f)
            
            # Filter by category if specified
            if category and data.get("category") != category:
                continue
            
            templates.append({
                "id": data["id"],
                "name": data["name"],
                "description": data.get("description", ""),
                "category": data.get("category", "general"),
                "tags": data.get("tags", []),
                "node_count": len(data["workflow"]["nodes"]),
                "edge_count": len(data["workflow"]["edges"]),
                "preview_image": data.get("preview_image")
            })
    
    return {"templates": templates}


@app.get("/workflows/templates/{template_id}")
async def get_template(template_id: str):
    """Get a specific template"""
    template_file = TEMPLATES_DIR / f"{template_id}.json"
    
    if not template_file.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    
    with open(template_file) as f:
        return json.load(f)
```

---

## Error Handling

### Standard Error Response

```json
{
  "detail": "Error message",
  "status_code": 400
}
```

### Common Error Codes

- `400 Bad Request` - Invalid request data
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

### Validation Errors

```json
{
  "detail": [
    {
      "loc": ["body", "workflow", "nodes"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Security Considerations

### Authentication (Future)

Currently no authentication required. In production:
- Add JWT authentication
- User-specific workflow storage
- Rate limiting on API endpoints

### Input Validation

- Validate workflow structure
- Sanitize workflow names
- Limit workflow size (max nodes, edges)
- Prevent path traversal in workflow IDs

### File System Security

- Store workflows in dedicated directory
- Use UUID-based filenames
- Validate file extensions
- Limit file sizes

---

## Performance Considerations

### Caching

- Cache workflow list in memory
- Invalidate cache on create/update/delete
- Use ETags for conditional requests

### Pagination

- Default limit: 50 workflows
- Max limit: 100 workflows
- Offset-based pagination

### File I/O

- Async file operations
- Batch operations where possible
- Monitor disk usage

---

## Migration Strategy

### Existing Workflows

Existing example workflows in `workflows/` directory:
- Move to `workflows/templates/`
- Add metadata (id, category, tags)
- Keep backward compatibility

### Frontend Changes

Frontend should:
- Try new endpoints first
- Fall back to localStorage if endpoints fail
- Migrate localStorage workflows to backend on first save

---

## Testing

### Unit Tests

```python
# test_workflow_api.py

def test_save_workflow():
    response = client.post("/workflows", json={
        "name": "Test Workflow",
        "workflow": {...}
    })
    assert response.status_code == 201
    assert "id" in response.json()

def test_list_workflows():
    response = client.get("/workflows")
    assert response.status_code == 200
    assert "workflows" in response.json()

def test_get_workflow():
    # Create workflow first
    create_response = client.post("/workflows", json={...})
    workflow_id = create_response.json()["id"]
    
    # Get workflow
    response = client.get(f"/workflows/{workflow_id}")
    assert response.status_code == 200
    assert response.json()["id"] == workflow_id

def test_update_workflow():
    # Create workflow first
    create_response = client.post("/workflows", json={...})
    workflow_id = create_response.json()["id"]
    
    # Update workflow
    response = client.put(f"/workflows/{workflow_id}", json={
        "name": "Updated Name"
    })
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"

def test_delete_workflow():
    # Create workflow first
    create_response = client.post("/workflows", json={...})
    workflow_id = create_response.json()["id"]
    
    # Delete workflow
    response = client.delete(f"/workflows/{workflow_id}")
    assert response.status_code == 200
    assert response.json()["success"] == True
    
    # Verify deleted
    get_response = client.get(f"/workflows/{workflow_id}")
    assert get_response.status_code == 404
```

### Integration Tests

- Test workflow save → list → get → update → delete flow
- Test template listing and retrieval
- Test error cases (not found, invalid data)
- Test pagination and sorting

---

## Documentation

### API Documentation

FastAPI automatically generates:
- OpenAPI schema at `/openapi.json`
- Swagger UI at `/docs`
- ReDoc at `/redoc`

### Example Requests

Include example requests in API docs:
- cURL commands
- JavaScript fetch examples
- Python requests examples

---

**Document Version:** 1.0  
**Last Updated:** 2025-11-03  
**Next Review:** After Phase 1 implementation
