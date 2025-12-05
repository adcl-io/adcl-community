# ADCL Platform Playground UI - Complete Analysis

## Project Structure Overview

The playground is built with React + Vite, using TypeScript/JSX, Tailwind CSS, and Shadcn UI components. The codebase is modular and follows the Unix philosophy principles outlined in CLAUDE.md.

### Frontend Directory Structure
```
frontend/src/
├── pages/
│   ├── PlaygroundPage.jsx          # Main chat interface (35KB)
│   ├── HistoryPage.jsx              # Conversation history view (7KB)
│   ├── ModelsPage.jsx               # Model management
│   ├── TeamsPage.jsx                # Team management
│   ├── AgentsPage.jsx               # Agent configuration
│   ├── MCPServersPage.jsx           # MCP server management
│   ├── RegistryPage.jsx             # Package registry
│   ├── WorkflowsPage.jsx            # Workflow builder
│   └── TriggersPage.jsx             # Event triggers
├── components/
│   ├── Navigation.jsx               # Left sidebar navigation
│   ├── UserSettings.jsx             # Settings modal
│   ├── ErrorBoundary.jsx            # Error handling
│   ├── ui/                          # Shadcn UI components
│   └── workflow/                    # Workflow-specific components
├── contexts/
│   └── ConversationHistoryContext.jsx  # Shared history state
├── hooks/
│   └── useConversationHistory.js    # Conversation persistence logic
└── App.jsx                          # Main app entry point
```

---

## 1. PLAYGROUND COMPONENT FILES

### Primary Playground Implementation: PlaygroundPage.jsx

**File Path:** `/home/jason/Desktop/adcl/adcl2/demo-sandbox/frontend/src/pages/PlaygroundPage.jsx`

**Size:** 35 KB, 935 lines

**Key Responsibilities:**
- Main chat interface rendering
- WebSocket connection management for real-time agent streaming
- HTTP fallback for teams without MCP servers
- Message display and formatting
- Team selection and management
- Execution control (start/stop)
- Session management integration

**Core State Management:**
```javascript
// Local component state
const [input, setInput] = useState('');
const [selectedTeam, setSelectedTeam] = useState(null);
const [teams, setTeams] = useState([]);
const [loading, setLoading] = useState(false);
const [streamingStatus, setStreamingStatus] = useState(null);
const [executionId, setExecutionId] = useState(null);
const [lastExecutionSummary, setLastExecutionSummary] = useState(null);

// Refs for non-rendered state
const wsRef = useRef(null);
const sessionIdRef = useRef(null);
const executionStartTime = useRef(null);
const executionCancelled = useRef(false);

// Shared context state
const {
  currentSessionId,
  sessions,
  messages,
  loading: historyLoading,
  initialized,
  appendMessage,
  loadSession,
  startNewConversation,
  loadSessions,
  clearAllHistory,
  setMessages,
  setCurrentSessionId
} = useConversationHistoryContext();
```

---

## 2. PLAYGROUND TOP BAR COMPONENT

**Location:** Lines 657-689 in PlaygroundPage.jsx

The "top bar" is a simple header component with:

```jsx
{/* Header */}
<div className="p-4 border-b border-border bg-card flex items-center justify-between">
  {/* Left side: Title + New Chat button */}
  <div className="flex items-center gap-3">
    <h2 className="text-lg font-semibold text-foreground">
      {selectedTeam?.name || 'ADCL Chat'}
    </h2>
    <Button
      size="sm"
      variant="outline"
      onClick={handleNewConversation}
    >
      <Plus className="h-4 w-4 mr-2" />
      New Chat
    </Button>
  </div>
  
  {/* Right side: Team selector + Settings */}
  <div className="flex items-center gap-3">
    <Button
      variant="outline"
      size="sm"
      onClick={() => setShowTeamSelector(true)}
      className="gap-2"
    >
      <Users className="h-4 w-4" />
      <span className="font-medium">{selectedTeam?.name || 'Select Team'}</span>
      {selectedTeam?.agents && selectedTeam.agents.length > 0 && (
        <span className="text-xs opacity-60 font-mono">
          ({selectedTeam.agents.length} {selectedTeam.agents.length === 1 ? 'agent' : 'agents'})
        </span>
      )}
    </Button>
    <UserSettings onClearHistory={handleClearHistory} />
  </div>
</div>
```

