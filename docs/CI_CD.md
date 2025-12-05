# CI/CD Documentation

## Overview

The ADCL platform uses GitHub Actions for continuous integration and testing. All code changes are automatically tested to ensure quality and prevent regressions.

---

## GitHub Actions Workflows

### 1. Test Suite (`.github/workflows/test.yml`)

**Triggers:**
- Every push to any branch
- Pull requests to `main`
- Manual trigger via GitHub UI

**Jobs:**

#### **Unit Tests** (~2 minutes)
- Runs TriggerManager unit tests (19 tests)
- Runs webhook signature security tests (13 tests)
- Uses Python 3.12
- Caches pip dependencies for speed
- Fails fast on any test failure

#### **Integration Tests** (~10 minutes)
- Runs trigger system integration tests (20 tests)
- Uses real Docker containers
- Tests end-to-end workflows
- Skips slow tests (marked with `@pytest.mark.slow`)
- Auto-cleanup of Docker containers

#### **All Tests Summary** (runs after both)
- Combines all test results
- Generates comprehensive summary
- Shows test counts and categories

#### **Test Status Check**
- Final gate for PR merging
- Fails if any test job failed
- Shows clear pass/fail status

**Example Output:**
```
📊 Test Suite Summary

Test Execution
- Unit Tests: 37 passing
- Integration Tests: 20 passing
- Total: 57 tests passing

Test Categories
- Unit Tests: DockerManager/Triggers (19 tests) + Webhook Signatures (18 tests)
- Integration Tests: Trigger system end-to-end (20 tests)
- Total: 57 tests

Note: Slow tests (marked with @pytest.mark.slow) are skipped in CI
```

---

### 2. License Header Check (`.github/workflows/license-check.yml`)

**Triggers:**
- Push to any branch
- Pull requests to `main`

**Jobs:**
- Checks all source files for copyright headers
- Auto-fixes missing headers on PRs
- Commits fixes with `[skip ci]` flag

---

## Local Testing

### Run All Tests Locally

```bash
# Activate virtual environment
source venv/bin/activate

# Set Python path (backend for app code, root for triggers module)
export PYTHONPATH=backend:$(pwd)

# Run unit tests only
pytest tests/test_trigger_manager.py tests/test_webhook_signatures.py -v

# Run integration tests only
pytest tests/test_trigger_integration.py -v -m "not slow"

# Run all tests (including slow tests)
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=backend/app --cov-report=html
```

### Run Tests Matching CI Exactly

```bash
# Simulate CI environment
docker run --rm -it \
  -v $(pwd):/workspace \
  -w /workspace \
  python:3.12 \
  bash -c "
    pip install pytest pytest-asyncio httpx docker && \
    pip install -r backend/requirements.txt && \
    export PYTHONPATH=backend:/workspace && \
    pytest tests/test_trigger_manager.py tests/test_webhook_signatures.py tests/test_trigger_integration.py -v -m 'not slow'
  "
```

---

## Test Configuration

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
markers =
    asyncio: mark test as async
    slow: mark test as slow (takes >60 seconds)
```

### Test Markers

**`@pytest.mark.asyncio`** - Async test
**`@pytest.mark.slow`** - Skipped in CI (takes >60s)

---

## Adding New Tests

### 1. Create Test File

```python
# tests/test_new_feature.py
import pytest

class TestNewFeature:
    """Test suite for new feature"""

    def test_basic_functionality(self):
        """Test basic feature works"""
        assert True

    @pytest.mark.asyncio
    async def test_async_functionality(self):
        """Test async feature works"""
        result = await async_function()
        assert result is not None

    @pytest.mark.slow
    def test_slow_operation(self):
        """This test takes >60s, skipped in CI"""
        # Long-running test
        pass
