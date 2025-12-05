# Playground UI Implementation - Executive Summary

## Overview

The ADCL Playground is a React-based chat interface that enables real-time multi-agent team execution with comprehensive token tracking, conversation persistence, and execution monitoring.

**Key Metrics:**
- Main Component: 935 lines (PlaygroundPage.jsx)
- State Management: Context + Hook pattern
- Backend Integration: WebSocket + HTTP + MCP
- Message Persistence: History MCP Server (port 7004)
- Token Tracking: Per-iteration aggregation with UI display

---

## Architecture

### Three-Layer Design

```
┌─────────────────────────────────────────────┐
│         UI Layer (React Components)          │
│  PlaygroundPage + Navigation + UserSettings  │
└────────────┬────────────────────────────────┘
             │ Uses
┌────────────▼────────────────────────────────┐
│    State Management Layer (Context/Hook)     │
│  ConversationHistoryContext                  │
│  useConversationHistory Hook                 │
└────────────┬────────────────────────────────┘
             │ Communicates via HTTP
┌────────────▼────────────────────────────────┐
│      Backend Services                        │
│  - History MCP (persistence)                 │
│  - WebSocket API (streaming)                 │
│  - Team API (configuration)                  │
└─────────────────────────────────────────────┘
```

### Data Flow Pattern

```
User Input → Message → Session Creation → Persistence → Display
                 ↓
            WebSocket
                 ↓
         Streaming Updates → Aggregation → Summary
```

---

## Feature Breakdown

### 1. Real-Time Chat Interface
- **Component:** PlaygroundPage.jsx (lines 654-934)
- **Rendering:** React ScrollArea with message bubbles
- **Message Types:** User, Assistant, Agent Status, Error
- **Auto-scroll:** Smooth scroll to latest message

### 2. Team/Agent Management
- **Team Selection:** Dropdown modal (lines 903-931)
- **Agent Count:** Display in header
- **Team Switching:** Mid-conversation support
- **MCP Detection:** Fallback to HTTP if no MCPs

### 3. Conversation Persistence
- **Storage:** History MCP Server (port 7004)
- **Smart Titles:** Auto-generated from first message
- **Session Tracking:** UUID-based session IDs
- **Search:** Full-text message and title search
- **History Page:** Browse and reload past conversations

### 4. Execution Control
- **Start:** WebSocket connection with team_id
- **Stop:** Cancellation flag + WebSocket close
- **Streaming:** Real-time status updates
- **Timeout:** Configurable in settings
- **Error Handling:** Graceful degradation

### 5. Token Tracking
- **Collection:** Per-iteration from WebSocket events
- **Aggregation:** Sum input + output tokens
- **Display:** 
  - Inline in message metadata (lines 750-755)
  - Summary bar at bottom (lines 849-850)
- **Metrics:** Tokens In, Tokens Out, Total

### 6. Agent Status Visualization
- **Color Coding:** Based on agent ID hash (8 colors)
- **Activity Log:** Collapsible details per message
- **Progress:** Real-time iteration tracking
- **Tools:** Show MCP tools being used

---

## Key Implementation Details

### Message Data Structure

```javascript
Message {
  id: string (UUID),
  role: 'user' | 'assistant' | 'error' | 'agent-status',
  content: string,
  timestamp: string (ISO 8601),
  metadata: {
    // Token tracking
    token_usage?: { input_tokens, output_tokens }
    // Execution metrics
    iteration?: number,
    max_iterations?: number,
    model?: string,
    // Agent identification
    agent_id?: string,
    agent_role?: string,
    agent_color?: string,
    // Tools used
    tools_used?: Array<{ name, summary }>,
    // Control
    persist?: boolean,
    type?: string
  }
}
```

### Token Calculation Algorithm

```javascript
// Collection Phase
for each 'agent_iteration' event:
  agentActivityLog.push({
    metadata: { token_usage: event.token_usage }
  })

// Aggregation Phase (on 'complete' event)
let totalIn = 0, totalOut = 0
agentActivityLog.forEach(activity => {
  totalIn += activity.metadata?.token_usage?.input_tokens || 0
  totalOut += activity.metadata?.token_usage?.output_tokens || 0
})

// Display Phase
setLastExecutionSummary({
  tokens: totalIn + totalOut,
  tokensIn: totalIn,
  tokensOut: totalOut
})
```

### Session Creation Logic

