# PRD-45: Memory UI Cleanup - Implementation Plan

**Issue**: Cleanup the Memory UI to make it less busy and cleaner
**Branch**: `prd-45`
**Status**: Planning

## Problem Statement

The current Playground page has a persistent chat history sidebar that makes the UI feel cluttered and busy. The sidebar takes up valuable screen space and displays too much information at once.

## Proposed Solution

Move chat history from a persistent sidebar to a navigation submenu, and create a dedicated History page for full conversation management.

## Design Changes

### 1. Remove History Sidebar from Playground
**File**: `frontend/src/pages/PlaygroundPage.jsx`

**Changes**:
- Remove the left sidebar containing chat history
- Remove `showHistorySidebar` state and toggle logic
- Remove sidebar toggle buttons from header
- Make chat area full-width
- Keep the "New chat" functionality accessible via header button

**Impact**: Cleaner, more focused chat interface similar to modern chat applications

### 2. Add History Submenu to Navigation
**File**: `frontend/src/components/Navigation.jsx`

**Changes**:
- Add expandable submenu under "Playground" navigation item
- Display 10 most recently accessed conversations
- Add "View All History" link at bottom of submenu
- Use collapsible component for expand/collapse behavior
- Show conversation titles only (no message counts or timestamps in submenu)

**UI Structure**:
```
Navigation
├── Playground ▼
│   ├── [Recent Chat 1]
│   ├── [Recent Chat 2]
│   ├── ...
│   ├── [Recent Chat 10]
│   └── View All History →
├── Models
├── MCP Servers
...
```

### 3. Move Team Selector to Header
**File**: `frontend/src/pages/PlaygroundPage.jsx`

**Changes**:
- Remove team selector from bottom of history sidebar
- Add team selector button to top right of header (next to message count badge)
- Keep existing modal/dropdown functionality
- Display selected team name with Users icon

**Header Layout**:
```
[Menu] Playground Title          [Team: Default Agent] [Badge: 5 messages]
```

### 4. Create Dedicated History Page
**File**: `frontend/src/pages/HistoryPage.jsx` (new)

**Features**:
- Full list of all conversations
- Search functionality
- Sort by date/title
- Message count and creation date display
- Click to load conversation (navigates to Playground)
- Refresh button
- Clean card-based layout

**Components Used**:
- Card for main container
- ScrollArea for conversation list
- Input with Search icon for filtering
- Badge for status indicators

### 4. Update App Routing
**File**: `frontend/src/App.jsx`

**Changes**:
- Add 'history' route case
- Import HistoryPage component
- Add navigation handler for history page

### 5. Update Navigation Hook Integration
**File**: `frontend/src/hooks/useConversationHistory.js`

**Changes** (if needed):
- Ensure `loadSessions()` can be called with limit parameter
- Add method to get recent N sessions
- No breaking changes to existing API

## Implementation Steps

1. **Create HistoryPage.jsx**
   - Build full history view with search
   - Test conversation loading
   - Verify navigation to Playground works

2. **Update Navigation.jsx**
   - Add Collapsible component for Playground submenu
   - Integrate with useConversationHistory hook
   - Fetch and display 10 most recent chats
   - Add "View All History" link

3. **Update PlaygroundPage.jsx**
   - Remove sidebar state and UI
   - Remove toggle buttons
   - Move team selector from sidebar to header (top right)
   - Add "New Chat" button to header
   - Adjust layout for full-width chat area

4. **Update App.jsx**
   - Add history route
   - Test navigation flow

5. **Testing**
   - Verify chat history loads in submenu
   - Test clicking recent chats loads them in Playground
   - Test "View All History" navigation
   - Test search on History page
   - Verify new chat creation still works
   - Test responsive behavior

## Files to Modify

- ✅ `docs/PRD-45-MEMORY-UI-CLEANUP.md` (this file)
- ⬜ `frontend/src/pages/HistoryPage.jsx` (new)
- ⬜ `frontend/src/pages/PlaygroundPage.jsx` (modify)
- ⬜ `frontend/src/components/Navigation.jsx` (modify)
- ⬜ `frontend/src/App.jsx` (modify)

## UI/UX Improvements

**Before**:
- Persistent sidebar takes 256px of width
- Always visible even when not needed
- Message counts and metadata add visual noise
- Toggle buttons add complexity
- Team selector hidden at bottom of sidebar

**After**:
- Full-width chat interface
- History accessible via navigation submenu
- Team selector prominent in header (top right)
- Cleaner, more focused chat experience
- Dedicated page for history management
- Reduced visual clutter

## Technical Considerations

1. **State Management**: Navigation component will need access to conversation history hook
2. **Navigation Events**: Use custom events or context to trigger navigation from History page
3. **Performance**: Limit submenu to 10 items to avoid rendering issues
4. **Persistence**: Current session still saved to localStorage
5. **Backwards Compatibility**: No breaking changes to conversation history API

## Success Criteria

- [ ] Chat history sidebar removed from Playground
- [ ] Team selector moved to header (top right, next to message count)
- [ ] Navigation submenu shows 10 recent chats
- [ ] History page displays all conversations with search
- [ ] Clicking recent chat loads it in Playground
- [ ] "New Chat" functionality preserved
- [ ] No regression in conversation persistence
- [ ] UI feels cleaner and less busy

## Future Enhancements (Out of Scope)

- Delete conversations from History page
- Archive/favorite conversations
- Export conversation history
- Conversation tags/categories
- Bulk operations on conversations