```

### 2. Run Locally First

```bash
pytest tests/test_new_feature.py -v
```

### 3. Commit and Push

```bash
git add tests/test_new_feature.py
git commit -m "test: Add tests for new feature"
git push
```

GitHub Actions will automatically run your tests!

---

## Viewing Test Results

### On GitHub

1. **Go to Actions tab** in repository
2. **Select workflow run** to see details
3. **Click on job** to see test output
4. **Check summary** at bottom of workflow run

### In Pull Request

- ✅ **Green checkmark** = All tests passed
- ❌ **Red X** = Some tests failed
- 🟡 **Yellow dot** = Tests running
- Click "Details" to see which tests failed

---

## Troubleshooting CI Failures

### Unit Test Failures

**Symptoms:** `unit-tests` job fails

**Common Causes:**
- Import errors (missing dependencies)
- API changes not reflected in tests
- Environment variable issues

**Fix:**
```bash
# Run locally to reproduce
export PYTHONPATH=backend:$(pwd)
pytest tests/test_trigger_manager.py tests/test_webhook_signatures.py -v
```

### Integration Test Failures

**Symptoms:** `integration-tests` job fails

**Common Causes:**
- Docker build failures
- Container cleanup issues
- Network connectivity problems
- File permission errors

**Fix:**
```bash
# Run locally with Docker
export PYTHONPATH=backend:$(pwd)
pytest tests/test_trigger_integration.py -v

# Clean up containers
docker ps -a --filter "name=trigger-" --format "{{.Names}}" | xargs docker rm -f
```

### Timeout Issues

**Symptoms:** Job times out after 20 minutes

**Common Causes:**
- Infinite loops
- Deadlocks
- Container startup hangs

**Fix:**
```bash
# Add timeout to specific test
@pytest.mark.timeout(30)
def test_with_timeout(self):
    pass
```

### Flaky Tests

**Symptoms:** Tests pass locally but fail in CI randomly

**Common Causes:**
- Race conditions
- Timing dependencies
- Shared state between tests

**Fix:**
```python
# Add retry decorator
@pytest.mark.flaky(reruns=3)
def test_flaky(self):
    pass

# Or increase wait times
await asyncio.sleep(5)  # Instead of sleep(2)
```

---

## Best Practices

### ✅ DO

- **Run tests locally** before pushing
- **Keep tests fast** (<5 seconds per test)
- **Use markers** for slow/integration tests
- **Clean up resources** in fixtures
- **Write descriptive test names**
- **Test edge cases** and error conditions

### ❌ DON'T

- **Commit failing tests** to main
- **Skip tests** without good reason
- **Leave containers running** after tests
- **Use hardcoded paths** or ports
- **Test external APIs** without mocks
- **Write tests dependent on order**

---

## Performance Optimization

### Caching

GitHub Actions caches:
- Python packages (pip cache)
- Docker layers (buildx cache)

This reduces test time by ~30%.

### Parallel Execution

Tests run in parallel jobs:
- Unit tests: ~2 minutes
- Integration tests: ~10 minutes
- Total: ~12 minutes (not 12 minutes sequentially)

### Skipping Slow Tests

Tests marked with `@pytest.mark.slow` are skipped in CI:

```python
@pytest.mark.slow
def test_schedule_trigger_executes_on_time(self):
    """This takes 70+ seconds, skip in CI"""
    pytest.skip("Slow test")
```

---

## Monitoring & Alerts

### GitHub Actions Badge

Add to README.md:

```markdown
![Tests](https://github.com/adcl-io/demo-sandbox/workflows/Test%20Suite/badge.svg)
```

### Notifications

Configure in repository settings:
- Email on test failures
- Slack integration
- Discord webhooks

---

## Maintenance

### Updating Dependencies

```bash
# Update requirements
pip freeze > backend/requirements.txt

# Test locally
pytest tests/ -v

# Commit and push
git add backend/requirements.txt
git commit -m "chore: Update dependencies"
git push
```

### Updating Python Version

Edit `.github/workflows/test.yml`:

```yaml
- name: Set up Python 3.13
  uses: actions/setup-python@v5
  with:
    python-version: '3.13'
```

---

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [Docker in GitHub Actions](https://docs.github.com/en/actions/using-containerized-services/about-service-containers)

---

**Last Updated:** 2025-10-26
**Workflow Version:** 1.0.0
