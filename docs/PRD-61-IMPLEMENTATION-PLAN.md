# PRD-61: Workflow UI Improvements - Implementation Plan

**Issue:** PRD-61 - Update Workflow UI - Planning & Implementation  
**Approach:** Option 5 - Hybrid Approach (Phased Delivery)  
**Total Timeline:** 8 weeks (updated to include Phase 4: Registry Integration)  
**Created:** 2025-11-03  
**Updated:** 2025-11-04  
**Status:** Planning Phase

---

## Executive Summary

This document outlines a three-phase approach to improving the MCP Agent Platform's workflow UI. The plan balances quick wins with strategic improvements, delivering value incrementally while building toward a professional n8n-style interface.

**Key Goals:**
1. Improve workflow creation UX (drag-and-drop, inline editing)
2. Enhance execution visualization (real-time feedback, progress tracking)
3. Better results display (custom renderers, export options)
4. Professional workflow management (save/load, templates)

**Success Metrics:**
- Reduced time to create workflows (target: 50% faster)
- Improved execution visibility (real-time status updates)
- Better error handling and validation feedback
- User satisfaction with workflow builder

---

## Phase 1: Quick Wins (2 weeks)

**Goal:** Deliver immediate value with Shadcn/Tailwind migration and minimal architectural changes

**Tasks:**
- 1.0: Shadcn/Tailwind Migration (3 days)
- 1.1: Drag-and-Drop (2 days)
- 1.2: Inline Editing (3 days)
- 1.3: Execution Visualization (2 days)
- 1.4: Save/Load UI + Backend (3 days)
- Testing/Polish (1 day)

**Total:** 14 days = 2 weeks

---

### 1.0 Shadcn/Tailwind Migration

**Current State:**
- Custom CSS files with hardcoded colors
- No theme support
- Inconsistent with rest of UI

**Implementation:**

**Frontend Changes:**
```
frontend/src/pages/WorkflowsPage.css (DELETE)
- Remove custom CSS file

frontend/src/pages/WorkflowsPage.jsx
- Convert to Shadcn UI components
- Use Tailwind utility classes
- Add theme support via ThemeProvider

frontend/src/components/workflow/*.jsx
- Convert all components to Shadcn primitives
- Use Card, Button, Badge, Dialog, etc.
- Replace custom styles with Tailwind classes
```

**Shadcn Components Used:**
- Card, CardHeader, CardTitle, CardContent
- Button (all variants)
- Badge (status indicators)
- Dialog (modals)
- Input, Textarea, Label (forms)
- DropdownMenu (dropdowns)
- ScrollArea (scrollable areas)
- Alert (notifications)
- Progress (progress bars)

**Acceptance Criteria:**
- ✅ All components use Shadcn UI primitives
- ✅ No custom CSS files remain
- ✅ Theme support (light/dark) works
- ✅ Consistent with rest of platform
- ✅ Proper focus indicators and hover states

**Estimated Time:** 3 days

---

### 1.1 Drag-and-Drop Node Creation

**Current State:**
- Nodes added via `addNode()` with random positioning
- No visual feedback during node creation
- Manual positioning required

**Implementation:**

**Frontend Changes:**
```
frontend/src/components/workflow/NodePalette.jsx
- Add draggable attribute to node items
- Implement onDragStart handler with node data
- Add visual drag feedback (ghost element)

frontend/src/components/workflow/WorkflowCanvas.jsx
- Add onDrop handler to ReactFlow
- Calculate drop position from event coordinates
- Call addNode with calculated position
- Add drop zone visual indicator

frontend/src/hooks/useWorkflow.js
- Update addNode to accept position parameter
- Add validation for node placement
```

**Acceptance Criteria:**
- ✅ User can drag node from palette to canvas
- ✅ Node appears at cursor position on drop
- ✅ Visual feedback during drag operation
- ✅ Invalid drop zones are indicated

**Estimated Time:** 2 days

---

### 1.2 Inline Parameter Editing

**Dependencies:** Task 1.0 (Shadcn migration must be complete)

**Current State:**
- No UI for editing node parameters
- Must edit workflow JSON manually
- No validation feedback

**Implementation:**

