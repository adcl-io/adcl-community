# PRD-61: Workflow UI Improvements - Test Plan

**Issue:** PRD-61 - Update Workflow UI - Planning & Implementation  
**Created:** 2025-11-03  
**Status:** Planning Phase

---

## Overview

This document outlines the comprehensive testing strategy for all three phases of the workflow UI improvements. Each phase includes unit tests, integration tests, and manual testing procedures.

---

## Testing Principles

1. **Test-Driven Development (TDD):** Write tests before implementation where possible
2. **Coverage Target:** Minimum 80% code coverage for new code
3. **Automated Testing:** All tests must be automated and run in CI/CD
4. **Manual Testing:** Critical user flows tested manually before release
5. **Regression Testing:** Ensure existing functionality still works

---

## Test Environment Setup

### Tools & Frameworks

```json
{
  "vitest": "^1.0.0",           // Unit testing framework
  "@testing-library/react": "^14.0.0",  // React component testing
  "@testing-library/user-event": "^14.0.0",  // User interaction simulation
  "@testing-library/jest-dom": "^6.0.0",  // DOM matchers
  "msw": "^2.0.0",              // API mocking
  "playwright": "^1.40.0"       // E2E testing (Phase 3)
}
```

### Test File Structure

```
frontend/src/
├── components/
│   └── workflow/
│       ├── __tests__/
│       │   ├── NodePalette.test.jsx
│       │   ├── WorkflowCanvas.test.jsx
│       │   ├── NodeConfigModal.test.jsx
│       │   └── ExecutionPanel.test.jsx
│       └── ...
├── hooks/
│   └── __tests__/
│       ├── useWorkflow.test.js
│       ├── useExecution.test.js
│       └── useMCPRegistry.test.js
└── utils/
    └── __tests__/
        ├── workflowValidation.test.js
        ├── workflowStorage.test.js
        └── expressionParser.test.js
```

---

## Phase 1: Quick Wins - Test Plan (2 weeks)

### 1.1 Drag-and-Drop Node Creation

#### Unit Tests

**File:** `frontend/src/components/workflow/__tests__/NodePalette.test.jsx`

```javascript
import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import NodePalette from '../NodePalette';

describe('NodePalette - Drag and Drop', () => {
  const mockServers = [
    {
      name: 'agent',
      tools: [
        { name: 'think', description: 'Reasoning tool' }
      ]
    }
  ];

  test('renders draggable node items', () => {
    render(<NodePalette servers={mockServers} />);
    const nodeItem = screen.getByText(/think/i);
    expect(nodeItem).toHaveAttribute('draggable', 'true');
  });

  test('sets drag data on drag start', () => {
    const { container } = render(<NodePalette servers={mockServers} />);
    const nodeItem = container.querySelector('[draggable="true"]');
    
    const dataTransfer = {
      setData: vi.fn(),
      effectAllowed: ''
    };
    
    const dragEvent = new DragEvent('dragstart', { dataTransfer });
    nodeItem.dispatchEvent(dragEvent);
    
    expect(dataTransfer.setData).toHaveBeenCalledWith(
      'application/json',
      expect.stringContaining('agent')
    );
  });

  test('shows visual feedback during drag', () => {
    render(<NodePalette servers={mockServers} />);
    const nodeItem = screen.getByText(/think/i);
    
    // Simulate drag start
    fireEvent.dragStart(nodeItem);
    
    expect(nodeItem).toHaveClass('dragging');
  });
});
```

**File:** `frontend/src/components/workflow/__tests__/WorkflowCanvas.test.jsx`