**Top Bar Features:**
- **Team Display:** Shows currently selected team name
- **New Chat Button:** Initiates new conversation
- **Team Selector:** Dropdown/modal to switch teams
- **Agent Count Badge:** Shows number of agents in selected team
- **Settings Menu:** Access to user preferences and history clearing

---

## 3. CHAT/MESSAGE DATA MANAGEMENT

### Message Storage Architecture

Messages are stored in two locations:

#### A. **Local Component State (Immediate UI Updates)**
```javascript
const [messages, setMessages] = useState([]);
```

#### B. **Persistent Backend (History MCP Server)**
Via the `ConversationHistoryContext` and `useConversationHistory` hook

### Message Structure

Messages conform to this structure:

```typescript
{
  id: string,                    // UUID
  role: 'user' | 'assistant' | 'error' | 'agent-status',
  content: string,               // Message text
  timestamp: string,             // ISO 8601 timestamp
  metadata: {
    // Optional fields depending on message type
    agent_id?: string,
    agent_role?: string,
    agent_color?: string,
    type?: string,               // 'execution_started', 'status', 'agent_start', etc.
    iteration?: number,
    max_iterations?: number,
    token_usage?: {
      input_tokens: number,
      output_tokens: number
    },
    model?: string,
    tools_used?: Array<{
      name: string,
      summary: string
    }>,
    stop_reason?: string,
    thinking_preview?: string,
    thinking?: string,
    tool_name?: string,
    tool_summary?: string,
    persist?: boolean             // Whether to save to history
  },
  agent?: string,                // Agent name/ID
  tools?: Array<string>,         // Tools used
  agentActivity?: Array<object>, // Agent execution log
  team_result?: object           // Full execution result
}
```

### Message Flow

1. **User sends message:**
   ```javascript
   const userMessage = {
     id: crypto.randomUUID(),
     role: 'user',
     content: input,
     timestamp: new Date().toISOString()
   };
   await appendMessage(userMessage);
   ```

2. **Messages append to local state:**
   ```javascript
   setMessages(prev => [...prev, uiMessage]);
   ```

3. **Messages persist to backend:**
   ```javascript
   const response = await axios.post(`${HISTORY_MCP_URL}/mcp/call_tool`, {
     tool: 'append_message',
     arguments: {
       session_id: sessionId,
       message_type: message.role,
       content: message.content,
       metadata: message.metadata
     }
   });
   ```

---

## 4. TOKEN TRACKING AND API RESPONSE HANDLING

### Token Usage Collection

Tokens are tracked at multiple points and aggregated:

#### A. **Per-Iteration Token Tracking** (Lines 346-358)

```javascript
const iterationData = {
  type: 'agent_iteration',
  iteration: data.iteration,
  max_iterations: data.max_iterations,
  token_usage: data.token_usage,        // {input_tokens, output_tokens}
  model: data.model,
  tools_used: data.tools_used,
  stop_reason: data.stop_reason,
  thinking_preview: data.thinking_preview,
  agent_id: currentAgent.id,
  agent_role: currentAgent.role,
  agent_color: currentAgent.color
};
```

#### B. **Execution Summary Aggregation** (Lines 468-504)

```javascript
// Sum up total tokens and iterations
let totalTokensIn = 0;
let totalTokensOut = 0;
let maxIteration = 0;

agentActivityLog.forEach(activity => {
  if (activity.type === 'iteration' && activity.metadata) {
    if (activity.metadata.token_usage) {
      totalTokensIn += activity.metadata.token_usage.input_tokens || 0;
      totalTokensOut += activity.metadata.token_usage.output_tokens || 0;
    }
    if (activity.metadata.iteration) {
      maxIteration = Math.max(maxIteration, activity.metadata.iteration);
    }
  }
});

const totalTokens = totalTokensIn + totalTokensOut;

setLastExecutionSummary({
  agentCount,
  iterations: maxIteration,
  time: executionTime,
  tokens: totalTokens,
  tokensIn: totalTokensIn,
  tokensOut: totalTokensOut
});
```

### Token Display Locations

#### 1. **Inline in Message Metadata** (Lines 747-777)

