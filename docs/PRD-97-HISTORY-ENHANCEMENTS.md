# PRD-97: Playground History UI/UX Enhancements

**Issue:** PRD-97 - Playground History UI/UX Improvements
**Created:** 2025-11-13
**Status:** ✅ P0 Complete | ✅ P1 Complete | P2 Pending
**Priority:** P1 (High)

---

## Overview

Improve the Playground conversation history system with better UX, performance optimizations, and architectural cleanup. This addresses critical UX issues and technical debt identified during bug fixes.

**What was completed:**
- ✅ Fixed sidebar history clicks not updating main view (Context Provider)
- ✅ Fixed "Invalid Date" display bug (field name mismatch)
- ✅ Filtered empty conversations from display
- ✅ **P0:** Smart title generation from first user message
- ✅ **P0:** Removed localStorage (ADCL compliance)
- ✅ **P0:** Pagination (20 per page with bounds checking)
- ✅ **P1:** CSS-based truncation (replaced JS substring)
- ✅ **P1:** Content-based message search (backend + frontend)
- ✅ **P1:** Auto-cleanup empty sessions (method + tool + script)
- ✅ **CRITICAL:** Fixed race condition where agent output didn't appear

**What remains:**
2 P2 (nice-to-have) enhancement tasks.

---

## Problem Statement

### User Pain Points

1. **Poor Conversation Titles** - Auto-generated titles are timestamps like "Conversation 11/11/2025, 2:15:18 AM" with no context
2. **Truncation Hides Context** - 60 char limit still cuts off important information
3. **No Search** - Can't search actual conversation content, only titles
4. **No Organization** - Flat list of all conversations with no grouping
5. **Performance Risk** - Loading all conversations at once (currently 35, could be 5000+)
6. **localStorage Pollution** - Hidden state violates ADCL principles
7. **Empty Session Clutter** - 0-message sessions still created and stored

### Business Impact

- **User Frustration** - Can't find past conversations easily
- **Performance Degradation** - App will slow down as history grows
- **ADCL Violation** - Hidden state in localStorage breaks "everything in files" principle

---

## Requirements

### P0 (Critical - Must Have)

#### 1. Smart Title Generation
**User Story:** As a user, I want meaningful conversation titles so I can identify conversations at a glance.

**Current:** "Conversation 11/11/2025, 2:15:18 AM"
**Desired:** "Debugging authentication issue with JWT tokens"

**Implementation:**
- Use first user message (first 60 chars) as title
- Fall back to timestamp only if message is empty/unavailable
- Backend should store preview on session creation

**Acceptance Criteria:**
- [x] New conversations show first user message as title
- [x] Existing conversations maintain their current titles
- [x] Titles are readable in both sidebar (60 chars) and full page
- [x] No title longer than 60 characters in sidebar

---

#### 2. Remove localStorage Usage
**User Story:** As a developer, I want history data in files only, following ADCL principles.

**Current:** Falls back to localStorage on MCP server errors
**Desired:** Fail gracefully and show error, never hide state

**Implementation:**
- Remove lines 31-46, 106-110, 158-162, 218-220 in `useConversationHistory.js`
- Show error toast when history MCP unavailable
- Don't create sessions when MCP is down