**Frontend Changes:**
```
frontend/src/components/workflow/NodeConfigModal.jsx (NEW)
- Modal dialog for node configuration
- Dynamic form generation based on tool schema
- Parameter validation with error messages
- Support for ${node-id.field} references

frontend/src/components/workflow/MCPNode.jsx
- Add "Configure" button to node
- Open NodeConfigModal on click
- Display parameter count badge
- Show validation errors on node

frontend/src/hooks/useWorkflow.js
- Add updateNodeParams method
- Add validateNodeParams method
```

**Acceptance Criteria:**
- ✅ Double-click node opens configuration modal
- ✅ Form fields generated from tool schema
- ✅ Parameter validation with error messages
- ✅ Changes saved to node data
- ✅ Parameter references autocomplete

**Estimated Time:** 3 days

---

### 1.3 Enhanced Execution Visualization

**Current State:**
- Basic status updates (idle, running, completed, error)
- No progress indicators
- Limited visual feedback

**Implementation:**

**Frontend Changes:**
```
frontend/src/components/workflow/MCPNode.jsx
- Add status badge with icon (⏳ running, ✅ completed, ❌ error)
- Add progress ring animation for running nodes
- Add execution time display
- Color-code node border by status

frontend/src/components/workflow/ExecutionPanel.jsx
- Add progress bar for overall workflow
- Display current executing node
- Show estimated time remaining
- Add pause/cancel buttons

frontend/src/hooks/useExecution.js
- Track execution start time per node
- Calculate progress percentage
- Estimate remaining time based on history
```

**Acceptance Criteria:**
- ✅ Nodes show clear status indicators
- ✅ Running nodes have animated progress ring
- ✅ Overall progress bar shows workflow completion
- ✅ Execution time displayed per node
- ✅ Can cancel running workflow

**Estimated Time:** 2 days

---

### 1.4 Workflow Save/Load UI

**Current State:**
- Can load examples via API
- No save functionality
- No workflow management

**Implementation:**

**Frontend Changes:**
```
frontend/src/components/workflow/WorkflowToolbar.jsx
- Add "Save" button with name input
- Add "Load" dropdown with saved workflows
- Add "Export JSON" button
- Add "Import JSON" file upload

frontend/src/hooks/useWorkflow.js
- Add saveWorkflow method (localStorage)
- Add loadWorkflow method
- Add exportWorkflow method (download JSON)
- Add importWorkflow method (parse uploaded file)

frontend/src/utils/workflowStorage.js (NEW)
- LocalStorage wrapper for workflows
- Workflow metadata (name, created, modified)
- List saved workflows
```

**Backend Changes (Required - No Hidden State):**
```
backend/app/main.py
- Add POST /workflows endpoint (save workflow)
- Add GET /workflows endpoint (list workflows)
- Add GET /workflows/{id} endpoint (load workflow)
- Add PUT /workflows/{id} endpoint (update workflow)
- Add DELETE /workflows/{id} endpoint (delete workflow)

backend/app/main.py (models)
- Add WorkflowSaveRequest model

workflows/user/ (NEW DIRECTORY)
- File-based storage for user workflows
- One JSON file per workflow
```

**Note:** Backend endpoints are **required** to maintain the platform's "no hidden state" principle. All workflow data must be stored server-side, not in localStorage.

**See:** `docs/PRD-61-API-CONTRACT.md` for complete API specification.

**Acceptance Criteria:**
- ✅ User can save workflow with name
- ✅ Saved workflows appear in load dropdown
- ✅ Can export workflow as JSON file
- ✅ Can import workflow from JSON file
- ✅ Workflows persist server-side (no localStorage)
- ✅ All workflow data visible and auditable

**Estimated Time:** 3 days (2 days frontend + 1 day backend)
- ✅ Workflows persist across sessions

**Estimated Time:** 3 days

---

## Phase 2: Strategic Improvements (3 weeks)

**Goal:** Build professional n8n-style interface with better UX

### 2.1 Side Panel for Node Configuration

**Current State:**
- Modal dialog for configuration
- Blocks workflow view
- Limited space for complex parameters

**Implementation:**