```javascript
import { render, screen, fireEvent } from '@testing-library/react';
import { ReactFlowProvider } from 'reactflow';
import WorkflowCanvas from '../WorkflowCanvas';

describe('WorkflowCanvas - Drop Handling', () => {
  const mockOnNodesChange = vi.fn();
  const mockOnEdgesChange = vi.fn();
  const mockOnConnect = vi.fn();

  test('accepts drop and creates node at cursor position', () => {
    const { container } = render(
      <ReactFlowProvider>
        <WorkflowCanvas
          nodes={[]}
          edges={[]}
          onNodesChange={mockOnNodesChange}
          onEdgesChange={mockOnEdgesChange}
          onConnect={mockOnConnect}
        />
      </ReactFlowProvider>
    );

    const canvas = container.querySelector('.react-flow');
    
    const dropData = JSON.stringify({
      mcp_server: 'agent',
      tool: 'think'
    });
    
    const dataTransfer = {
      getData: vi.fn(() => dropData)
    };
    
    const dropEvent = new DragEvent('drop', {
      dataTransfer,
      clientX: 100,
      clientY: 200
    });
    
    fireEvent(canvas, dropEvent);
    
    expect(mockOnNodesChange).toHaveBeenCalled();
  });

  test('shows drop zone indicator on drag over', () => {
    const { container } = render(
      <ReactFlowProvider>
        <WorkflowCanvas nodes={[]} edges={[]} />
      </ReactFlowProvider>
    );

    const canvas = container.querySelector('.react-flow');
    fireEvent.dragOver(canvas);
    
    expect(canvas).toHaveClass('drop-zone-active');
  });
});
```

#### Integration Tests

```javascript
describe('Drag and Drop Integration', () => {
  test('complete drag-and-drop flow', async () => {
    const user = userEvent.setup();
    render(<WorkflowsPage />);
    
    // Find draggable node in palette
    const nodeItem = screen.getByText(/think/i);
    
    // Drag to canvas
    await user.pointer([
      { keys: '[MouseLeft>]', target: nodeItem },
      { coords: { x: 500, y: 300 } },
      { keys: '[/MouseLeft]' }
    ]);
    
    // Verify node created
    expect(screen.getByText(/agent.think/i)).toBeInTheDocument();
  });
});
```

#### Manual Test Cases

- [ ] Drag node from palette to canvas
- [ ] Node appears at cursor position
- [ ] Visual feedback during drag (ghost element)
- [ ] Drop zone indicator shows on canvas
- [ ] Invalid drop zones are rejected
- [ ] Multiple nodes can be added
- [ ] Undo/redo works with drag-and-drop

---

### 1.2 Inline Parameter Editing

#### Unit Tests

**File:** `frontend/src/components/workflow/__tests__/NodeConfigModal.test.jsx`

```javascript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import NodeConfigModal from '../NodeConfigModal';

describe('NodeConfigModal', () => {
  const mockNode = {
    id: 'node-1',
    data: {
      mcp_server: 'agent',
      tool: 'think',
      params: { prompt: 'Test prompt' }
    }
  };

  const mockToolSchema = {
    type: 'object',
    properties: {
      prompt: {
        type: 'string',
        description: 'Question or task'
      }
    },
    required: ['prompt']
  };

  test('renders modal with node configuration', () => {
    render(
      <NodeConfigModal
        node={mockNode}
        toolSchema={mockToolSchema}
        onSave={vi.fn()}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByText(/Configure Node/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/prompt/i)).toHaveValue('Test prompt');
  });

  test('validates required fields', async () => {
    const user = userEvent.setup();
    const mockOnSave = vi.fn();
    
    render(
      <NodeConfigModal
        node={mockNode}
        toolSchema={mockToolSchema}
        onSave={mockOnSave}
        onClose={vi.fn()}
      />
    );

    // Clear required field
    const promptInput = screen.getByLabelText(/prompt/i);
    await user.clear(promptInput);
    
    // Try to save
    const saveButton = screen.getByText(/Save/i);
    await user.click(saveButton);
    
    // Should show validation error
    expect(screen.getByText(/required/i)).toBeInTheDocument();
    expect(mockOnSave).not.toHaveBeenCalled();
  });

  test('saves valid configuration', async () => {
    const user = userEvent.setup();
    const mockOnSave = vi.fn();
    
    render(
      <NodeConfigModal
        node={mockNode}
        toolSchema={mockToolSchema}
        onSave={mockOnSave}
        onClose={vi.fn()}
      />
    );

    // Update field
    const promptInput = screen.getByLabelText(/prompt/i);
    await user.clear(promptInput);
    await user.type(promptInput, 'New prompt');
    
    // Save
    const saveButton = screen.getByText(/Save/i);
    await user.click(saveButton);
    
    expect(mockOnSave).toHaveBeenCalledWith({
      prompt: 'New prompt'
    });
  });

  test('supports parameter references', async () => {
    const user = userEvent.setup();
    
    render(
      <NodeConfigModal
        node={mockNode}
        toolSchema={mockToolSchema}
        onSave={vi.fn()}
        onClose={vi.fn()}
      />
    );

    const promptInput = screen.getByLabelText(/prompt/i);
    await user.type(promptInput, '${node-1.result}');
    
    // Should show reference indicator
    expect(screen.getByText(/reference/i)).toBeInTheDocument();
  });
});
```