```jsx
{message.role === 'agent-status' && message.metadata && (
  <div className="mt-2 pt-2 border-t border-current/10">
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs font-mono text-muted-foreground/70">
      {message.metadata?.token_usage && (
        <span>
          Tokens: {message.metadata.token_usage.input_tokens?.toLocaleString() || 0} in / 
                  {message.metadata.token_usage.output_tokens?.toLocaleString() || 0} out
        </span>
      )}
      {message.metadata?.model && (
        <span>Model: {message.metadata.model}</span>
      )}
      {message.metadata?.iteration && (
        <span>{message.metadata.iteration}/{message.metadata.max_iterations} iterations</span>
      )}
    </div>
  </div>
)}
```

#### 2. **Execution Summary Bar** (Lines 835-862)

A horizontal bar at bottom of chat showing last execution stats:

```jsx
{lastExecutionSummary && (
  <div className="border-t border-border bg-muted/30 px-4 py-2">
    <div className="max-w-3xl mx-auto flex items-center justify-between text-xs font-mono text-muted-foreground">
      <div className="flex items-center gap-4">
        <span className="font-semibold text-foreground">Last run:</span>
        {lastExecutionSummary.agentCount > 0 && (
          <span>{lastExecutionSummary.agentCount} agents</span>
        )}
        {lastExecutionSummary.iterations > 0 && (
          <span>{lastExecutionSummary.iterations} iterations</span>
        )}
        {lastExecutionSummary.time && (
          <span>{lastExecutionSummary.time}s</span>
        )}
        {lastExecutionSummary.tokens > 0 && (
          <span>{lastExecutionSummary.tokens.toLocaleString()} tokens</span>
        )}
      </div>
    </div>
  </div>
)}
```

### WebSocket Message Types for Token Data

The WebSocket receives several message types that contain token information:

```javascript
// On agent iteration (contains token_usage)
data.type === 'agent_iteration'  // token_usage: {input_tokens, output_tokens}

// On execution complete (final aggregated data)
data.type === 'complete'         // result contains full execution summary

// Status updates
data.type === 'status'           // Generic status messages
data.type === 'agent_start'      // Agent begins work
data.type === 'agent_complete'   // Agent finishes
data.type === 'tool_execution'   // Tool execution event
```

---

## 5. CONVERSATION/EXECUTION STORAGE AND TRACKING

### Session/Conversation Persistence

#### Backend Storage: History MCP Server

**URL:** `http://localhost:7004` (via `VITE_HISTORY_MCP_URL` env var)

**Stored via:** `/mcp/call_tool` endpoint

**Persistence Operations:**

1. **Create Session:**
   ```javascript
   POST ${HISTORY_MCP_URL}/mcp/call_tool
   {
     tool: 'create_session',
     arguments: {
       title: string (auto-generated from first message),
       metadata: {}
     }
   }
   ```

2. **Append Message:**
   ```javascript
   POST ${HISTORY_MCP_URL}/mcp/call_tool
   {
     tool: 'append_message',
     arguments: {
       session_id: string,
       message_type: string,        // 'user', 'assistant', 'error', etc.
       content: string,
       metadata: {
         agent, tools, token_usage, iteration, etc.
       }
     }
   }
   ```

3. **Load Session:**
   ```javascript
   POST ${HISTORY_MCP_URL}/mcp/call_tool
   {
     tool: 'get_messages',
     arguments: {
       session_id: string,
       limit: 100,
       reverse: false
     }
   }
   ```

4. **List Sessions:**
   ```javascript
   POST ${HISTORY_MCP_URL}/mcp/call_tool
   {
     tool: 'list_sessions',
     arguments: {
       limit: 50,
       status: 'active'
     }
   }
   ```

5. **Search Messages:**
   ```javascript
   POST ${HISTORY_MCP_URL}/mcp/call_tool
   {
     tool: 'search_messages',
     arguments: {
       query: string,
       limit: 100
     }
   }
   ```

### Execution Tracking

#### Execution ID and State

```javascript
const [executionId, setExecutionId] = useState(null);
const executionStartTime = useRef(null);
const executionCancelled = useRef(false);

// On execution start
if (data.type === 'execution_started') {
  setExecutionId(data.execution_id);
  executionStartTime.current = Date.now();
}

// Calculate execution time
const executionTime = executionStartTime.current
  ? ((Date.now() - executionStartTime.current) / 1000).toFixed(1)
  : null;
```

#### Agent Activity Logging

