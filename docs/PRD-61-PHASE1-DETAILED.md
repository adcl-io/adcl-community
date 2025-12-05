# PRD-61: Phase 1 Detailed Implementation Plan

**Phase:** 1 - Quick Wins  
**Duration:** 2 weeks  
**Goal:** Deliver immediate value with Shadcn/Tailwind migration

---

## Overview

Phase 1 focuses on quick wins that immediately improve the workflow creation experience. Additionally, we'll migrate all workflow components to use Shadcn UI and Tailwind CSS for consistency with the rest of the platform and proper theme support.

---

## Task Breakdown

### Task 1.0: Shadcn/Tailwind Migration (3 days)

**Priority:** HIGH - Must be done first to establish foundation

#### 1.0.1 Audit Current Styling

**File:** `frontend/src/pages/WorkflowsPage.css`

Current approach:
- Custom CSS file with hardcoded colors
- No theme support
- Inconsistent with rest of UI

**Action Items:**
- [ ] Document all current styles
- [ ] Map to Shadcn/Tailwind equivalents
- [ ] Identify custom styles that need preservation

---

#### 1.0.2 Convert WorkflowsPage Layout

**Before:**
```css
/* WorkflowsPage.css */
.workflows-page {
  display: flex;
  height: 100vh;
  background: #1a1a1a;
  color: #ffffff;
}

.workflow-sidebar {
  width: 300px;
  background: #2a2a2a;
  border-right: 1px solid #3a3a3a;
  padding: 20px;
}
```

**After:**
```jsx
// WorkflowsPage.jsx
<div className="flex h-screen bg-background text-foreground">
  <div className="w-80 bg-card border-r border-border p-6">
    {/* Sidebar content */}
  </div>
  <div className="flex-1">
    {/* Canvas */}
  </div>
</div>
```

**Shadcn Classes Used:**
- `bg-background` - Main background color (theme-aware)
- `text-foreground` - Main text color (theme-aware)
- `bg-card` - Card background (theme-aware)
- `border-border` - Border color (theme-aware)
- `p-6` - Padding (24px, follows 8px grid)
- `w-80` - Width (320px)

---

#### 1.0.3 Convert Components to Shadcn

**NodePalette Component:**

```jsx
// Before (custom CSS)
<div className="node-palette">
  <h3 className="palette-title">MCP Servers</h3>
  <div className="node-list">
    {servers.map(server => (
      <div key={server.name} className="node-item">
        {server.name}
      </div>
    ))}
  </div>
</div>

// After (Shadcn/Tailwind)
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

<Card>
  <CardHeader>
    <CardTitle>MCP Servers</CardTitle>
  </CardHeader>
  <CardContent className="space-y-2">
    {servers.map(server => (
      <div
        key={server.name}
        className="flex items-center justify-between p-3 rounded-md border border-border hover:bg-accent hover:text-accent-foreground cursor-pointer transition-colors"
        draggable
      >
        <span className="font-medium">{server.name}</span>
        <Badge variant="secondary">{server.tools.length}</Badge>
      </div>
    ))}
  </CardContent>
</Card>
```

**ExecutionPanel Component:**

```jsx
// Before
<div className="execution-panel">
  <button className="execute-btn" onClick={onExecute}>
    Execute Workflow
  </button>
  <div className="logs">
    {logs.map(log => (
      <div className={`log-entry log-${log.level}`}>
        {log.message}
      </div>
    ))}
  </div>
</div>

// After
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription } from '@/components/ui/alert';

<Card>
  <CardHeader>
    <CardTitle>Execution</CardTitle>
  </CardHeader>
  <CardContent className="space-y-4">
    <Button 
      onClick={onExecute} 
      disabled={executing}
      className="w-full"
    >
      {executing ? (
        <>
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          Executing...
        </>
      ) : (
        'Execute Workflow'
      )}
    </Button>
    
    <ScrollArea className="h-64">
      <div className="space-y-2">
        {logs.map((log, i) => (
          <Alert key={i} variant={log.level === 'error' ? 'destructive' : 'default'}>
            <AlertDescription className="text-sm">
              {log.message}
            </AlertDescription>
          </Alert>
        ))}
      </div>
    </ScrollArea>
  </CardContent>
</Card>
```

**WorkflowToolbar Component:**

```jsx
// After
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Save, FolderOpen, Download, Upload } from 'lucide-react';

<div className="flex items-center gap-2 p-4 border-b border-border bg-card">
  <Button onClick={onSave} variant="default">
    <Save className="mr-2 h-4 w-4" />
    Save
  </Button>
  
  <DropdownMenu>
    <DropdownMenuTrigger asChild>
      <Button variant="outline">
        <FolderOpen className="mr-2 h-4 w-4" />
        Load
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent>
      {workflows.map(wf => (
        <DropdownMenuItem key={wf.id} onClick={() => onLoad(wf.id)}>
          {wf.name}
        </DropdownMenuItem>
      ))}
    </DropdownMenuContent>
  </DropdownMenu>
  
  <Button onClick={onExport} variant="outline">
    <Download className="mr-2 h-4 w-4" />
    Export
  </Button>
  
  <Button onClick={onImport} variant="outline">
    <Upload className="mr-2 h-4 w-4" />
    Import
  </Button>
</div>
```

