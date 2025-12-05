# PRD-45: Memory UI Cleanup - Unit Test Plan

**Issue**: PRD-45 - Cleanup the Memory UI
**Branch**: `prd-45`
**Status**: Planning

## Test Strategy

All UI changes will be tested using React Testing Library and Vitest. Tests will verify component rendering, user interactions, and state management.

## Test Files to Create/Modify

### 1. HistoryPage Tests
**File**: `frontend/src/pages/__tests__/HistoryPage.test.jsx` (new)

**Test Cases**:
- [ ] Renders history page with title and description
- [ ] Displays "No conversations found" when sessions array is empty
- [ ] Renders list of conversations when sessions exist
- [ ] Filters conversations based on search input
- [ ] Calls loadSession and navigates to playground when conversation clicked
- [ ] Refresh button calls loadSessions
- [ ] Displays correct message count and date for each session
- [ ] Shows session status badge

### 2. PlaygroundPage Tests
**File**: `frontend/src/pages/__tests__/PlaygroundPage.test.jsx` (new/modify)

**Test Cases**:
- [ ] Renders without history sidebar
- [ ] Displays team selector in header (top right)
- [ ] Team selector shows current team name
- [ ] Message count badge displays in header
- [ ] New chat button creates new conversation
- [ ] Team selector modal opens on click
- [ ] Selecting team updates selectedTeam state
- [ ] Full-width chat area renders correctly
- [ ] Messages display without sidebar interference

### 3. Navigation Tests
**File**: `frontend/src/components/__tests__/Navigation.test.jsx` (new/modify)

**Test Cases**:
- [ ] Renders all navigation items
- [ ] Playground item has expandable submenu
- [ ] Submenu displays 10 most recent conversations
- [ ] "View All History" link navigates to history page
- [ ] Clicking recent conversation loads it and navigates to playground
- [ ] Submenu collapses/expands on click
- [ ] Active page highlighted correctly
- [ ] History page navigation item works

### 4. useConversationHistory Hook Tests
**File**: `frontend/src/hooks/__tests__/useConversationHistory.test.js` (new/modify)

**Test Cases**:
- [ ] loadSessions fetches and sets sessions
- [ ] loadSession loads messages for specific session
- [ ] createSession creates new session and returns ID
- [ ] appendMessage adds message to current session
- [ ] startNewConversation creates session and clears messages
- [ ] Falls back to localStorage when API fails
- [ ] Persists active session ID to localStorage

## Test Setup

### Dependencies
```json
{
  "devDependencies": {
    "@testing-library/react": "^14.0.0",
    "@testing-library/jest-dom": "^6.1.0",
    "@testing-library/user-event": "^14.5.0",
    "vitest": "^1.0.0",
    "@vitest/ui": "^1.0.0",
    "jsdom": "^23.0.0"
  }
}
```

### Vitest Configuration
**File**: `frontend/vitest.config.js` (new)

```javascript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: ['node_modules/', 'src/test/']
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  }
});
```

### Test Setup File
**File**: `frontend/src/test/setup.js` (new)

```javascript
import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

afterEach(() => {
  cleanup();
});
```

## GitHub Workflow

**File**: `.github/workflows/frontend-tests.yml` (new)

```yaml
name: Frontend Tests

on:
  push:
    branches: ['**']
    paths:
      - 'frontend/**'
      - '.github/workflows/frontend-tests.yml'
  pull_request:
    branches: [main]
    paths:
      - 'frontend/**'

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        working-directory: frontend
        run: npm ci
      
      - name: Run tests
        working-directory: frontend
        run: npm test -- --run
      
      - name: Generate coverage report
        working-directory: frontend
        run: npm test -- --coverage --run
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./frontend/coverage/coverage-final.json
          flags: frontend
          fail_ci_if_error: false
```

## Mock Data

### Mock Sessions
```javascript
export const mockSessions = [
  {
    id: 'session-1',
    title: 'Test Conversation 1',
    message_count: 5,
    created_at: '2025-11-01T10:00:00Z',
    status: 'active'
  },
  {
    id: 'session-2',
    title: 'Test Conversation 2',
    message_count: 3,
    created_at: '2025-11-01T09:00:00Z',
    status: 'active'
  }
];
```

### Mock Messages
```javascript
export const mockMessages = [
  {
    id: 1,
    role: 'user',
    content: 'Hello',
    timestamp: '2025-11-01T10:00:00Z'
  },
  {
    id: 2,
    role: 'assistant',
    content: 'Hi there!',
    timestamp: '2025-11-01T10:00:05Z'
  }
];
```

## Test Execution

### Local Testing
```bash
# Run all tests
cd frontend
npm test

# Run tests in watch mode
npm test -- --watch

# Run with coverage
npm test -- --coverage

# Run specific test file
npm test HistoryPage.test.jsx
```

### CI/CD Testing
- Tests run automatically on every push
- Tests run on all pull requests
- Coverage reports uploaded to Codecov
- Workflow fails if tests fail

## Coverage Goals

- **Overall Coverage**: 80%+
- **New Components**: 90%+
  - HistoryPage: 90%+
  - Navigation submenu: 90%+
  - PlaygroundPage modifications: 85%+

## Implementation Order

1. **Setup test infrastructure**
   - Install dependencies
   - Create vitest.config.js
   - Create test setup file
   - Add test scripts to package.json

2. **Create mock data and utilities**
   - Mock sessions
   - Mock messages
   - Mock API responses

3. **Write component tests**
   - HistoryPage tests
   - Navigation tests
   - PlaygroundPage tests

4. **Write hook tests**
   - useConversationHistory tests

5. **Create GitHub workflow**
   - Add frontend-tests.yml
   - Test workflow locally with act (optional)
   - Push and verify workflow runs

6. **Verify coverage**
   - Check coverage reports
   - Add missing tests
   - Update documentation

## Success Criteria

- [ ] All test files created
- [ ] Test coverage meets goals (80%+ overall)
- [ ] GitHub workflow created and passing
- [ ] Tests run on every push
- [ ] Coverage reports generated
- [ ] No failing tests
- [ ] Documentation updated

## Notes

- Use `data-testid` attributes for complex selectors
- Mock axios calls using vitest.mock()
- Mock localStorage for persistence tests
- Test both success and error scenarios
- Test loading states
- Test empty states