```javascript
const agentActivityLog = [];

// Logged on each agent event
agentActivityLog.push({
  type: 'start',              // or 'complete', 'iteration'
  agent_id: data.agent_id,
  role: data.role,
  message: data.message,
  progress: data.progress,
  iteration: data.iteration,
  max_iterations: data.max_iterations,
  token_usage: data.token_usage,
  model: data.model,
  tools_used: data.tools_used
});

// Stored in assistant message metadata
const assistantMessage = {
  id: crypto.randomUUID(),
  role: 'assistant',
  content: data.result.answer,
  agent: selectedTeam?.name,
  timestamp: new Date().toISOString(),
  agentActivity: agentActivityLog,
  team_result: data.result,
  metadata: {
    agentActivity: agentActivityLog,
    team_result: data.result
  }
};
```

---

## 6. DATA FLOW DIAGRAM

### Message/Chat Flow

```
User Input
   ↓
[PlaygroundPage] sendMessage()
   ├─→ Create userMessage object
   ├─→ appendMessage() → ConversationHistoryContext
   │   ├─→ Check if session exists
   │   ├─→ Create new session if needed (via History MCP)
   │   ├─→ Add to local messages state
   │   └─→ Persist to History MCP Server (async)
   ├─→ Send via WebSocket or HTTP
   │   ├─→ WebSocket: ws://localhost:8000/ws/chat/{sessionId}
   │   └─→ HTTP: POST /chat
   └─→ Receive streaming response

WebSocket Messages
   ↓
[PlaygroundPage] ws.onmessage()
   ├─→ Parse JSON
   ├─→ Route by data.type
   │   ├─→ execution_started
   │   ├─→ status
   │   ├─→ agent_start
   │   ├─→ agent_iteration (contains token_usage)
   │   ├─→ tool_execution
   │   ├─→ agent_complete
   │   └─→ complete (final results + tokens)
   ├─→ Create status messages
   ├─→ Call addAgentStatusMessage()
   ├─→ Aggregate execution metrics
   └─→ Update lastExecutionSummary

Assistant Response
   ↓
appendMessage(assistantMessage)
   ├─→ Add to messages state
   └─→ Persist to History MCP

Render
   ↓
Display in ScrollArea with:
   ├─→ Message bubbles
   ├─→ Token counts
   ├─→ Tool usage
   ├─→ Agent activity details
   └─→ Execution summary bar
```

---

## 7. CONVERSATION HISTORY CONTEXT

**File:** `/home/jason/Desktop/adcl/adcl2/demo-sandbox/frontend/src/contexts/ConversationHistoryContext.jsx`

Simple context provider wrapper around the `useConversationHistory` hook.

```javascript
export function ConversationHistoryProvider({ children }) {
  const history = useConversationHistory();
  return (
    <ConversationHistoryContext.Provider value={history}>
      {children}
    </ConversationHistoryContext.Provider>
  );
}

export function useConversationHistoryContext() {
  const context = useContext(ConversationHistoryContext);
  if (!context) {
    throw new Error('useConversationHistoryContext must be used within ConversationHistoryProvider');
  }
  return context;
}
```

---

## 8. CONVERSATION HISTORY HOOK

**File:** `/home/jason/Desktop/adcl/adcl2/demo-sandbox/frontend/src/hooks/useConversationHistory.js`

**Size:** 338 lines

**Responsibilities:**
- Manages current session state
- Lists and loads sessions
- Appends messages to sessions
- Searches conversations
- Creates new sessions with smart title generation

**Key Functions:**