**Frontend Changes:**
```
frontend/src/components/workflow/NodeConfigPanel.jsx (NEW)
- Slide-out panel from right side
- Tabbed interface (Parameters, Settings, Info)
- Resizable panel width
- Sticky header with node name
- Close button and keyboard shortcuts

frontend/src/pages/WorkflowsPage.jsx
- Update layout to accommodate side panel
- Add panel state management
- Handle panel open/close transitions

frontend/src/components/workflow/WorkflowCanvas.jsx
- Adjust canvas width when panel open
- Maintain node visibility during resize
```

**Acceptance Criteria:**
- ✅ Panel slides in from right on node select
- ✅ Panel doesn't block workflow view
- ✅ Smooth open/close animations
- ✅ Resizable panel width
- ✅ ESC key closes panel

**Estimated Time:** 3 days

---

### 2.2 Expression Editor with Autocomplete

**Current State:**
- Plain text input for parameters
- No autocomplete for ${node-id.field}
- Manual reference typing

**Implementation:**

**Frontend Changes:**
```
frontend/src/components/workflow/ExpressionEditor.jsx (NEW)
- Monaco Editor or CodeMirror integration
- Syntax highlighting for ${...} expressions
- Autocomplete for node IDs and fields
- Validation for expression syntax
- Preview of resolved value

frontend/src/utils/expressionParser.js (NEW)
- Parse ${node-id.field} expressions
- Validate expression syntax
- Resolve expressions against execution context
- Support for ${env:VAR} references

frontend/src/hooks/useExpressionAutocomplete.js (NEW)
- Build autocomplete suggestions from workflow
- Include node IDs, field names, env vars
- Filter suggestions based on input
```

**Acceptance Criteria:**
- ✅ Autocomplete shows available node references
- ✅ Syntax highlighting for expressions
- ✅ Validation errors shown inline
- ✅ Preview of resolved value
- ✅ Keyboard navigation in autocomplete

**Estimated Time:** 4 days

---

### 2.3 Custom Result Renderers

**Current State:**
- Basic JSON viewer for all results
- No type-specific rendering
- No export options

**Implementation:**

**Frontend Changes:**
```
frontend/src/components/workflow/renderers/CodeRenderer.jsx (NEW)
- Syntax-highlighted code display
- Language detection
- Copy to clipboard button
- Download as file button

frontend/src/components/workflow/renderers/DiffRenderer.jsx (NEW)
- Side-by-side diff view
- Highlight changes
- Line numbers
- Expand/collapse sections

frontend/src/components/workflow/renderers/TableRenderer.jsx (NEW)
- Tabular data display
- Sortable columns
- Filterable rows
- Export to CSV

frontend/src/components/workflow/renderers/MarkdownRenderer.jsx (NEW)
- Rendered markdown preview
- Raw markdown toggle
- Copy markdown button

frontend/src/components/workflow/ResultsViewer.jsx
- Detect result type (code, diff, table, markdown, json)
- Route to appropriate renderer
- Add renderer selector dropdown
```

**Acceptance Criteria:**
- ✅ Code results show syntax highlighting
- ✅ Diff results show side-by-side comparison
- ✅ Table results are sortable/filterable
- ✅ Markdown results are rendered
- ✅ Can export results in appropriate format

**Estimated Time:** 4 days

---

### 2.4 Execution Timeline View

**Current State:**
- Simple log list
- No visual timeline
- Hard to track execution flow

**Implementation:**

**Frontend Changes:**
```
frontend/src/components/workflow/ExecutionTimeline.jsx (NEW)
- Horizontal timeline with node execution
- Color-coded by status
- Hover shows details (duration, result preview)
- Click to jump to node
- Zoom controls for long workflows

frontend/src/components/workflow/ExecutionPanel.jsx
- Add timeline view tab
- Toggle between logs and timeline
- Sync timeline with node selection

frontend/src/hooks/useExecution.js
- Track execution timestamps per node
- Calculate node durations
- Build timeline data structure
```

**Acceptance Criteria:**
- ✅ Timeline shows execution order
- ✅ Node durations visualized
- ✅ Hover shows execution details
- ✅ Click timeline to select node
- ✅ Zoom controls for long workflows

**Estimated Time:** 3 days

---

### 2.5 Custom Node Renderers for MCP Types

**Current State:**
- Generic node appearance
- No visual distinction between MCP types
- Limited node information display

**Implementation:**

