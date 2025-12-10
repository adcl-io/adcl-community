# ADCL E2E Tests

End-to-end tests for the ADCL Platform that test the complete workflow from playground UI through backend execution.

## What This Tests

1. **Team Selection** - Can fetch and select teams via API
2. **Team Execution** - Can execute multi-agent teams
3. **Status Polling** - Can track execution progress
4. **KPI Collection** - Captures critical performance metrics

## KPIs Tracked

### Performance Metrics
- **Execution Time**: Total time to complete team execution (seconds)
- **Tokens Per Second**: Throughput (tokens/sec)

### Cost Metrics
- **Total Cost**: Total API costs in USD
- **Cost Per 1K Tokens**: Cost efficiency ($/1K tokens)
- **Total Tokens**: Input + output tokens combined

### Quality Metrics
- **Success Rate**: Percentage of agents that completed successfully
- **Successful Agents**: Count of agents that completed
- **Failed Agents**: Count of agents that errored

### Execution Metrics
- **Agent Count**: Number of agents in the team
- **Total Iterations**: Sum of iterations across all agents
- **Tools Used**: Count of tool calls across execution

## Quick Start

**No local Python installation required!** Tests run inside Docker containers.

### 1. Ensure ADCL is Running

```bash
# Start the platform
docker-compose up -d

# Verify it's running
docker-compose ps
```

### 2. Run Tests (Containerized)

```bash
# Run all test scenarios (uses container)
./run-e2e-tests.sh

# Run a specific team
./run-e2e-tests.sh --team "test-security-team" \
  --task "Analyze the security of a REST API" \
  --timeout 180
```

### Alternative: Run Directly in Container

```bash
# Run tests inside orchestrator container
docker-compose exec orchestrator python /app/tests/e2e/run_e2e_tests.py

# Run with pytest
docker-compose exec orchestrator pytest /app/tests/e2e/test_playground_team.py -v
```

## Test Scenarios

### Default Scenarios

1. **Quick Security Test**
   - Team: `test-security-team`
   - Task: Analyze login endpoint security
   - Timeout: 180s

2. **Code Review Test**
   - Team: `code-review-team`
   - Task: Review Python function
   - Timeout: 120s

### Custom Scenarios

Add your own scenarios in `run_e2e_tests.py`:

```python
TEST_SCENARIOS = [
    {
        "name": "HR Recruitment Test",
        "team": "hr-recruitment-team",
        "task": "Review this resume and provide coaching on LinkedIn messaging",
        "timeout": 300,
    },
]
```

## Test Results

### Console Output

Tests print a formatted summary to console:

```
================================================================================
ADCL E2E Test Results
================================================================================

Test #1: team_test-security-team ✅
  Team: test-security-team
  Status: completed
  Duration: 45.23s

  KPIs:
    • Execution Time: 43.5s
    • Total Cost: $0.1234
    • Total Tokens: 12,456 (8,234 in / 4,222 out)
    • Agents: 3 total
    • Success Rate: 100% (3 succeeded)
    • Total Iterations: 15
    • Tools Used: 8
    • Throughput: 286.3 tokens/sec
    • Cost Efficiency: $0.0099 per 1K tokens

--------------------------------------------------------------------------------
Summary
--------------------------------------------------------------------------------
  Total Execution Time: 43.5s
  Total Cost: $0.1234
  Total Tokens: 12,456
  Average Success Rate: 100%
  Total Agents Tested: 3
================================================================================
```

### JSON Reports

Detailed reports saved to `tests/e2e/results/`:

```json
{
  "test_suite": "Playground Team E2E Tests",
  "timestamp": "2025-12-09T12:00:00",
  "total_tests": 2,
  "passed": 2,
  "failed": 0,
  "tests": [...],
  "summary_kpis": {
    "total_execution_time": 85.4,
    "total_cost": 0.2456,
    "total_tokens": 24567,
    "avg_success_rate": 100,
    "total_agents_tested": 6
  }
}
```

## CI/CD Integration

Tests run inside containers - no Python installation needed in CI!

### GitHub Actions

```yaml
- name: Run E2E Tests
  run: |
    docker-compose up -d
    sleep 15  # Wait for services to be ready
    ./run-e2e-tests.sh
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

- name: Upload Test Results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: e2e-test-results
    path: tests/e2e/results/
```

### GitLab CI

```yaml
e2e_tests:
  image: docker/compose:latest
  services:
    - docker:dind
  script:
    - docker-compose up -d
    - sleep 15
    - ./run-e2e-tests.sh
  artifacts:
    paths:
      - tests/e2e/results/
    when: always
    expire_in: 30 days
```

## Troubleshooting

### Tests Timeout

- Increase `--timeout` parameter
- Check backend logs: `docker-compose logs backend`
- Verify API keys are configured

### API Connection Refused

- Ensure services are running: `docker-compose ps`
- Check URLs match your setup
- Verify firewall/network settings

### Team Not Found

- List available teams: `curl http://localhost:8000/api/teams`
- Create team in `agent-teams/` directory
- Restart backend to load new team

## Development

### Adding New Tests

1. Edit `TEST_SCENARIOS` in `run_e2e_tests.py`
2. Or use the `test_playground_team.py` module directly:

```python
from test_playground_team import PlaygroundTeamTest

tester = PlaygroundTeamTest()
result = await tester.test_team_execution(
    team_name="my-team",
    task="My task",
    timeout_seconds=300
)
tester.print_summary()
```

### Extending KPIs

Add custom KPI collection in `_collect_kpis()` method:

```python
async def _collect_kpis(self, session_id, execution_time):
    kpis = await super()._collect_kpis(session_id, execution_time)

    # Add custom KPI
    kpis["custom_metric"] = await self._calculate_custom_metric()

    return kpis
```

## Architecture

```
tests/e2e/
├── test_playground_team.py    # Core test class
├── run_e2e_tests.py            # Test runner with scenarios
├── results/                    # JSON test reports
│   └── e2e_report_*.json
└── README.md                   # This file
```

The test flow:
1. **Fetch Teams** → GET `/api/teams`
2. **Execute Team** → POST `/api/teams/{id}/execute`
3. **Poll Status** → GET `/api/playground/status/{session_id}` (every 2s)
4. **Collect KPIs** → Extract metrics from final status
5. **Generate Report** → Save JSON + print summary
