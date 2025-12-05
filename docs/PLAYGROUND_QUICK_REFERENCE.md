# Playground UI - Quick Reference Guide

## File Locations

| Component | Path | Lines | Purpose |
|-----------|------|-------|---------|
| Main Chat | `/frontend/src/pages/PlaygroundPage.jsx` | 935 | Core playground interface |
| History View | `/frontend/src/pages/HistoryPage.jsx` | 188 | Conversation list & search |
| History Hook | `/frontend/src/hooks/useConversationHistory.js` | 338 | Session management & persistence |
| History Context | `/frontend/src/contexts/ConversationHistoryContext.jsx` | 36 | State provider |
| Navigation | `/frontend/src/components/Navigation.jsx` | 200+ | Left sidebar |
| User Settings | `/frontend/src/components/UserSettings.jsx` | 200 | Settings modal |
| App Root | `/frontend/src/App.jsx` | 142 | Entry point & routing |

## Key Components Breakdown

### PlaygroundPage.jsx Structure

```
PlaygroundPage (Main Component)
├── Header (Team selector, New Chat, Settings)
├── Messages Area (ScrollArea with message bubbles)
│   ├── User Messages
│   ├── Assistant Messages
│   ├── Agent Status Messages (colored by agent)
│   └── Error Messages
├── Execution Summary Bar (Token counts, timing, iterations)
└── Input Area (Textarea + Send/Stop button)
```

## State Management

### Local State (PlaygroundPage)
```javascript
input                    // User message input
selectedTeam             // Currently selected team
teams                    // List of available teams
loading                  // WebSocket connection status
streamingStatus          // Current streaming status message
executionId              // Current execution ID
lastExecutionSummary     // Metrics from last execution
```

### Context State (ConversationHistoryContext)
```javascript
currentSessionId         // Active session/conversation ID
sessions                 // List of saved sessions
messages                 // Current conversation messages
initialized              // Context initialization flag
```

### Refs (Non-rendered state)
```javascript
wsRef                    // WebSocket connection reference
sessionIdRef             // Session ID for current execution
executionStartTime       // Start time for execution timing
executionCancelled       // Flag to prevent race conditions
```

## API Endpoints

### Backend APIs
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/teams` | GET | List available teams |
| `/chat` | POST | HTTP fallback chat endpoint |
| `/ws/chat/{sessionId}` | WebSocket | Streaming agent execution |
| `/api/settings` | GET/POST | User settings |

### History MCP Server (Port 7004)
| Tool | Purpose |
|------|---------|
| `create_session` | Create new conversation |
| `get_messages` | Load conversation messages |
| `append_message` | Save message to conversation |
| `list_sessions` | List all conversations |
| `search_messages` | Search message content |
| `search_titles` | Search by conversation title |

## WebSocket Message Types

```javascript
'execution_started'      // Execution begun, includes execution_id
'status'                 // Generic status update
'agent_start'           // Agent begins work
'agent_iteration'       // Agent iteration (contains token_usage)
'tool_execution'        // Tool invoked by agent
'agent_complete'        // Agent finished
'complete'              // Execution complete with results
'error'                 // Error occurred
```

## Message Structure

```javascript
{
  id: string,                 // UUID
  role: 'user|assistant|error|agent-status',
  content: string,
  timestamp: string,          // ISO 8601
  metadata: {
    // Token tracking
    token_usage: {
      input_tokens: number,
      output_tokens: number
    },
    // Execution metrics
    iteration: number,
    max_iterations: number,
    model: string,
    // Agent info
    agent_id: string,
    agent_role: string,
    agent_color: string,
    // Tools
    tools_used: Array,
    // Control flags
    persist: boolean,
    type: string
  }
}
```

## Token Tracking Flow

```
WebSocket 'agent_iteration' event
    ↓ (contains token_usage)
addAgentStatusMessage() with metadata
    ↓
Store in message.metadata
    ↓
Aggregate in agentActivityLog
    ↓
On 'complete' event:
  totalTokensIn += all input tokens
  totalTokensOut += all output tokens
    ↓
setLastExecutionSummary({
  tokens: totalTokensIn + totalTokensOut,
  tokensIn: totalTokensIn,
  tokensOut: totalTokensOut,
  ...
})
    ↓
Display in:
  - Inline message metadata
  - Execution summary bar (bottom)
```

## Data Persistence Flow

```
User sends message
    ↓
appendMessage(userMessage)
    ↓
    ├─→ Check currentSessionId
    ├─→ If null: createSession() (smart title)
    ├─→ Add to local messages state (immediate)
    └─→ POST to History MCP (async)
         tool: 'append_message'
         arguments: {
           session_id,
           message_type: role,
           content,
           metadata
         }
         ↓
History MCP Server
    ↓
