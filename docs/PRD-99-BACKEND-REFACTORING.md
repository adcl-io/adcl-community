# PRD-99: Backend Architecture Refactoring

## Overview
Refactor the 3,006-line `backend/app/main.py` monolith into a clean, modular architecture following ADCL principles. Transform the backend into a maintainable, testable, and scalable codebase with clear separation of concerns.

## Status
**PLANNING** - 2025-11-15

## Problem Statement

### Current State
- **main.py**: 3,006 lines (violates single responsibility principle)
- **Duplicate code**: WorkflowEngine exists in multiple places
- **No service layer**: Business logic mixed with API routes
- **Missing health checks**: Dockerfiles lack health check endpoints
- **Missing directories**: logs/, packages/, volumes/ not created
- **Low test coverage**: <30% coverage for critical paths
- **Hard to maintain**: Changes require touching massive files

### Impact
- **Developer velocity**: Simple changes touch 100+ line diffs
- **Code quality**: Difficult to review, test, and reason about
- **Deployment risk**: Changes have unpredictable side effects
- **Onboarding**: New developers struggle to understand architecture
- **Testing**: Integration tests are slow and brittle

## Goals

### Primary Goals
1. **Reduce main.py to <300 lines** - From 3,006 to simple application bootstrap
2. **Extract 7 service classes** - Clean separation of concerns
3. **Create proper API layer** - Route handlers separate from business logic
4. **Achieve 80%+ test coverage** - Unit + integration tests
5. **Zero regressions** - All existing functionality must work

### Non-Goals
- ❌ Rewrite functionality (refactor only)
- ❌ Change external APIs (maintain backward compatibility)
- ❌ Microservices migration (keep monolithic deployment)
- ❌ Database migration (state management unchanged)
- ❌ Frontend changes (backend only)

## Architecture

### Current Architecture (Anti-Pattern)
```
backend/app/
├── main.py (3,006 lines)    ← EVERYTHING HERE
│   ├── FastAPI app
│   ├── 7+ service classes
│   ├── 15+ route handlers
│   ├── Business logic
│   ├── WebSocket handlers
│   └── Utility functions
├── agent_runtime.py
└── mcp_registry.py
```

### Target Architecture (ADCL Compliant)
```
backend/
├── app/
│   ├── main.py (<300 lines)           ← Bootstrap only
│   ├── api/                           ← Route handlers
│   │   ├── __init__.py
│   │   ├── agents.py
│   │   ├── workflows.py
│   │   ├── teams.py
│   │   ├── executions.py
│   │   ├── models_api.py
│   │   ├── triggers.py
│   │   └── mcp.py
│   ├── services/                      ← Business logic
│   │   ├── __init__.py
│   │   ├── agent_service.py
│   │   ├── workflow_service.py
│   │   ├── team_service.py
│   │   ├── execution_service.py
│   │   ├── model_service.py
│   │   ├── mcp_service.py
│   │   └── docker_service.py
│   ├── core/                          ← Shared utilities
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── errors.py
│   │   └── logging.py
│   ├── agent_runtime.py               ← Existing
│   ├── mcp_registry.py                ← Existing
│   └── token_tracker.py               ← Existing
└── tests/
    ├── unit/
    │   ├── test_agent_service.py
    │   ├── test_workflow_service.py
    │   └── ...
    └── integration/
        ├── test_agent_api.py
        ├── test_workflow_api.py
        └── ...
```

## Implementation Plan

### Phase 1: Foundation (Day 1 - 8 hours)
**Goal**: Set up directory structure and health checks

**Tasks**:
1. Create directory structure
   ```bash
   mkdir -p backend/app/{api,services,core}
   mkdir -p backend/tests/{unit,integration}
   mkdir -p logs packages volumes/data
   ```

2. Add health checks to all Dockerfiles
   ```dockerfile
   HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
     CMD curl -f http://localhost:8000/health || exit 1
   ```

