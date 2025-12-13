# Workflow V2 Tests

## Test Structure

- **Unit Tests** - Run locally with mocks, no dependencies
  - `test_validation.py` - DAG validation tests (10 tests)
  - `test_executor.py` - Executor logic tests (5 tests)

- **Integration Tests** - Require full production environment
  - `test_integration.py` - End-to-end workflow execution (7 tests)
  - `test_api_integration.py` - API endpoint tests (9 tests)

## Running Unit Tests

Unit tests use mocks and can run locally:

```bash
cd backend
source ../venv/bin/activate
PYTHONPATH=. pytest tests/workflow_v2/test_validation.py tests/workflow_v2/test_executor.py -v
```

**Expected:** 15 tests pass

## Running Integration Tests

Integration tests require full environment (configs, MCPs, agents). Run on production servers:

### Option 1: Production Server

```bash
# SSH to production server
ssh ubuntu@98.81.106.149

# Navigate to project
cd /opt/demo-sandbox

# Remove skip markers
sed -i '/pytestmark = pytest.mark.skip/d' backend/tests/workflow_v2/test_integration.py
sed -i '/pytestmark = pytest.mark.skip/d' backend/tests/workflow_v2/test_api_integration.py

# Run tests in orchestrator container
docker exec demo-sandbox_orchestrator_1 pytest tests/workflow_v2/test_integration.py -v
docker exec demo-sandbox_orchestrator_1 pytest tests/workflow_v2/test_api_integration.py -v
```

### Option 2: Manual Testing

We've already completed real-world integration testing:

1. **sqli-analysis workflow** - Tested on 172.31.2.137
   - Single-node workflow execution
   - Agent autonomy
   - Tool usage (nikto, sqlmap)
   - Report generation

2. **linear-analysis workflow** - Tested with Linear webhook trigger
   - Webhook integration
   - V2 workflow detection
   - Agent session handling
   - Linear API integration

## Test Coverage

- **Unit Tests:** 15 tests covering validation and executor logic
- **Integration Tests:** 16 tests covering end-to-end scenarios
- **Real-World Testing:** 2 production workflows tested successfully

## Why Integration Tests Are Skipped in CI/CD

Integration tests require:
- Full config files (`/configs/*.yaml`)
- Running MCP servers (agent, file_tools, linear, kali, etc.)
- Agent definitions in correct locations
- Docker socket access for dynamic MCPs
- Environment variables for API keys

CI/CD environment doesn't have these dependencies, so tests are marked to skip.

## Test Scenarios Covered

### Unit Tests
- Empty workflow validation
- Duplicate node IDs
- Invalid edges
- Self-loops
- Cycle detection
- Disconnected graphs
- Serial DAG execution
- Parallel DAG execution
- Single node execution
- Node failure handling
- Convergence logic

### Integration Tests
- Single-node workflow
- Serial workflow (A → B)
- Parallel workflow (A → [B, C] → D)
- Timeout handling
- Validation errors
- Non-existent agents
- CRUD operations (create, read, update, delete)
- Workflow execution via API
- Error responses