---

#### 1.0.4 Theme Support

**Add Theme Provider:**

```jsx
// App.jsx
import { ThemeProvider } from 'next-themes';

function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
      {/* App content */}
    </ThemeProvider>
  );
}
```

**Theme Toggle in Navigation:**

```jsx
// Navigation.jsx
import { ThemeToggle } from '@/components/ui/theme-toggle';

<nav className="flex items-center justify-between p-4 border-b border-border">
  {/* Navigation items */}
  <ThemeToggle />
</nav>
```

**CSS Variables (already in index.css):**

```css
@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --border: 214.3 31.8% 91.4%;
    /* ... */
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --card: 222.2 84% 4.9%;
    --card-foreground: 210 40% 98%;
    --border: 217.2 32.6% 17.5%;
    /* ... */
  }
}
```

---

#### 1.0.5 Remove Old CSS

**Files to Delete:**
- `frontend/src/pages/WorkflowsPage.css`

**Files to Update:**
- Remove CSS imports from all workflow components
- Ensure all styling is via Tailwind classes

---

#### 1.0.6 Testing Theme Support

**Unit Tests:**

```javascript
// __tests__/theming.test.jsx
import { render } from '@testing-library/react';
import { ThemeProvider } from 'next-themes';
import WorkflowsPage from '../WorkflowsPage';

describe('Theme Support', () => {
  test('renders in light mode', () => {
    const { container } = render(
      <ThemeProvider defaultTheme="light">
        <WorkflowsPage />
      </ThemeProvider>
    );
    
    expect(container.firstChild).not.toHaveClass('dark');
  });

  test('renders in dark mode', () => {
    const { container } = render(
      <ThemeProvider defaultTheme="dark">
        <WorkflowsPage />
      </ThemeProvider>
    );
    
    expect(container.firstChild).toHaveClass('dark');
  });

  test('uses theme-aware colors', () => {
    const { getByTestId } = render(
      <ThemeProvider defaultTheme="dark">
        <WorkflowsPage />
      </ThemeProvider>
    );
    
    const sidebar = getByTestId('workflow-sidebar');
    expect(sidebar).toHaveClass('bg-card');
  });
});
```

**Manual Testing:**
- [ ] Light theme displays correctly
- [ ] Dark theme displays correctly
- [ ] Theme toggle works
- [ ] All components use theme colors
- [ ] No hardcoded colors remain
- [ ] Consistent with rest of UI

---

### Task 1.1: Drag-and-Drop Node Creation (2 days)

*(Detailed in main implementation plan)*

**Dependencies:** Task 1.0 (Shadcn migration)

**Shadcn Components Used:**
- `Badge` - For tool count
- `Card` - For palette container
- Tailwind utilities for drag feedback

---

### Task 1.2: Inline Parameter Editing (3 days)

**New Component:** `NodeConfigModal.jsx`

**Shadcn Components:**

```jsx
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';

function NodeConfigModal({ node, toolSchema, onSave, onClose }) {
  const [params, setParams] = useState(node.data.params);
  const [errors, setErrors] = useState({});

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Configure Node</DialogTitle>
          <DialogDescription>
            {node.data.mcp_server}.{node.data.tool}
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          {Object.entries(toolSchema.properties).map(([key, schema]) => (
            <div key={key} className="space-y-2">
              <Label htmlFor={key}>
                {key}
                {toolSchema.required?.includes(key) && (
                  <span className="text-destructive ml-1">*</span>
                )}
              </Label>
              
              {schema.type === 'string' && schema.description?.length > 100 ? (
                <Textarea
                  id={key}
                  value={params[key] || ''}
                  onChange={(e) => setParams({ ...params, [key]: e.target.value })}
                  placeholder={schema.description}
                  className={errors[key] ? 'border-destructive' : ''}
                />
              ) : (
                <Input
                  id={key}
                  value={params[key] || ''}
                  onChange={(e) => setParams({ ...params, [key]: e.target.value })}
                  placeholder={schema.description}
                  className={errors[key] ? 'border-destructive' : ''}
                />
              )}
              
              {errors[key] && (
                <Alert variant="destructive">
                  <AlertDescription className="text-sm">
                    {errors[key]}
                  </AlertDescription>
                </Alert>
              )}
            </div>
          ))}
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave}>
            Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

**Testing:**
- Unit tests for validation
- Integration tests for save flow
- Manual testing for UX

---

### Task 1.3: Enhanced Execution Visualization (2 days)

**Updated MCPNode with Status:**

```jsx
import { Badge } from '@/components/ui/badge';
import { Loader2, CheckCircle2, XCircle, Clock } from 'lucide-react';