3. Create core modules
   - `core/config.py` - Configuration management
   - `core/dependencies.py` - Dependency injection
   - `core/errors.py` - Custom exceptions
   - `core/logging.py` - Structured logging

**Acceptance Criteria**:
- ✅ All directories exist
- ✅ Health checks pass in all containers
- ✅ Core modules importable
- ✅ No broken imports

**Files to Create**:
- `backend/app/core/config.py`
- `backend/app/core/dependencies.py`
- `backend/app/core/errors.py`
- `backend/app/core/logging.py`
- `backend/app/api/__init__.py`
- `backend/app/services/__init__.py`

### Phase 2: Service Extraction (Days 2-4 - 24 hours)
**Goal**: Extract 7 services from main.py

#### Service 1: AgentService (Day 2)
```python
# backend/app/services/agent_service.py
class AgentService:
    """Manages agent definitions and lifecycle"""

    def __init__(self, agent_dir: Path):
        self.agent_dir = agent_dir

    async def list_agents(self) -> List[dict]:
        """Load all agent definitions"""

    async def get_agent(self, agent_id: str) -> dict:
        """Get single agent definition"""

    async def create_agent(self, agent_data: dict) -> dict:
        """Create new agent definition"""

    async def update_agent(self, agent_id: str, agent_data: dict) -> dict:
        """Update agent definition"""

    async def delete_agent(self, agent_id: str) -> bool:
        """Delete agent definition"""
```

**Extract from main.py**:
- Lines 200-350 (agent loading logic)
- Lines 450-520 (agent CRUD operations)

#### Service 2: WorkflowService (Day 2)
```python
# backend/app/services/workflow_service.py
class WorkflowService:
    """Manages workflow definitions and execution"""

    async def list_workflows(self) -> List[dict]:
        """Load all workflows"""

    async def get_workflow(self, workflow_id: str) -> dict:
        """Get workflow definition"""

    async def create_workflow(self, workflow_data: dict) -> dict:
        """Create new workflow"""

    async def execute_workflow(self, workflow_id: str, params: dict) -> dict:
        """Execute workflow with parameters"""
```

**⚠️ CRITICAL**: Delete duplicate WorkflowEngine class

**Extract from main.py**:
- Lines 520-680 (workflow logic)
- Remove duplicate WorkflowEngine

#### Service 3: TeamService (Day 3)
```python
# backend/app/services/team_service.py
class TeamService:
    """Manages agent teams and coordination"""

    async def list_teams(self) -> List[dict]:
        """Load all team definitions"""

    async def get_team(self, team_id: str) -> dict:
        """Get team definition"""

    async def create_team(self, team_data: dict) -> dict:
        """Create new team"""
```

**Extract from main.py**:
- Lines 680-820 (team management logic)

#### Service 4: ExecutionService (Day 3)
```python
# backend/app/services/execution_service.py
class ExecutionService:
    """Tracks and manages execution state"""

    async def create_execution(self, execution_data: dict) -> str:
        """Create execution record"""

    async def get_execution(self, execution_id: str) -> dict:
        """Get execution status"""

    async def update_execution(self, execution_id: str, updates: dict):
        """Update execution state"""

    async def cancel_execution(self, execution_id: str):
        """Cancel running execution"""
```

**Extract from main.py**:
- Lines 820-950 (execution tracking)
- Lines 1200-1350 (execution state management)

#### Service 5: ModelService (Day 4)
```python
# backend/app/services/model_service.py
class ModelService:
    """Manages model configurations"""

    async def list_models(self) -> List[dict]:
        """Load model configurations"""

    async def get_model(self, model_id: str) -> dict:
        """Get model config"""

    async def set_default_model(self, model_id: str):
        """Set default model"""
```

**Extract from main.py**:
- Lines 100-200 (model loading)
- Lines 350-450 (model management)

#### Service 6: MCPService (Day 4)
```python
# backend/app/services/mcp_service.py
class MCPService:
    """Manages MCP server registry"""

    def __init__(self, registry: MCPServerRegistry):
        self.registry = registry

    async def list_servers(self) -> List[dict]:
        """List available MCP servers"""

    async def get_server_tools(self, server_id: str) -> List[dict]:
        """Get tools from MCP server"""
```