**Frontend Changes:**
```
frontend/src/components/workflow/nodes/AgentNode.jsx (NEW)
- Custom styling for agent nodes
- Show model icon/badge
- Display token usage estimate
- Thinking animation during execution

frontend/src/components/workflow/nodes/FileToolsNode.jsx (NEW)
- File icon and operation type
- Show file path preview
- File size indicator

frontend/src/components/workflow/nodes/ConditionalNode.jsx (NEW)
- Diamond shape for if/switch nodes
- Show condition preview
- Branch indicators

frontend/src/components/workflow/nodes/LoopNode.jsx (NEW)
- Loop icon and iteration count
- Show loop variable
- Progress indicator for iterations

frontend/src/components/workflow/MCPNode.jsx
- Route to custom renderer based on node type
- Fallback to generic renderer
```

**Acceptance Criteria:**
- ✅ Agent nodes have distinct appearance
- ✅ File nodes show file operations clearly
- ✅ Conditional nodes use diamond shape
- ✅ Loop nodes show iteration progress
- ✅ All nodes maintain consistent sizing

**Estimated Time:** 3 days

---

## Phase 3: Polish & Advanced Features (2 weeks)

**Goal:** Refine UX and add advanced workflow capabilities

### 3.1 Workflow Templates Library

**Current State:**
- Only example workflows available
- No template system
- No workflow discovery

**Implementation:**

**Frontend Changes:**
```
frontend/src/components/workflow/TemplateLibrary.jsx (NEW)
- Grid view of workflow templates
- Template preview cards
- Category filtering (Security, Development, Data Processing)
- Search by name/description
- "Use Template" button

frontend/src/pages/WorkflowsPage.jsx
- Add "Templates" button to toolbar
- Open template library modal
- Load selected template to canvas

frontend/src/utils/workflowTemplates.js (NEW)
- Template definitions
- Template metadata (category, tags, description)
- Template validation
```

**Backend Changes (Not Yet Implemented):**
```
backend/app/main.py
- Add GET /workflows/templates endpoint
- Return template list with metadata

workflows/templates/ (NEW DIRECTORY)
- security-scan.json
- code-review.json
- data-pipeline.json
- api-integration.json
```

**Note:** Backend template endpoints are not yet implemented. Phase 3.1 can initially use hardcoded templates in frontend. Backend implementation should be coordinated with workflow CRUD endpoints (Phase 1.4).

**See:** `docs/PRD-61-API-CONTRACT.md` for complete API specification.

**Acceptance Criteria:**
- ✅ Template library shows available templates
- ✅ Templates organized by category
- ✅ Search filters templates
- ✅ Preview shows template structure
- ✅ One-click template loading

**Estimated Time:** 3 days

---

### 3.2 Advanced Node Types UI

**Current State:**
- Only basic mcp_call nodes supported in UI
- No UI for if/else, loops, try/catch
- Backend supports these but UI doesn't

**Implementation:**

**Frontend Changes:**
```
frontend/src/components/workflow/NodePalette.jsx
- Add "Control Flow" section
- Add if/else, switch, for_each, while nodes
- Add try/catch, retry nodes
- Add set, sleep, webhook nodes

frontend/src/components/workflow/nodes/IfNode.jsx (NEW)
- Condition editor
- True/false branch indicators
- Visual branch connections

frontend/src/components/workflow/nodes/ForEachNode.jsx (NEW)
- Array input selector
- Item variable name
- Loop body indicator

frontend/src/components/workflow/nodes/TryCatchNode.jsx (NEW)
- Try block indicator
- Catch block indicator
- Error handling options

frontend/src/hooks/useWorkflow.js
- Support for advanced node types
- Validation for control flow nodes
- Branch connection handling
```

**Acceptance Criteria:**
- ✅ Control flow nodes in palette
- ✅ If/else nodes with condition editor
- ✅ Loop nodes with iteration config
- ✅ Try/catch nodes with error handling
- ✅ Proper validation for all node types

**Estimated Time:** 4 days

---

### 3.3 Performance Optimizations

**Current State:**
- No virtualization for large workflows
- Re-renders on every state change
- No memoization

**Implementation:**