```javascript
// Load list of sessions
const loadSessions = useCallback(async () => {
  const response = await axios.post(`${HISTORY_MCP_URL}/mcp/call_tool`, {
    tool: 'list_sessions',
    arguments: { limit: 50, status: 'active' }
  });
  const result = JSON.parse(response.data.content[0].text);
  setSessions(result.sessions || []);
}, []);

// Create new session with smart title from first message
const createSession = useCallback(async (title = null, metadata = {}) => {
  if (sessionCreationInProgress.current) return null;
  
  sessionCreationInProgress.current = true;
  const response = await axios.post(`${HISTORY_MCP_URL}/mcp/call_tool`, {
    tool: 'create_session',
    arguments: { title, metadata }
  });
  
  const result = JSON.parse(response.data.content[0].text);
  if (result.success) {
    currentSessionIdRef.current = result.session_id;
    setCurrentSessionId(result.session_id);
    setMessages([]);
    await loadSessions();
    return result.session_id;
  }
}, [loadSessions]);

// Load messages from a session
const loadSession = useCallback(async (sessionId) => {
  const response = await axios.post(`${HISTORY_MCP_URL}/mcp/call_tool`, {
    tool: 'get_messages',
    arguments: { session_id: sessionId, limit: 100, reverse: false }
  });
  
  const result = JSON.parse(response.data.content[0].text);
  if (result.success) {
    const loadedMessages = (result.messages || []).map(msg => ({
      id: msg.id,
      role: msg.type,
      content: msg.content,
      timestamp: msg.timestamp,
      metadata: msg.metadata || {}
    }));
    setMessages(loadedMessages);
    setCurrentSessionId(sessionId);
  }
}, []);

// Append message (auto-creates session if needed)
const appendMessage = useCallback(async (message) => {
  let sessionId = currentSessionIdRef.current || currentSessionId;
  if (!sessionId) {
    const smartTitle = message.role === 'user' && message.content
      ? sanitizeTitle(message.content)
      : null;
    sessionId = await createSession(smartTitle);
  }
  
  // Add to UI immediately
  setMessages(prev => [...prev, uiMessage]);
  
  // Persist to history in background
  await axios.post(`${HISTORY_MCP_URL}/mcp/call_tool`, {
    tool: 'append_message',
    arguments: {
      session_id: sessionId,
      message_type: message.role,
      content: message.content,
      metadata: message.metadata
    }
  });
}, [currentSessionId, createSession, loadSessions]);

// Search messages across all conversations
const searchMessages = useCallback(async (query) => {
  const response = await axios.post(`${HISTORY_MCP_URL}/mcp/call_tool`, {
    tool: 'search_messages',
    arguments: { query, limit: 100 }
  });
  const result = JSON.parse(response.data.content[0].text);
  return result.success ? result.results : [];
}, []);
```

---

## 9. HISTORY PAGE

**File:** `/home/jason/Desktop/adcl/adcl2/demo-sandbox/frontend/src/pages/HistoryPage.jsx`

**Size:** 7 KB

**Features:**
- List all conversations with:
  - Title
  - Message count
  - Creation date
  - Status badge
- Search conversations by title or message content
- Pagination (20 per page)
- Click to load conversation

**Key State:**
```javascript
const { sessions, loadSessions, loadSession, searchMessages } = useConversationHistoryContext();
const [searchQuery, setSearchQuery] = useState('');
const [filteredSessions, setFilteredSessions] = useState([]);
const [currentPage, setCurrentPage] = useState(1);
```

---

## 10. USER SETTINGS COMPONENT

**File:** `/home/jason/Desktop/adcl/adcl2/demo-sandbox/frontend/src/components/UserSettings.jsx`

**Size:** 200 lines

**Settings Available:**
- **Theme:** Light/Dark/System
- **Log Level:** Error/Info/Debug
- **MCP Timeout:** 30s/60s/120s
- **Auto-save Drafts:** Toggle
- **Clear History:** Destructive action button

**Backend Integration:**
- GET `/api/settings` - Load user settings
- POST `/api/settings` - Update individual settings

---

## 11. NAVIGATION COMPONENT

**File:** `/home/jason/Desktop/adcl/adcl2/demo-sandbox/frontend/src/components/Navigation.jsx`

**Left Sidebar Navigation with:**
- Main page links (Playground, Models, MCPs, Teams, Agents, Registry, Workflows, Triggers)
- Recent conversations submenu
- Theme toggle button
- Conversation search/filtering

---

## 12. EXECUTION CONTROL

### WebSocket Connection Management

```javascript
const ws = new WebSocket(`${WS_URL}/ws/chat/${sessionIdRef.current}`);
wsRef.current = ws;

ws.onopen = () => {
  ws.send(JSON.stringify({
    team_id: selectedTeam?.id || 'default',
    message: messageContent
  }));
};

ws.onmessage = async (event) => {
  const data = JSON.parse(event.data);
  // Process streaming updates...
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  if (wsRef.current === ws) {
    wsRef.current = null;
  }
};
```

### Stop Execution