**Extract from main.py**:
- Lines 950-1100 (MCP integration)

#### Service 7: DockerService (Day 4)
```python
# backend/app/services/docker_service.py
class DockerService:
    """Manages Docker container lifecycle"""

    async def list_containers(self) -> List[dict]:
        """List running containers"""

    async def start_container(self, image: str, config: dict) -> str:
        """Start new container"""

    async def stop_container(self, container_id: str):
        """Stop running container"""
```

**Extract from main.py**:
- Lines 1100-1200 (Docker management)

**Acceptance Criteria**:
- ✅ Each service has single responsibility
- ✅ Services are independently testable
- ✅ No circular dependencies
- ✅ All main.py logic extracted
- ✅ Unit tests for each service (>80% coverage)

### Phase 3: API Layer Refactoring (Days 5-6 - 16 hours)
**Goal**: Separate route handlers from main.py

#### Create Route Modules

**backend/app/api/agents.py**
```python
from fastapi import APIRouter, Depends
from app.services.agent_service import AgentService
from app.core.dependencies import get_agent_service

router = APIRouter(prefix="/agents", tags=["agents"])

@router.get("")
async def list_agents(service: AgentService = Depends(get_agent_service)):
    return await service.list_agents()

@router.get("/{agent_id}")
async def get_agent(agent_id: str, service: AgentService = Depends(get_agent_service)):
    return await service.get_agent(agent_id)

@router.post("")
async def create_agent(agent_data: dict, service: AgentService = Depends(get_agent_service)):
    return await service.create_agent(agent_data)
```

**Similar modules**:
- `api/workflows.py` - Workflow routes
- `api/teams.py` - Team routes
- `api/executions.py` - Execution routes
- `api/models_api.py` - Model routes
- `api/triggers.py` - Trigger routes
- `api/mcp.py` - MCP routes

**New main.py** (target: <300 lines):
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agents, workflows, teams, executions, models_api, triggers, mcp
from app.core.config import settings
from app.core.dependencies import get_services

app = FastAPI(title="ADCL Orchestrator")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agents.router)
app.include_router(workflows.router)
app.include_router(teams.router)
app.include_router(executions.router)
app.include_router(models_api.router)
app.include_router(triggers.router)
app.include_router(mcp.router)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "orchestrator"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Acceptance Criteria**:
- ✅ main.py < 300 lines
- ✅ All routes migrated to api/ modules
- ✅ Dependency injection working
- ✅ No broken endpoints
- ✅ API tests pass

### Phase 4: Testing & Validation (Days 7-8 - 16 hours)
**Goal**: Achieve 80%+ test coverage with zero regressions

#### Unit Tests
**Create test files**:
- `tests/unit/test_agent_service.py`
- `tests/unit/test_workflow_service.py`
- `tests/unit/test_team_service.py`
- `tests/unit/test_execution_service.py`
- `tests/unit/test_model_service.py`
- `tests/unit/test_mcp_service.py`
- `tests/unit/test_docker_service.py`

**Coverage targets**:
- Each service: >80% line coverage
- Critical paths: 100% coverage
- Edge cases: Covered

#### Integration Tests
**Create test files**:
- `tests/integration/test_agent_api.py`
- `tests/integration/test_workflow_api.py`
- `tests/integration/test_team_api.py`
- `tests/integration/test_execution_api.py`

**Test scenarios**:
- End-to-end agent execution
- Workflow orchestration
- Team coordination
- Execution tracking
- Model management

#### Performance Tests
**Regression testing**:
- Agent execution time: No slower than baseline
- API response time: <200ms for CRUD operations
- Memory usage: No leaks
- Concurrent execution: Support 10+ parallel agents

**Acceptance Criteria**:
- ✅ 80%+ unit test coverage
- ✅ All integration tests pass
- ✅ No performance regressions
- ✅ All existing tests still pass
- ✅ CI/CD pipeline green