**Frontend Changes:**
```
frontend/src/hooks/useWorkflow.js
- Add useMemo for expensive computations
- Optimize node state updates
- Batch state changes

frontend/src/components/workflow/WorkflowCanvas.jsx
- Enable ReactFlow virtualization
- Optimize edge rendering
- Lazy load node components

frontend/src/components/workflow/ExecutionPanel.jsx
- Virtualize log list for large logs
- Debounce log updates
- Limit visible logs (pagination)

frontend/src/utils/workflowValidation.js
- Cache validation results
- Incremental validation
- Debounce validation calls
```

**Acceptance Criteria:**
- ✅ Smooth performance with 50+ nodes
- ✅ No lag during execution updates
- ✅ Efficient memory usage
- ✅ Fast workflow loading
- ✅ Responsive UI during heavy operations

**Estimated Time:** 3 days

---

### 3.4 UI Polish & Refinement

**Current State:**
- Inconsistent spacing and styling
- No loading states
- Limited error handling

**Implementation:**

**Frontend Changes:**
```
frontend/src/components/workflow/LoadingStates.jsx (NEW)
- Skeleton loaders for components
- Spinner for async operations
- Progress indicators

frontend/src/components/workflow/ErrorStates.jsx (NEW)
- Friendly error messages
- Retry buttons
- Error details (collapsible)

frontend/src/pages/WorkflowsPage.css
- Consistent spacing (8px grid)
- Smooth transitions
- Hover states
- Focus indicators

frontend/src/components/workflow/Tooltips.jsx (NEW)
- Helpful tooltips for all actions
- Keyboard shortcut hints
- Context-sensitive help
```

**Acceptance Criteria:**
- ✅ Consistent spacing throughout
- ✅ Loading states for all async operations
- ✅ Friendly error messages
- ✅ Smooth animations and transitions
- ✅ Helpful tooltips everywhere

**Estimated Time:** 2 days

---

## Phase 4: Registry Integration (1 week)

**Goal:** Migrate workflows to registry pattern for versioning, signing, and distribution

### 4.1 Workflow Registry Structure

**Current State:**
- Workflows stored in `workflows/` directory
- No versioning or signing
- Inconsistent with mcps/teams/triggers pattern

**Implementation:**

**Registry Structure:**
```
registry/
└── workflows/
    └── {workflow-name}/
        └── {version}/
            ├── workflow.json       # Workflow definition
            ├── workflow.json.asc   # GPG signature
            └── metadata.json       # Package metadata
```

**Backend Changes:**
```
backend/app/main.py
- Update GET /registries/catalog to include workflows
- Add workflow filtering to catalog endpoint
- Reuse existing package verification logic

src/registry/package_types.py
- Add WorkflowPackage class
- Implement workflow-specific validation
- Add workflow metadata schema
```

**Acceptance Criteria:**
- ✅ Workflows follow registry pattern
- ✅ Workflows appear in catalog
- ✅ Workflows can be signed and verified
- ✅ Consistent with mcps/teams/triggers

**Estimated Time:** 2 days

---

### 4.2 Workflow Installation API

**Implementation:**

**Backend Changes:**
```
backend/app/main.py
- Add POST /registries/install/workflow/{workflow_id}
- Install workflow to user's workspace
- Verify signature before installation
- Track installed workflows

backend/app/docker_manager.py
- Add workflow installation tracking
- List installed workflows
- Update/uninstall workflows
```

**Frontend Changes:**
```
frontend/src/components/workflow/TemplateLibrary.jsx
- Update to use registry catalog API
- Show workflow versions
- Display publisher information
- Add "Install" button for registry workflows

frontend/src/hooks/useRegistry.js
- Add installWorkflow method
- Add listInstalledWorkflows method
- Handle installation status
```

**Acceptance Criteria:**
- ✅ Can install workflows from registry
- ✅ Signature verification before install
- ✅ Track installed workflows
- ✅ Show publisher information

**Estimated Time:** 2 days

---

### 4.3 Migrate Example Workflows

**Implementation:**

**Migration Steps:**
```bash
# Create registry structure
mkdir -p registry/workflows/{hello-world,code-review,network-scan}/1.0.0

# Move and sign workflows
for workflow in workflows/*.json; do
  name=$(basename $workflow .json)
  cp $workflow registry/workflows/$name/1.0.0/workflow.json
  gpg --detach-sign registry/workflows/$name/1.0.0/workflow.json
  # Generate metadata.json
done

# Update API to use registry
# Remove old /workflows/examples endpoints
# Update frontend to use registry catalog
```