```javascript
// Smart title generation
const smartTitle = message.role === 'user' && message.content
  ? sanitizeTitle(message.content)  // Truncate at 60 chars
  : null

// Session creation on first message
if (!currentSessionId) {
  sessionId = await createSession(smartTitle)
}

// Idempotent append
const uiMessage = { ...message }
setMessages(prev => [...prev, uiMessage])  // Immediate
await persistToHistory(uiMessage)            // Background
```

---

## Component Interaction Map

```
App.jsx (Provider wrapper)
  ├─ ConversationHistoryProvider
  │   └─ PlaygroundPage
  │       ├─ Header
  │       │   ├─ Team Selector
  │       │   ├─ New Chat Button
  │       │   └─ UserSettings
  │       ├─ Messages Area
  │       │   ├─ Message Bubbles
  │       │   ├─ Status Messages
  │       │   └─ Error Messages
  │       ├─ Execution Summary Bar
  │       └─ Input Area
  │           ├─ Textarea
  │           └─ Send/Stop Button
  ├─ Navigation (uses same Context)
  │   ├─ Page Links
  │   └─ Recent Sessions
  └─ HistoryPage (from Navigation)
      ├─ Session List
      ├─ Search Bar
      └─ Pagination
```

---

## API Integration Points

### WebSocket Event Flow

```
User sends message
  ↓
ws.open() sends {team_id, message}
  ↓
Backend responds with streaming events
  ↓
[execution_started]
  → setExecutionId()
  → executionStartTime = now()
  ↓
[agent_iteration]
  → collect token_usage in agentActivityLog
  → display inline metrics
  ↓
[agent_complete]
  → save agentActivity to message
  ↓
[complete]
  → aggregate all metrics
  → set lastExecutionSummary
  → close WebSocket
```

### History MCP Persistence

```
Message to persist
  ↓
POST /mcp/call_tool {
  tool: 'append_message',
  arguments: {
    session_id,
    message_type: message.role,
    content: message.content,
    metadata: message.metadata
  }
}
  ↓
History MCP Server processes
  ↓
Returns: { success: true, message_id }
```

---

## State Management Strategy

### Context Responsibility
- **Sessions list:** All conversations
- **Current session ID:** Active session
- **Messages array:** All messages in current session
- **Initialization flag:** Bootstrap state

### Component Responsibility
- **Input text:** Textarea content
- **Team selection:** Current team
- **Loading state:** Execution status
- **Streaming status:** Real-time updates
- **Execution summary:** Last run metrics

### Ref Responsibility
- **WebSocket ref:** Connection instance
- **Session ID ref:** Immediate access (race condition prevention)
- **Execution time ref:** Start timestamp
- **Cancellation flag:** Prevents race conditions

### Division of Concerns

| Concern | Location | Why |
|---------|----------|-----|
| Session persistence | History MCP | Survives app reloads |
| Message display | Local state | Fast UI updates |
| WebSocket | Refs | No re-renders needed |
| User input | Component state | Local only |
| Execution metrics | Component state | Temporary, last run only |

---

## Token Tracking Deep Dive

### Where Tokens Come From
1. **WebSocket Event:** `data.type === 'agent_iteration'`
2. **Contains:** `data.token_usage = {input_tokens: N, output_tokens: M}`
3. **Per Agent:** Each agent sends tokens for each iteration

### How They're Aggregated
1. **Storage:** Each iteration stored in `agentActivityLog` with metadata
2. **Aggregation:** On 'complete' event, sum all tokens across all iterations
3. **Safety:** Handle missing/null values with `|| 0` defaults

### Where They're Displayed
1. **Inline:** In message bubble under agent-status messages
2. **Summary:** Execution summary bar at bottom of chat
3. **Format:** Localized numbers with thousand separators

### Edge Cases Handled
```javascript
// Missing token_usage
activity.metadata?.token_usage?.input_tokens || 0

// Multiple agents
Set(agentIds) to deduplicate and count

// No activity
Check agentActivityLog.length before displaying

// Execution failed
Agent results checked for status === 'error'
```

---

## Execution Control Safety

### Race Condition Prevention

```javascript
// Problem: User can cancel while new message is being sent
// Solution: Cancellation flag

executionCancelled.current = true  // Set FIRST
if (wsRef.current?.readyState === WebSocket.OPEN) {
  wsRef.current.send({...})
}
wsRef.current?.close()

// In onmessage handler:
if (executionCancelled.current) return  // Check early
```

### Session Creation Race Condition