### Phase 5: Documentation (Day 9 - 8 hours)
**Goal**: Update all documentation

#### Architecture Documentation
**Update/Create**:
- `docs/ARCHITECTURE.md` - New three-tier architecture
- `docs/SERVICE_DIRECTORY.md` - Service catalog
- `docs/API_DOCUMENTATION.md` - OpenAPI spec
- `docs/MIGRATION_GUIDE.md` - How to navigate new structure

#### Code Documentation
**Add docstrings**:
- Every service class
- Every public method
- Complex business logic
- API endpoints

#### Developer Onboarding
**Create**:
- `docs/DEVELOPMENT_SETUP.md` - Local dev environment
- `docs/TESTING_GUIDE.md` - How to run tests
- `docs/CONTRIBUTING.md` - Code contribution guidelines

**Acceptance Criteria**:
- ✅ All services have docstrings
- ✅ Architecture diagrams updated
- ✅ API documentation complete
- ✅ Migration guide written
- ✅ Developer onboarding docs complete

### Phase 6: Cleanup (Day 10 - 8 hours)
**Goal**: Remove dead code and polish

#### Dead Code Removal
- Delete unused imports
- Remove commented-out code
- Delete duplicate functions
- Clean up temporary files

#### Code Formatting
- Run `black` on all Python files
- Run `isort` for import sorting
- Run `flake8` for linting
- Fix all warnings

#### Dependency Cleanup
- Update `requirements.txt`
- Remove unused dependencies
- Pin dependency versions
- Document dependency rationale

**Acceptance Criteria**:
- ✅ No dead code
- ✅ Consistent formatting
- ✅ No linting warnings
- ✅ Clean requirements.txt

### Phase 7: Optional Future Enhancements
**Not included in initial 10-day sprint**

#### In-Process Event Bus
- Decouple services with events
- Async event processing
- Event sourcing for audit trail

#### Async Workers (Celery)
- Long-running workflow execution
- Background job processing
- Scheduled tasks

#### Microservices (Only If Needed)
- Extract services to separate deployments
- Service mesh (Istio/Linkerd)
- Independent scaling

## ADCL Principles Compliance

### ✅ Configuration is Code
- All configs in text files (YAML/JSON/TOML)
- No database-stored configuration
- Version controlled

### ✅ Directory Structure
```
backend/
├── app/
│   ├── api/          ← Route handlers (presentation layer)
│   ├── services/     ← Business logic (service layer)
│   ├── core/         ← Shared utilities
│   └── main.py       ← Bootstrap (<300 lines)
├── tests/
│   ├── unit/         ← Service tests
│   └── integration/  ← API tests
└── requirements.txt
```

### ✅ Modularity Rules
- Each service has single responsibility
- Services communicate via dependency injection
- No circular dependencies
- Independently testable

### ✅ Error Handling
- Custom exceptions in `core/errors.py`
- Structured error responses
- Comprehensive logging
- Graceful degradation

### ✅ No Hardcoded Values
- All config externalized
- Environment-based configuration
- No magic numbers or strings

## Risk Management

### High-Risk Areas
1. **WebSocket handlers** - Complex state management
2. **Execution tracking** - Race conditions possible
3. **MCP integration** - External dependencies
4. **Workflow orchestration** - Complex coordination logic

### Mitigation Strategies
1. **Feature branch development** - No direct commits to main
2. **Continuous testing** - Run tests after each change
3. **Incremental refactoring** - One service at a time
4. **Keep main.py working** - Don't break until end
5. **Comprehensive integration tests** - Catch regressions early

### Rollback Plan
- Each phase is a separate commit
- Can cherry-pick or revert individual phases
- Feature flag for new architecture (if needed)
- Keep old main.py until full validation

## Success Metrics