**Backend Changes:**
```
backend/app/main.py
- Deprecate GET /workflows/examples
- Deprecate GET /workflows/examples/{filename}
- Add migration endpoint (optional)
- Update documentation
```

**Frontend Changes:**
```
frontend/src/pages/WorkflowsPage.jsx
- Update to use registry catalog
- Remove hardcoded examples
- Use installWorkflow instead of direct load

frontend/src/hooks/useWorkflow.js
- Update loadExample to use registry
- Handle workflow installation
```

**Acceptance Criteria:**
- ✅ All example workflows in registry
- ✅ Old endpoints deprecated
- ✅ Frontend uses registry catalog
- ✅ Backward compatibility maintained

**Estimated Time:** 1 day

---

### 4.4 Workflow Publishing

**Implementation:**

**Backend Changes:**
```
backend/app/main.py
- Add POST /workflows/publish endpoint
- Validate workflow before publishing
- Generate metadata.json
- Sign workflow with publisher key
- Add to registry catalog
```

**Frontend Changes:**
```
frontend/src/components/workflow/WorkflowToolbar.jsx
- Add "Publish" button
- Show publish dialog (name, version, description)
- Handle GPG key selection
- Show publish status

frontend/src/components/workflow/PublishDialog.jsx (NEW)
- Workflow name/version input
- Description and tags
- Category selection
- Publisher key selection
- Preview before publish
```

**Acceptance Criteria:**
- ✅ Users can publish workflows to registry
- ✅ Workflows are signed automatically
- ✅ Published workflows appear in catalog
- ✅ Version management supported

**Estimated Time:** 2 days

---

**Phase 4 Total Time:** 1 week (7 days)

---

## Technical Architecture

### Component Hierarchy

```
WorkflowsPage
├── WorkflowToolbar
│   ├── SaveButton
│   ├── LoadDropdown
│   ├── TemplatesButton
│   └── ExportButton
├── NodePalette
│   ├── MCPServersSection
│   └── ControlFlowSection
├── WorkflowCanvas (ReactFlow)
│   ├── MCPNode (custom node types)
│   ├── AgentNode
│   ├── FileToolsNode
│   ├── IfNode
│   └── ForEachNode
├── NodeConfigPanel (side panel)
│   ├── ParametersTab
│   │   └── ExpressionEditor
│   ├── SettingsTab
│   └── InfoTab
├── ExecutionPanel
│   ├── ProgressBar
│   ├── LogsView
│   └── TimelineView
└── ResultsViewer
    ├── CodeRenderer
    ├── DiffRenderer
    ├── TableRenderer
    └── MarkdownRenderer
```

### State Management

**Current Approach:** React hooks with local state

**Proposed Changes:**
- Keep React hooks for simplicity
- Add context for shared state (execution, validation)
- Use custom hooks for complex logic
- No need for Redux/Zustand yet

**State Structure:**
```javascript
// Workflow state (useWorkflow)
{
  nodes: Node[],
  edges: Edge[],
  selectedNode: string | null,
  validationErrors: ValidationError[]
}

// Execution state (useExecution)
{
  executing: boolean,
  executionId: string | null,
  nodeStates: Record<string, NodeState>,
  logs: ExecutionLog[],
  result: ExecutionResult | null
}

// MCP Registry state (useMCPRegistry)
{
  servers: MCPServer[],
  loading: boolean,
  error: Error | null
}
```

### API Contracts

**Existing Endpoints (No Changes):**
```
GET  /mcp/servers
POST /mcp/servers/{name}/tools
POST /workflows/execute
WS   /ws/execute/{session_id}
GET  /workflows/examples/{filename}
```

**Note:** MCP endpoints work fine as-is. No format changes required.

**New Endpoints (Phase 1.4):**
```
POST   /workflows
  Body: { name, workflow }
  Response: { id, name, created }

GET    /workflows
  Response: { workflows: [{ id, name, created, modified }] }

GET    /workflows/{id}
  Response: { id, name, workflow }

DELETE /workflows/{id}
  Response: { success: true }
```

**New Endpoints (Phase 3.1):**
```
GET /workflows/templates
  Response: { templates: [{ id, name, category, description, workflow }] }
```