**File:** `frontend/src/components/workflow/__tests__/MCPNode.test.jsx`

```javascript
describe('MCPNode - Configuration', () => {
  test('shows configure button', () => {
    const mockData = {
      label: 'agent.think',
      mcp_server: 'agent',
      tool: 'think',
      params: {}
    };

    render(<MCPNode data={mockData} />);
    expect(screen.getByTitle(/Configure/i)).toBeInTheDocument();
  });

  test('opens modal on double-click', async () => {
    const user = userEvent.setup();
    const mockData = {
      label: 'agent.think',
      mcp_server: 'agent',
      tool: 'think',
      params: {}
    };

    render(<MCPNode data={mockData} />);
    
    const node = screen.getByText(/agent.think/i);
    await user.dblClick(node);
    
    // Modal should open
    await waitFor(() => {
      expect(screen.getByText(/Configure Node/i)).toBeInTheDocument();
    });
  });

  test('shows parameter count badge', () => {
    const mockData = {
      label: 'agent.think',
      mcp_server: 'agent',
      tool: 'think',
      params: { prompt: 'test', context: 'test' }
    };

    render(<MCPNode data={mockData} />);
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  test('shows validation error indicator', () => {
    const mockData = {
      label: 'agent.think',
      mcp_server: 'agent',
      tool: 'think',
      params: {},
      validationError: 'Missing required field: prompt'
    };

    render(<MCPNode data={mockData} />);
    expect(screen.getByTitle(/validation error/i)).toBeInTheDocument();
  });
});
```

#### Integration Tests

```javascript
describe('Parameter Editing Integration', () => {
  test('edit node parameters and see changes', async () => {
    const user = userEvent.setup();
    render(<WorkflowsPage />);
    
    // Add node
    // ... (drag and drop)
    
    // Double-click to configure
    const node = screen.getByText(/agent.think/i);
    await user.dblClick(node);
    
    // Edit parameter
    const promptInput = screen.getByLabelText(/prompt/i);
    await user.type(promptInput, 'Test prompt');
    
    // Save
    await user.click(screen.getByText(/Save/i));
    
    // Verify parameter count badge updated
    expect(screen.getByText('1')).toBeInTheDocument();
  });
});
```

#### Manual Test Cases

- [ ] Double-click node opens configuration modal
- [ ] Form fields generated from tool schema
- [ ] Required fields show validation errors
- [ ] Parameter references (${node-id.field}) work
- [ ] Changes saved to node data
- [ ] Parameter count badge updates
- [ ] ESC key closes modal
- [ ] Click outside closes modal

---

### 1.3 Enhanced Execution Visualization

#### Unit Tests

**File:** `frontend/src/hooks/__tests__/useExecution.test.js`