### Quantitative Metrics
- ✅ main.py: 3,006 → <300 lines (90% reduction)
- ✅ Test coverage: <30% → >80% (>50% improvement)
- ✅ Code duplication: 15% → <5% (remove WorkflowEngine duplicate)
- ✅ Cyclomatic complexity: Avg 20 → <10 (50% reduction)
- ✅ Number of services: 0 → 7 (clear separation)

### Qualitative Metrics
- ✅ Code reviewability: PRs are <500 lines (currently 1000+)
- ✅ Onboarding time: New dev productive in 2 days (currently 5 days)
- ✅ Bug fix time: Average 2 hours (currently 8 hours)
- ✅ Developer confidence: High confidence in changes (currently low)

## Timeline

### 10 Working Days (2 Weeks)

| Phase | Days | Effort | Deliverables |
|-------|------|--------|--------------|
| Phase 1: Foundation | Day 1 | 8h | Directory structure, health checks, core modules |
| Phase 2: Services | Days 2-4 | 24h | 7 service classes extracted, unit tests |
| Phase 3: API Layer | Days 5-6 | 16h | Route handlers separated, main.py <300 lines |
| Phase 4: Testing | Days 7-8 | 16h | 80%+ coverage, integration tests, performance tests |
| Phase 5: Documentation | Day 9 | 8h | Architecture docs, API docs, migration guide |
| Phase 6: Cleanup | Day 10 | 8h | Dead code removed, formatting, dependency cleanup |
| **Total** | **10 days** | **80 hours** | **Production-ready refactored backend** |

## Deployment Checklist

### Pre-Deployment
- [ ] All tests pass (unit + integration)
- [ ] Performance tests show no regressions
- [ ] Code review completed
- [ ] Documentation updated
- [ ] Migration guide reviewed

### Deployment
- [ ] Deploy to staging environment
- [ ] Run smoke tests
- [ ] Run integration tests against staging
- [ ] Monitor for 24 hours
- [ ] Get approval from team

### Post-Deployment
- [ ] Deploy to production
- [ ] Monitor error rates
- [ ] Monitor performance metrics
- [ ] Gather developer feedback
- [ ] Create retrospective document

## Review Requirements

### Code Quality
- [ ] All services follow single responsibility principle
- [ ] No circular dependencies
- [ ] Dependency injection used throughout
- [ ] Error handling comprehensive
- [ ] Logging structured and consistent

### Architecture Review
- [ ] Run `linus-torvalds` agent for Unix philosophy compliance
- [ ] Verify three-tier architecture (API → Service → Data)
- [ ] Check service boundaries
- [ ] Validate dependency injection

### QA Review
- [ ] Run `code-nitpicker-9000` agent for quality checks
- [ ] Verify test coverage >80%
- [ ] Check for dead code
- [ ] Validate documentation completeness

## References

### Related Documents
- `docs/REFACTORING_TASK_LIST.md` - Detailed task breakdown
- `docs/ARCHITECTURE_ANALYSIS.md` - Current architecture analysis
- `docs/ARCHITECTURE_OPTIONS_ANALYSIS.md` - Architecture options compared
- `CLAUDE.md` - ADCL principles and guidelines

### Related PRDs
- PRD-98: Token Tracking (demonstrates clean service pattern)
- PRD-97: Playground History UI/UX
- PRD-89: Full agent reasoning

## Conclusion

PRD-99 transforms the ADCL backend from a 3,006-line monolith into a clean, modular, testable architecture:

**Before**:
- 3,006-line main.py
- No separation of concerns
- <30% test coverage
- Hard to maintain and extend

**After**:
- <300-line main.py (bootstrap only)
- 7 focused service classes
- >80% test coverage
- Clear three-tier architecture
- Easy to maintain and extend

**Implementation Approach**:
- ✅ Incremental refactoring (one service at a time)
- ✅ Continuous testing (no big-bang rewrite)
- ✅ ADCL principles compliant
- ✅ Zero regressions
- ✅ Production-ready in 10 working days

The refactoring follows ADCL's Unix philosophy: "Do one thing well, communicate via clear interfaces, compose simple modules into complex systems."

**Status**: Ready for implementation ✅