function MCPNode({ data }) {
  const statusIcons = {
    idle: <Clock className="h-4 w-4 text-muted-foreground" />,
    running: <Loader2 className="h-4 w-4 animate-spin text-primary" />,
    completed: <CheckCircle2 className="h-4 w-4 text-success" />,
    error: <XCircle className="h-4 w-4 text-destructive" />
  };

  const statusColors = {
    idle: 'border-border',
    running: 'border-primary',
    completed: 'border-success',
    error: 'border-destructive'
  };

  return (
    <div className={`
      p-4 rounded-lg border-2 bg-card
      ${statusColors[data.executionStatus || 'idle']}
      transition-all duration-200
    `}>
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium text-sm">{data.label}</span>
        {statusIcons[data.executionStatus || 'idle']}
      </div>
      
      {data.params && Object.keys(data.params).length > 0 && (
        <Badge variant="secondary" className="text-xs">
          {Object.keys(data.params).length} params
        </Badge>
      )}
      
      {data.executionTime && (
        <div className="text-xs text-muted-foreground mt-2">
          {data.executionTime}ms
        </div>
      )}
    </div>
  );
}
```

**Progress Bar Component:**

```jsx
import { Progress } from '@/components/ui/progress';

function ExecutionProgress({ progress, currentNode, estimatedTime }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">
          {currentNode ? `Executing: ${currentNode}` : 'Ready'}
        </span>
        <span className="font-medium">{progress}%</span>
      </div>
      
      <Progress value={progress} className="h-2" />
      
      {estimatedTime && (
        <div className="text-xs text-muted-foreground text-right">
          ~{estimatedTime}s remaining
        </div>
      )}
    </div>
  );
}
```

---

### Task 1.4: Workflow Save/Load UI (3 days)

**Save Dialog:**

```jsx
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';

function SaveWorkflowDialog({ open, onClose, onSave }) {
  const [name, setName] = useState('');

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Save Workflow</DialogTitle>
          <DialogDescription>
            Give your workflow a name to save it
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="name">Workflow Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Workflow"
            />
          </div>
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={() => onSave(name)} disabled={!name}>
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

---

## Component Checklist

### Shadcn Components to Use

- [x] `Card`, `CardHeader`, `CardTitle`, `CardContent` - Container components
- [x] `Button` - All buttons
- [x] `Badge` - Status indicators, counts
- [x] `Dialog` - Modals
- [x] `Input`, `Textarea`, `Label` - Form fields
- [x] `DropdownMenu` - Dropdowns
- [x] `ScrollArea` - Scrollable areas
- [x] `Alert` - Notifications, errors
- [x] `Progress` - Progress bars
- [x] `Skeleton` - Loading states

### Lucide Icons to Use

- `Save`, `FolderOpen`, `Download`, `Upload` - Toolbar actions
- `Loader2` - Loading spinner
- `CheckCircle2`, `XCircle`, `Clock` - Status icons
- `Settings`, `Play`, `Pause`, `X` - Control icons

---

## Testing Checklist

### Unit Tests
- [ ] Theme support tests
- [ ] Component rendering tests
- [ ] Drag-and-drop tests
- [ ] Parameter editing tests
- [ ] Execution visualization tests
- [ ] Save/load tests

### Integration Tests
- [ ] Complete workflow creation flow
- [ ] Theme switching
- [ ] Save and load workflow
- [ ] Export and import

### Manual Tests
- [ ] Visual consistency with rest of UI
- [ ] Light/dark theme switching
- [ ] All interactions work
- [ ] Responsive layout
- [ ] Accessibility (keyboard navigation, screen readers)

---

## Acceptance Criteria

### Shadcn/Tailwind Migration
- ✅ All components use Shadcn UI primitives
- ✅ All styling via Tailwind classes
- ✅ No custom CSS files
- ✅ Theme support (light/dark)
- ✅ Consistent with rest of platform
- ✅ 8px grid spacing
- ✅ Proper focus indicators
- ✅ Hover states

### Drag-and-Drop
- ✅ Drag node from palette to canvas
- ✅ Node appears at cursor position
- ✅ Visual feedback during drag
- ✅ Drop zone indicator

### Parameter Editing
- ✅ Double-click opens modal
- ✅ Form generated from schema
- ✅ Validation errors shown
- ✅ Changes saved

### Execution Visualization
- ✅ Progress bar shows completion
- ✅ Node status indicators
- ✅ Execution time displayed
- ✅ Cancel button works

### Save/Load
- ✅ Save workflow with name
- ✅ Load from dropdown
- ✅ Export JSON
- ✅ Import JSON
- ✅ Persist across sessions

---

## Timeline

**Day 1-3:** Shadcn/Tailwind migration  
**Day 4-5:** Drag-and-drop implementation  
**Day 6-8:** Parameter editing  
**Day 9-10:** Execution visualization  
**Day 11-13:** Save/load UI  
**Day 14:** Testing, bug fixes, polish

---

**Document Version:** 1.0  
**Last Updated:** 2025-11-03