```javascript
import { renderHook, act, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import useExecution from '../useExecution';

describe('useExecution', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('tracks execution start time', async () => {
    const { result } = renderHook(() => useExecution());
    
    const nodes = [{ id: 'node-1', data: {} }];
    const edges = [];
    
    act(() => {
      result.current.executeWorkflow(nodes, edges, vi.fn());
    });
    
    expect(result.current.executing).toBe(true);
    expect(result.current.executionStartTime).toBeDefined();
  });

  test('calculates progress percentage', async () => {
    const { result } = renderHook(() => useExecution());
    
    const nodes = [
      { id: 'node-1', data: {} },
      { id: 'node-2', data: {} },
      { id: 'node-3', data: {} }
    ];
    const edges = [
      { source: 'node-1', target: 'node-2' },
      { source: 'node-2', target: 'node-3' }
    ];
    
    act(() => {
      result.current.executeWorkflow(nodes, edges, vi.fn());
    });
    
    // Simulate node completion
    act(() => {
      result.current.updateNodeState('node-1', 'completed');
    });
    
    expect(result.current.progress).toBe(33); // 1/3 nodes completed
  });

  test('estimates remaining time', async () => {
    const { result } = renderHook(() => useExecution());
    
    const nodes = [
      { id: 'node-1', data: {} },
      { id: 'node-2', data: {} }
    ];
    const edges = [{ source: 'node-1', target: 'node-2' }];
    
    act(() => {
      result.current.executeWorkflow(nodes, edges, vi.fn());
    });
    
    // Advance time by 10 seconds
    act(() => {
      vi.advanceTimersByTime(10000);
    });
    
    // Complete first node
    act(() => {
      result.current.updateNodeState('node-1', 'completed');
    });
    
    // Should estimate ~10 seconds remaining (1 node left, 10s per node)
    expect(result.current.estimatedTimeRemaining).toBeCloseTo(10, 0);
  });
});
```

**File:** `frontend/src/components/workflow/__tests__/ExecutionPanel.test.jsx`

```javascript
describe('ExecutionPanel - Visualization', () => {
  test('shows progress bar', () => {
    render(
      <ExecutionPanel
        executing={true}
        progress={50}
        onExecute={vi.fn()}
      />
    );

    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveAttribute('aria-valuenow', '50');
  });

  test('displays current executing node', () => {
    render(
      <ExecutionPanel
        executing={true}
        currentNode="node-1"
        onExecute={vi.fn()}
      />
    );

    expect(screen.getByText(/Executing: node-1/i)).toBeInTheDocument();
  });

  test('shows estimated time remaining', () => {
    render(
      <ExecutionPanel
        executing={true}
        estimatedTimeRemaining={30}
        onExecute={vi.fn()}
      />
    );

    expect(screen.getByText(/30s remaining/i)).toBeInTheDocument();
  });

  test('cancel button stops execution', async () => {
    const user = userEvent.setup();
    const mockOnCancel = vi.fn();
    
    render(
      <ExecutionPanel
        executing={true}
        onCancel={mockOnCancel}
        onExecute={vi.fn()}
      />
    );

    await user.click(screen.getByText(/Cancel/i));
    expect(mockOnCancel).toHaveBeenCalled();
  });
});
```

#### Integration Tests

```javascript
describe('Execution Visualization Integration', () => {
  test('complete execution flow with visualization', async () => {
    const user = userEvent.setup();
    
    // Mock WebSocket
    const mockWS = setupMockWebSocket();
    
    render(<WorkflowsPage />);
    
    // Load example workflow
    await user.click(screen.getByText(/Load Example/i));
    
    // Execute
    await user.click(screen.getByText(/Execute/i));
    
    // Should show progress
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
    
    // Simulate node execution
    act(() => {
      mockWS.simulateMessage({
        type: 'node_state',
        data: { node_id: 'node-1', status: 'running' }
      });
    });
    
    // Node should show running status
    expect(screen.getByText(/node-1/i)).toHaveClass('status-running');
    
    // Complete execution
    act(() => {
      mockWS.simulateMessage({
        type: 'result',
        data: { status: 'success' }
      });
    });
    
    // Should show completion
    expect(screen.getByText(/Completed/i)).toBeInTheDocument();
  });
});
```

#### Manual Test Cases