### File Structure Changes

```
frontend/src/
├── components/
│   └── workflow/
│       ├── NodeConfigPanel.jsx (NEW - Phase 2.1)
│       ├── ExpressionEditor.jsx (NEW - Phase 2.2)
│       ├── ExecutionTimeline.jsx (NEW - Phase 2.4)
│       ├── TemplateLibrary.jsx (NEW - Phase 3.1)
│       ├── LoadingStates.jsx (NEW - Phase 3.4)
│       ├── ErrorStates.jsx (NEW - Phase 3.4)
│       ├── Tooltips.jsx (NEW - Phase 3.4)
│       ├── nodes/
│       │   ├── AgentNode.jsx (NEW - Phase 2.5)
│       │   ├── FileToolsNode.jsx (NEW - Phase 2.5)
│       │   ├── IfNode.jsx (NEW - Phase 3.2)
│       │   ├── ForEachNode.jsx (NEW - Phase 3.2)
│       │   └── TryCatchNode.jsx (NEW - Phase 3.2)
│       └── renderers/
│           ├── CodeRenderer.jsx (NEW - Phase 2.3)
│           ├── DiffRenderer.jsx (NEW - Phase 2.3)
│           ├── TableRenderer.jsx (NEW - Phase 2.3)
│           └── MarkdownRenderer.jsx (NEW - Phase 2.3)
├── hooks/
│   └── useExpressionAutocomplete.js (NEW - Phase 2.2)
└── utils/
    ├── workflowStorage.js (NEW - Phase 1.4)
    ├── expressionParser.js (NEW - Phase 2.2)
    └── workflowTemplates.js (NEW - Phase 3.1)

backend/
└── app/
    └── main.py (MODIFIED - Phase 1.4, 3.1)

workflows/
└── templates/ (NEW - Phase 3.1)
    ├── security-scan.json
    ├── code-review.json
    ├── data-pipeline.json
    └── api-integration.json
```

---

## Testing Strategy

### Unit Tests

**Phase 1:**
- `useWorkflow.test.js` - Workflow state management
- `workflowValidation.test.js` - Validation logic
- `workflowStorage.test.js` - LocalStorage operations

**Phase 2:**
- `expressionParser.test.js` - Expression parsing and validation
- `ExpressionEditor.test.jsx` - Expression editor component
- `ResultsViewer.test.jsx` - Result renderer selection

**Phase 3:**
- `workflowTemplates.test.js` - Template loading and validation
- `TemplateLibrary.test.jsx` - Template library component

### Integration Tests

**Phase 1:**
- Drag-and-drop node creation
- Node configuration modal
- Workflow save/load

**Phase 2:**
- Side panel interactions
- Expression autocomplete
- Execution timeline

**Phase 3:**
- Template loading
- Advanced node types
- End-to-end workflow creation

### Manual Testing Checklist

**Phase 1:**
- [ ] Drag node from palette to canvas
- [ ] Configure node parameters
- [ ] Execute workflow and see progress
- [ ] Save and load workflow
- [ ] Export and import JSON

**Phase 2:**
- [ ] Open side panel for node config
- [ ] Use expression autocomplete
- [ ] View results in custom renderers
- [ ] Navigate execution timeline
- [ ] Test all custom node types

**Phase 3:**
- [ ] Browse template library
- [ ] Load and customize template
- [ ] Create workflow with control flow nodes
- [ ] Test performance with large workflow
- [ ] Verify all UI polish items

---

## Risk Mitigation

### Technical Risks

**Risk:** ReactFlow performance with large workflows  
**Mitigation:** Enable virtualization, optimize rendering, test with 100+ nodes

**Risk:** Expression parser complexity  
**Mitigation:** Use existing parser libraries (e.g., mathjs), comprehensive tests

**Risk:** WebSocket connection stability  
**Mitigation:** Implement reconnection logic, fallback to polling

**Risk:** Browser compatibility issues  
**Mitigation:** Test on Chrome, Firefox, Safari; use polyfills

### Schedule Risks

**Risk:** Phase 1 takes longer than 2 weeks  
**Mitigation:** Prioritize drag-and-drop and inline editing, defer save/load if needed

**Risk:** Phase 2 scope creep  
**Mitigation:** Strict scope control, defer nice-to-haves to Phase 3