Persisted to backend storage
```

## Execution Control

### Starting Execution
1. User types message and clicks Send
2. Check if execution already running (cancel if yes)
3. Create userMessage with UUID
4. Call appendMessage() (persists + updates state)
5. Open WebSocket: `/ws/chat/{sessionId}`
6. Send: `{team_id, message}`
7. Listen for streaming updates

### Stopping Execution
1. User clicks Stop button
2. Set `executionCancelled.current = true`
3. Send cancellation message to backend
4. Close WebSocket connection
5. Reset loading state
6. Add cancellation status message

## Component Integration Points

### PlaygroundPage ↔ ConversationHistoryContext
- Uses: `appendMessage()`, `loadSession()`, `setCurrentSessionId()`
- Provides: User messages, assistant responses, status updates

### PlaygroundPage ↔ Navigation
- Shared Context: ConversationHistoryContext
- Navigation shows recent sessions from context
- Clicking session calls `loadSession()`

### PlaygroundPage ↔ UserSettings
- Callback: `onClearHistory` → triggers `clearAllHistory()`
- Settings: Theme, Log Level, Timeout (backend APIs)

## Token Display Locations

### 1. Inline Metadata (Message Level)
```
Location: Lines 747-777 of PlaygroundPage.jsx
Shown in: Each agent-status message bubble
Format: "Tokens: X in / Y out | Model: Z | Iteration: A/B"
```

### 2. Execution Summary Bar
```
Location: Lines 835-862 of PlaygroundPage.jsx
Position: Bottom of chat, above input area
Shows: Agents, Iterations, Time, Total Tokens
Update: Set on 'complete' event
```

## Common Patterns

### Creating Status Messages
```javascript
const statusMessage = {
  id: crypto.randomUUID(),
  role: 'agent-status',
  content: 'User readable message',
  timestamp: new Date().toISOString(),
  metadata: {
    type: 'status_type',
    token_usage: { input_tokens: X, output_tokens: Y },
    persist: true  // Save to history
  }
};
await addAgentStatusMessage(statusMessage.content, statusMessage.metadata);
```

### Aggregating Execution Metrics
```javascript
let totalTokensIn = 0;
let totalTokensOut = 0;

agentActivityLog.forEach(activity => {
  if (activity.metadata?.token_usage) {
    totalTokensIn += activity.metadata.token_usage.input_tokens || 0;
    totalTokensOut += activity.metadata.token_usage.output_tokens || 0;
  }
});

setLastExecutionSummary({
  tokens: totalTokensIn + totalTokensOut,
  tokensIn: totalTokensIn,
  tokensOut: totalTokensOut,
  time: executionTime,
  agentCount: uniqueAgents.size,
  iterations: maxIteration
});
```

### Safe WebSocket Cancellation
```javascript
executionCancelled.current = true;  // Set flag first

if (wsRef.current?.readyState === WebSocket.OPEN) {
  wsRef.current.send(JSON.stringify({
    type: 'cancel_execution',
    execution_id: executionId
  }));
}

wsRef.current?.close();
wsRef.current = null;
```

## Environment Variables

```bash
VITE_API_URL              # Backend API URL (default: http://localhost:8000)
VITE_HISTORY_MCP_URL      # History MCP server (default: http://localhost:7004)
```

## Color System

Agent messages automatically colored by agent ID hash:
```javascript
colors = ['blue', 'green', 'purple', 'orange', 'pink', 'cyan', 'indigo', 'teal']
colorIndex = hash(agentId) % colors.length
```

Each color has three CSS classes:
- `.avatar` - Background for agent icon
- `.icon` - Color for icon
- `.bubble` - Message bubble styling

## Dependencies

- React 18+
- axios - HTTP client
- next-themes - Theme management
- shadcn/ui - UI components
- lucide-react - Icons
- sonner - Toast notifications
- Tailwind CSS - Styling

## Testing Files

- `/frontend/src/pages/__tests__/PlaygroundPage.test.jsx`
- `/frontend/src/pages/__tests__/HistoryPage.test.jsx`
- `/frontend/src/components/__tests__/Navigation.test.jsx`

## Architecture Principles

1. **Immediate UI Updates** - Messages added to state immediately for responsiveness
2. **Background Persistence** - History saved asynchronously to backend
3. **Race Condition Safe** - Uses refs and flags to prevent concurrent operations
4. **Graceful Degradation** - Continues if history server unavailable
5. **Smart Titles** - Session titles auto-generated from first message
6. **Minimal State** - Only essential data in React state, rest in refs

## Common Issues & Solutions

### Messages not persisting?
- Check VITE_HISTORY_MCP_URL environment variable
- Verify History MCP server is running on port 7004
- Check browser console for axios errors

### WebSocket disconnects?
- Check WS_URL environment variable
- Verify backend WebSocket endpoint is running
- Check network tab for connection failures

### Execution never completes?
- Check if 'complete' message is sent by backend
- Verify token aggregation logic
- Check agentActivityLog population

### Sessions not appearing?
- Verify History MCP is accessible
- Check list_sessions response format
- Ensure sessions have message_count > 0