```javascript
const stopExecution = async () => {
  executionCancelled.current = true;  // Prevent processing in-flight messages
  
  // Notify backend
  if (wsRef.current?.readyState === WebSocket.OPEN) {
    wsRef.current.send(JSON.stringify({
      type: 'cancel_execution',
      execution_id: executionId
    }));
  }
  
  // Close WebSocket
  wsRef.current?.close();
  wsRef.current = null;
  
  // Reset state
  setLoading(false);
  setStreamingStatus(null);
  
  // Add cancellation message
  await appendMessage({
    id: crypto.randomUUID(),
    role: 'agent-status',
    content: 'Execution cancelled by user.',
    timestamp: new Date().toISOString(),
    metadata: { type: 'cancelled' }
  });
};
```

---

## 13. API ENDPOINTS USED

### Chat/Execution APIs
- `POST /chat` - HTTP fallback for simple responses
- `WebSocket /ws/chat/{sessionId}` - Streaming agent execution

### Team Management
- `GET /teams` - List available teams

### History MCP APIs
- `POST /mcp/call_tool` - Generic MCP tool invocation with:
  - `tool: 'list_sessions'`
  - `tool: 'create_session'`
  - `tool: 'get_messages'`
  - `tool: 'append_message'`
  - `tool: 'search_messages'`
  - `tool: 'search_titles'`

### Settings
- `GET /api/settings`
- `POST /api/settings`

---

## 14. KEY TECHNICAL DETAILS

### Token Calculation Method

Tokens are summed from individual iterations during agent execution:

```javascript
// Per iteration: data.token_usage = {input_tokens: N, output_tokens: M}
// Aggregated by iterating through agentActivityLog
totalTokensIn += activity.metadata.token_usage.input_tokens || 0
totalTokensOut += activity.metadata.token_usage.output_tokens || 0
totalTokens = totalTokensIn + totalTokensOut
```

### Message Persistence Strategy

- **Immediate:** Messages added to local state for responsive UI
- **Background:** Persisted to History MCP server asynchronously
- **Auto-creates:** Session created on first message with smart title from message content
- **Handles offline:** If History MCP unavailable, user can continue but history won't persist

### Cancellation Safety

Race condition prevention:
```javascript
executionCancelled.current = true  // Flag set before closing
// Check flag in onmessage handler before processing
if (executionCancelled.current) return;
```

### Color Coding

Agent messages get consistent colors based on hash of agent ID:

```javascript
const getAgentColor = (agentId) => {
  const colors = ['blue', 'green', 'purple', 'orange', 'pink', 'cyan', 'indigo', 'teal'];
  let hash = agentId.length;
  for (let i = 0; i < agentId.length; i++) {
    hash = (hash * 31 + agentId.charCodeAt(i)) | 0;
  }
  return colors[Math.abs(hash) % colors.length];
};
```

---

## 15. METADATA STORAGE IN MESSAGES

Each message can carry rich metadata stored in `message.metadata`:

```javascript
{
  // Agent information
  agent_id: string,
  agent_role: string,
  agent_color: string,
  
  // Execution metrics
  token_usage: { input_tokens, output_tokens },
  iteration: number,
  max_iterations: number,
  model: string,
  stop_reason: string,
  
  // Tool usage
  tools_used: Array<{ name, summary }>,
  tool_name: string,
  tool_summary: string,
  
  // Reasoning
  thinking_preview: string,
  thinking: string,
  
  // Status flags
  type: 'status' | 'agent_start' | 'agent_iteration' | 'tool_execution' | 'agent_complete' | 'execution_started',
  persist: boolean,
  
  // Custom user data
  [key: string]: any
}
```

---

## Summary

The ADCL playground is a sophisticated React-based chat interface that:

1. **Displays conversations** with multi-agent execution tracking
2. **Streams real-time updates** via WebSocket for responsive feedback
3. **Tracks token usage** at iteration level and aggregates for summary display
4. **Persists all data** to a History MCP backend with smart session creation
5. **Manages execution** with cancellation support and detailed activity logging
6. **Colorizes agent messages** for visual distinction between team members
7. **Shows rich metadata** including tokens, iterations, tools, and reasoning

The architecture cleanly separates concerns between UI (PlaygroundPage), state management (ConversationHistoryContext), and persistence (History MCP), following ADCL's Unix philosophy principles.