**Risk:** Phase 3 polish takes too long  
**Mitigation:** Define "done" criteria upfront, timebox polish work

### User Experience Risks

**Risk:** Users prefer old UI  
**Mitigation:** Keep old UI accessible via feature flag, gather feedback early

**Risk:** Learning curve for new features  
**Mitigation:** Add tooltips, help text, tutorial workflow

**Risk:** Breaking changes to existing workflows  
**Mitigation:** Maintain backward compatibility, migration guide

---

## Success Criteria

### Phase 1 Success Metrics

- ✅ 90% of users can create workflow without documentation
- ✅ Workflow creation time reduced by 30%
- ✅ Zero critical bugs in production
- ✅ Positive user feedback (>4/5 rating)

### Phase 2 Success Metrics

- ✅ Expression autocomplete used in 80% of parameter inputs
- ✅ Custom renderers improve result readability (user survey)
- ✅ Execution timeline helps debug workflows (user survey)
- ✅ Side panel preferred over modal (A/B test)

### Phase 3 Success Metrics

- ✅ 50% of workflows created from templates
- ✅ Advanced node types used in 30% of workflows
- ✅ Performance acceptable with 100+ node workflows
- ✅ UI polish items completed (100% checklist)

---

## Rollout Plan

### Phase 1 Rollout

**Week 1-2:** Development  
**Week 3:** Internal testing and bug fixes  
**Week 4:** Beta release to select users  
**Week 5:** Production release with feature flag

### Phase 2 Rollout

**Week 6-8:** Development  
**Week 9:** Internal testing and bug fixes  
**Week 10:** Beta release to select users  
**Week 11:** Production release

### Phase 3 Rollout

**Week 12-13:** Development  
**Week 14:** Internal testing and bug fixes  
**Week 15:** Beta release to select users  
**Week 16:** Production release

### Phase 4 Rollout

**Week 17:** Development (registry structure and migration)  
**Week 18:** Internal testing and workflow migration  
**Week 19:** Beta release with backward compatibility  
**Week 20:** Production release and deprecate old endpoints

### Feature Flags

```javascript
// Feature flag configuration
const FEATURE_FLAGS = {
  dragDropNodes: true,        // Phase 1
  inlineEditing: true,        // Phase 1
  enhancedExecution: true,    // Phase 1
  workflowSaveLoad: true,     // Phase 1
  sidePanel: false,           // Phase 2 (beta)
  expressionEditor: false,    // Phase 2 (beta)
  customRenderers: false,     // Phase 2 (beta)
  executionTimeline: false,   // Phase 2 (beta)
  templateLibrary: false,     // Phase 3 (beta)
  advancedNodes: false,       // Phase 3 (beta)
};
```

---

## Documentation Requirements

### User Documentation

**Phase 1:**
- Workflow creation guide
- Node configuration tutorial
- Save/load workflows guide

**Phase 2:**
- Expression syntax reference
- Custom renderer guide
- Execution timeline guide

**Phase 3:**
- Template library guide
- Advanced node types reference
- Performance best practices

### Developer Documentation

**Phase 1:**
- Component API documentation
- Hook usage examples
- Testing guide

**Phase 2:**
- Expression parser API
- Custom renderer development guide
- Side panel integration guide

**Phase 3:**
- Template creation guide
- Custom node type development
- Performance optimization guide

---

## Appendix

### Dependencies

**New NPM Packages:**
```json
{
  "monaco-editor": "^0.44.0",           // Phase 2.2 - Expression editor
  "react-monaco-editor": "^0.51.0",     // Phase 2.2
  "react-diff-viewer": "^3.1.1",        // Phase 2.3 - Diff renderer
  "react-markdown": "^9.0.0",           // Phase 2.3 - Markdown renderer
  "react-syntax-highlighter": "^15.5.0", // Phase 2.3 - Code renderer
  "react-virtualized": "^9.22.5"        // Phase 3.3 - Performance
}
```

### Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

### Accessibility

- WCAG 2.1 Level AA compliance
- Keyboard navigation for all features
- Screen reader support
- High contrast mode support

---

**Document Version:** 1.0  
**Last Updated:** 2025-11-03  
**Next Review:** After Phase 1 completion