**Acceptance Criteria:**
- [x] No localStorage.setItem() calls in history hook
- [x] No localStorage.getItem() calls in history hook
- [x] Error displayed to user when MCP unavailable
- [x] Application remains functional (just can't save history)

**Files:**
- `frontend/src/hooks/useConversationHistory.js`

---

#### 3. Pagination in HistoryPage
**User Story:** As a user with hundreds of conversations, I want fast page load and smooth scrolling.

**Current:** Loads all sessions at once (performance risk)
**Desired:** 20 conversations per page with prev/next buttons

**Implementation:**
- Add state: `const [page, setPage] = useState(0)`
- Slice: `filteredSessions.slice(page * 20, (page + 1) * 20)`
- Add pagination controls with page numbers

**Acceptance Criteria:**
- [x] Only 20 conversations rendered at once
- [x] Previous/Next buttons work correctly
- [x] Page number indicator (e.g., "Page 2 of 5")
- [x] Fast performance with 1000+ conversations

**Files:**
- `frontend/src/pages/HistoryPage.jsx`

---

### P1 (High Priority - Should Have)

#### 4. CSS-Based Truncation
**User Story:** As a developer, I want clean CSS-based truncation instead of JavaScript string manipulation.

**Current:** JavaScript substring + "..." concatenation
**Desired:** CSS `text-overflow: ellipsis`

**Implementation:**
- Replace `session.preview.substring(0, 60) + '...'` with CSS
- Apply `.truncate` class with `overflow: hidden; text-overflow: ellipsis; white-space: nowrap;`

**Acceptance Criteria:**
- [x] No hardcoded character limits in JavaScript
- [x] Ellipsis appears automatically when text overflows
- [x] Tooltip shows full text on hover

**Files:**
- `frontend/src/components/Navigation.jsx` (lines 91-95)

---

#### 5. Content-Based Search
**User Story:** As a user, I want to search conversation content, not just titles.

**Current:** Searches only session.title
**Desired:** Searches message content via backend API

**Implementation:**
- Add search endpoint to history MCP: `search_conversations(query)`
- Backend searches message content in session files
- Frontend displays matched conversations with snippets

**Acceptance Criteria:**
- [x] Typing in search box queries message content
- [x] Results highlight matched snippets
- [x] Search is fast (< 500ms for 1000 conversations)
- [x] Empty search shows all conversations

**Files:**
- `frontend/src/pages/HistoryPage.jsx`
- `mcp_servers/history/server.py` (new endpoint)

---

#### 6. Auto-Cleanup Empty Sessions
**User Story:** As a user, I don't want to see empty conversation placeholders cluttering my history.

**Current:** Empty sessions (0 messages) are created and saved
**Desired:** Only save sessions when first message added

**Implementation:**
- Don't create session until first message
- Backend cleanup job removes sessions with 0 messages older than 1 hour
- Add cleanup script: `scripts/cleanup-history.sh`

**Acceptance Criteria:**
- [x] New chats don't create session until user sends first message
- [x] Existing empty sessions removed by cleanup script
- [x] Cleanup runs on platform startup
- [x] No 0-message sessions in HistoryPage

**Files:**
- `frontend/src/hooks/useConversationHistory.js` (defer session creation)
- `mcp_servers/history/server.py` (cleanup method)
- `scripts/cleanup-history.sh` (new script)

---

### P2 (Medium Priority - Nice to Have)

#### 7. Conversation Grouping by Date
**User Story:** As a user, I want conversations organized by recency for easier browsing.

**Current:** Flat list sorted by updated date
**Desired:** Grouped sections: Today, Yesterday, Last Week, Older

**Implementation:**
```jsx
const groupedSessions = {
  today: [],
  yesterday: [],
  lastWeek: [],
  older: []
};
// Group logic based on session.updated timestamp
```

**Acceptance Criteria:**
- [ ] Conversations grouped under date headers
- [ ] Groups are collapsible
- [ ] Counts shown for each group (e.g., "Today (5)")

**Files:**
- `frontend/src/pages/HistoryPage.jsx`

---

#### 8. Hover Preview
**User Story:** As a user, I want to peek at conversation content without clicking.

**Current:** Must click to see conversation
**Desired:** Hover shows first 2-3 messages in tooltip/popover

**Implementation:**
- Use Shadcn Popover component
- Load preview on hover (debounced 300ms)
- Show first 3 messages only

**Acceptance Criteria:**
- [ ] Hovering session shows preview popover
- [ ] Preview loads within 300ms
- [ ] Preview shows first 3 messages
- [ ] Clicking loads full conversation

**Files:**
- `frontend/src/pages/HistoryPage.jsx`
- `frontend/src/components/Navigation.jsx`

---

## Technical Approach

### Phase 1: Critical Fixes (P0) - 1-2 days

**Tasks:**
1. Smart title generation (2-3 hours)
2. Remove localStorage (1-2 hours)
3. Pagination in HistoryPage (2-3 hours)

**Validation:**
- Unit tests for title generation
- Manual testing of pagination
- Verify no localStorage usage

---

### Phase 2: UX Improvements (P1) - 2-3 days

**Tasks:**
4. CSS-based truncation (1 hour)
5. Content-based search (4-5 hours - backend + frontend)
6. Auto-cleanup empty sessions (2-3 hours)

**Validation:**
- Search performance testing
- Cleanup script execution
- Manual UX testing

---

### Phase 3: Polish (P2) - 1-2 days

**Tasks:**
7. Conversation grouping by date (2-3 hours)
8. Hover preview (2-3 hours)

**Validation:**
- User acceptance testing
- Performance benchmarks

---

## Success Metrics

**Before:**
- 35 total conversations (many empty)
- Meaningless timestamp titles
- No search or grouping
- Performance unknown with large history

**After:**
- Only conversations with messages shown
- Smart, readable titles
- Full-text search under 500ms
- Fast pagination with 1000+ conversations
- No localStorage (ADCL compliant)
- Organized by date with previews

---

## Dependencies

- History MCP Server (`mcp_servers/history/`)
- Conversation History Hook (`frontend/src/hooks/useConversationHistory.js`)
- Shadcn UI components (Popover, Pagination)

---

## Risks & Mitigations

**Risk:** Backend search performance with large conversation sets
**Mitigation:** Implement full-text search index in history MCP

**Risk:** Breaking existing history functionality
**Mitigation:** Comprehensive testing, feature flags for new features

**Risk:** User confusion with title changes
**Mitigation:** Only apply to new conversations, keep existing titles

---

## Agent Reviews Required

Per CLAUDE.md, run these agents after implementation:

1. **linus-torvalds** - Architectural review for ADCL compliance
2. **code-nitpicker-9000** - QA review for test coverage and linting

---

## Timeline

**Week 1:**
- Phase 1: Critical fixes (P0)
- Phase 2: UX improvements (P1)

**Week 2:**
- Phase 3: Polish (P2)
- Testing and agent reviews
- Documentation updates

**Total:** 1-2 weeks

---

## Next Steps

1. Review and approve this PRD
2. Create branch `PRD-97-HISTORY-ENHANCEMENTS`
3. Implement Phase 1 (P0 tasks)
4. Run agent reviews
5. Merge and deploy
6. Repeat for Phases 2 & 3

---

## References

- Original bug report: Sidebar history clicks not working
- Agent feedback: Linus Torvalds architectural review
- Agent feedback: Steve Jobs UI/UX critique
- ADCL Principles: CLAUDE.md