- [ ] Progress bar shows during execution
- [ ] Current node highlighted
- [ ] Execution time displayed per node
- [ ] Estimated time remaining shown
- [ ] Cancel button stops execution
- [ ] Status badges on nodes (⏳ running, ✅ completed, ❌ error)
- [ ] Progress ring animation on running nodes
- [ ] Overall workflow progress accurate

---

### 1.4 Workflow Save/Load UI

#### Unit Tests

**File:** `frontend/src/utils/__tests__/workflowStorage.test.js`

```javascript
import { describe, test, expect, beforeEach } from 'vitest';
import {
  saveWorkflow,
  loadWorkflow,
  listWorkflows,
  deleteWorkflow
} from '../workflowStorage';

describe('workflowStorage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test('saves workflow to localStorage', () => {
    const workflow = {
      name: 'Test Workflow',
      nodes: [{ id: 'node-1' }],
      edges: []
    };

    const id = saveWorkflow(workflow);
    
    expect(id).toBeDefined();
    expect(localStorage.getItem(`workflow_${id}`)).toBeDefined();
  });

  test('loads workflow from localStorage', () => {
    const workflow = {
      name: 'Test Workflow',
      nodes: [{ id: 'node-1' }],
      edges: []
    };

    const id = saveWorkflow(workflow);
    const loaded = loadWorkflow(id);
    
    expect(loaded.name).toBe('Test Workflow');
    expect(loaded.nodes).toHaveLength(1);
  });

  test('lists all workflows', () => {
    saveWorkflow({ name: 'Workflow 1', nodes: [], edges: [] });
    saveWorkflow({ name: 'Workflow 2', nodes: [], edges: [] });
    
    const workflows = listWorkflows();
    
    expect(workflows).toHaveLength(2);
    expect(workflows[0].name).toBe('Workflow 1');
  });

  test('deletes workflow', () => {
    const id = saveWorkflow({ name: 'Test', nodes: [], edges: [] });
    
    deleteWorkflow(id);
    
    expect(loadWorkflow(id)).toBeNull();
  });

  test('handles invalid workflow ID', () => {
    expect(loadWorkflow('invalid-id')).toBeNull();
  });
});
```

**File:** `frontend/src/components/workflow/__tests__/WorkflowToolbar.test.jsx`

```javascript
describe('WorkflowToolbar - Save/Load', () => {
  test('save button opens name input', async () => {
    const user = userEvent.setup();
    render(<WorkflowToolbar onSave={vi.fn()} />);
    
    await user.click(screen.getByText(/Save/i));
    
    expect(screen.getByPlaceholderText(/Workflow name/i)).toBeInTheDocument();
  });

  test('saves workflow with name', async () => {
    const user = userEvent.setup();
    const mockOnSave = vi.fn();
    
    render(<WorkflowToolbar onSave={mockOnSave} />);
    
    await user.click(screen.getByText(/Save/i));
    await user.type(screen.getByPlaceholderText(/Workflow name/i), 'My Workflow');
    await user.click(screen.getByText(/Confirm/i));
    
    expect(mockOnSave).toHaveBeenCalledWith('My Workflow');
  });

  test('load dropdown shows saved workflows', async () => {
    const user = userEvent.setup();
    const mockWorkflows = [
      { id: '1', name: 'Workflow 1' },
      { id: '2', name: 'Workflow 2' }
    ];
    
    render(<WorkflowToolbar workflows={mockWorkflows} onLoad={vi.fn()} />);
    
    await user.click(screen.getByText(/Load/i));
    
    expect(screen.getByText('Workflow 1')).toBeInTheDocument();
    expect(screen.getByText('Workflow 2')).toBeInTheDocument();
  });

  test('export button downloads JSON', async () => {
    const user = userEvent.setup();
    const mockWorkflow = {
      name: 'Test',
      nodes: [],
      edges: []
    };
    
    // Mock URL.createObjectURL
    global.URL.createObjectURL = vi.fn(() => 'blob:test');
    
    render(<WorkflowToolbar workflow={mockWorkflow} />);
    
    await user.click(screen.getByText(/Export/i));
    
    expect(global.URL.createObjectURL).toHaveBeenCalled();
  });
});
```