```javascript
// Problem: Multiple appendMessage calls could create multiple sessions
// Solution: In-progress flag

if (sessionCreationInProgress.current) return null
sessionCreationInProgress.current = true
try {
  // Create session...
} finally {
  sessionCreationInProgress.current = false
}
```

---

## Performance Considerations

### Optimization Strategies

1. **Immediate UI Updates**
   - Messages added to state before persistence
   - User sees response instantly
   - Backend save happens in background

2. **Lazy Session Creation**
   - Don't create until first message
   - Use smart title generation
   - Avoid empty sessions

3. **Metadata Filtering**
   - Don't persist transient status messages
   - Use `persist` flag in metadata
   - Save only meaningful milestones

4. **Message Pagination**
   - History page: 20 per page
   - Limits backend load
   - Smooth pagination UX

### Potential Bottlenecks

- **WebSocket bandwidth:** Many agents = many events
- **Token aggregation:** Large histories slow down calculation
- **Message rendering:** ScrollArea virtualizes for efficiency
- **Search performance:** Full-text search on History MCP

---

## Error Handling Strategy

### Recovery Mechanisms

```javascript
// History MCP unavailable?
catch (err) {
  console.warn('[History] Failed to load sessions');
  // Continue - history optional, don't block chat
}

// WebSocket timeout?
ws.onerror = () => reject(error)
// User sees error message, can retry

// Partial execution failure?
if (agentErrors.length > 0) {
  // Treat as error, show details
  // Suggest retry
}

// Cancellation race condition?
if (executionCancelled.current) return
// Skip processing in-flight messages
```

### User-Facing Messages

- **Execution started:** "Starting to work on your request..."
- **Agent working:** "[Agent Name] is thinking..."
- **Tools running:** "[Agent Name] is using: tool_summary"
- **Agent done:** "[Agent Name] has finished: answer_preview"
- **Cancelled:** "Execution cancelled by user."
- **Error:** Shows specific error with details

---

## Testing Approach

### Unit Tests
- Message creation and formatting
- Token aggregation logic
- Session creation with smart titles
- Color generation from agent IDs

### Integration Tests
- Full chat flow: send → stream → complete
- Persistence: append → load → verify
- Navigation: history browsing → session load
- Error handling: cancellation, timeouts, failures

### Test Files
```
frontend/src/pages/__tests__/
  ├─ PlaygroundPage.test.jsx
  ├─ HistoryPage.test.jsx
components/__tests__/
  └─ Navigation.test.jsx
```

---

## Future Enhancement Ideas

1. **Token Budget**
   - Track tokens against API budget
   - Warn when approaching limit
   - Auto-pause expensive operations

2. **Rich Metadata Export**
   - Download execution trace as JSON
   - Export conversation as PDF
   - Share execution results

3. **Advanced Search**
   - Filter by agent, date range, token cost
   - Tag conversations manually
   - Saved searches/filters

4. **Execution Replay**
   - Step through execution events
   - View tool I/O details
   - Compare executions side-by-side

5. **Performance Analytics**
   - Token cost over time
   - Agent efficiency metrics
   - Tool hit rates

---

## Compliance with ADCL Principles

### Unix Philosophy
✓ Do one thing well - Playground focuses on chat UI
✓ Text-based configuration - Settings in JSON
✓ Compose tools - Integrates History MCP, Team API
✓ Text streams - WebSocket events are text JSON

### Configuration is Code
✓ All settings inspectable (user.conf via API)
✓ Hot-reloadable (UI settings immediate)
✓ No binary configs
✓ No hidden state

### Modularity
✓ Each hook/component independent
✓ Communication via props/context only
✓ No cross-service imports
✓ Clean separation of concerns

### Error Handling
✓ Fail fast (cancellation immediate)
✓ Fail loudly (errors displayed to user)
✓ Meaningful error messages
✓ Graceful degradation (History MCP optional)

---

## Summary

The ADCL Playground is a well-architected React chat interface that demonstrates:

1. **Sophisticated State Management** - Context + Hook pattern for scalability
2. **Real-Time Streaming** - WebSocket integration with fallback
3. **Comprehensive Persistence** - Session management with smart features
4. **Rich Metrics Tracking** - Token counting at iteration level
5. **Safety First** - Race condition prevention throughout
6. **User-Centric Design** - Responsive, informative, actionable UI

The implementation balances immediate responsiveness (local state) with data durability (async persistence) while maintaining clean separation between UI concerns, state management, and backend integration.