#### Integration Tests

```javascript
describe('Workflow Save/Load Integration', () => {
  test('complete save and load flow', async () => {
    const user = userEvent.setup();
    render(<WorkflowsPage />);
    
    // Create workflow
    // ... (add nodes)
    
    // Save
    await user.click(screen.getByText(/Save/i));
    await user.type(screen.getByPlaceholderText(/name/i), 'Test Workflow');
    await user.click(screen.getByText(/Confirm/i));
    
    // Clear canvas
    await user.click(screen.getByText(/Clear/i));
    
    // Load
    await user.click(screen.getByText(/Load/i));
    await user.click(screen.getByText('Test Workflow'));
    
    // Workflow should be restored
    expect(screen.getByText(/agent.think/i)).toBeInTheDocument();
  });

  test('export and import workflow', async () => {
    const user = userEvent.setup();
    render(<WorkflowsPage />);
    
    // Create workflow
    // ... (add nodes)
    
    // Export
    await user.click(screen.getByText(/Export/i));
    
    // Get downloaded JSON
    const exportedJSON = getLastDownload();
    
    // Clear canvas
    await user.click(screen.getByText(/Clear/i));
    
    // Import
    const file = new File([exportedJSON], 'workflow.json', { type: 'application/json' });
    const input = screen.getByLabelText(/Import/i);
    await user.upload(input, file);
    
    // Workflow should be restored
    expect(screen.getByText(/agent.think/i)).toBeInTheDocument();
  });
});
```

#### Manual Test Cases

- [ ] Save workflow with name
- [ ] Saved workflows appear in load dropdown
- [ ] Load workflow restores nodes and edges
- [ ] Export downloads JSON file
- [ ] Import loads JSON file
- [ ] Workflows persist across page refresh
- [ ] Delete workflow removes from list
- [ ] Duplicate names handled gracefully

---

### 1.5 Shadcn/Tailwind Migration

#### Unit Tests

**File:** `frontend/src/components/workflow/__tests__/theming.test.jsx`

```javascript
describe('Theming Support', () => {
  test('components use Shadcn classes', () => {
    render(<NodeConfigModal node={mockNode} />);
    
    const modal = screen.getByRole('dialog');
    expect(modal).toHaveClass('bg-background', 'text-foreground');
  });

  test('supports dark mode', () => {
    render(
      <ThemeProvider defaultTheme="dark">
        <WorkflowsPage />
      </ThemeProvider>
    );
    
    const container = screen.getByTestId('workflows-page');
    expect(container).toHaveClass('dark');
  });

  test('theme toggle works', async () => {
    const user = userEvent.setup();
    render(
      <ThemeProvider>
        <WorkflowsPage />
      </ThemeProvider>
    );
    
    const themeToggle = screen.getByRole('button', { name: /theme/i });
    await user.click(themeToggle);
    
    // Should toggle theme
    expect(document.documentElement).toHaveClass('dark');
  });
});
```

#### Manual Test Cases

- [ ] All components use Shadcn/Tailwind classes
- [ ] Light theme displays correctly
- [ ] Dark theme displays correctly
- [ ] Theme toggle works
- [ ] Colors consistent with rest of UI
- [ ] Spacing follows 8px grid
- [ ] Typography matches design system
- [ ] Hover states work
- [ ] Focus indicators visible

---

## Phase 1 Test Summary

### Coverage Requirements

- **Unit Tests:** 80% coverage minimum
- **Integration Tests:** All critical user flows
- **Manual Tests:** All acceptance criteria

### Test Execution

```bash
# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run specific test file
npm test NodePalette.test.jsx

# Run in watch mode
npm test -- --watch
```

### CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm ci
      - run: npm test -- --coverage
      - uses: codecov/codecov-action@v3
```

---

## Phase 2 & Phase 3 Test Plans

*(Detailed test plans for Phase 2 and Phase 3 will be added in separate sections)*

---

**Document Version:** 1.0  
**Last Updated:** 2025-11-03  
**Next Review:** After Phase 1 completion
