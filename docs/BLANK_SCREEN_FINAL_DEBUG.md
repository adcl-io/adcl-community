# Blank Screen on agent.think - Final Debug Guide

## Issue
User reports: "still doing the same bug; run nmap recon and when it gets to agent.think = blank screen on web gui"

## What We've Done So Far

### 1. ✅ Error Boundaries Added
- Added React `ErrorBoundary` component at top level
- Wraps entire App to catch any React rendering errors
- Will show error details instead of blank screen
- Includes "Reload Page" button

### 2. ✅ Try-Catch Wrappers
- `ResultRenderer` wrapped in try-catch
- Results mapping wrapped in try-catch
- WebSocket message parsing wrapped in try-catch

### 3. ✅ Type Safety
- Agent `reasoning` field type-checked before rendering
- Falls back to JSON.stringify if not a string

### 4. ✅ Console Logging
- Logs each result when it arrives
- Logs WebSocket connection events
- Logs execution completion
- Logs all errors to console

### 5. ✅ Backend Verified
- Agent.think works correctly via WebSocket API
- Returns valid JSON with `reasoning` field
- No backend errors

## NOW - What You Need To Do

The Error Boundary will now **catch the crash** and show you the actual error instead of a blank screen. Here's what to do:

### Step 1: Open Browser DevTools

**Before running the workflow:**
1. Open http://localhost:3000 in your browser
2. Press **F12** to open Developer Tools
3. Click on **Console** tab
4. Make sure "All levels" is selected (not just Errors)

### Step 2: Run the Workflow

1. Click "🔍 Nmap Recon" workflow button
2. Click "Execute Workflow"
3. **Watch the console** as it executes

### Step 3: Observe What Happens

#### Scenario A: Error Boundary Catches It ✅
You'll see a red error page with:
```
⚠️ Something went wrong

Click "Error Details" to see:
- The exact error message
- Component stack trace
```

**What to do:**
- Take a screenshot or copy the error message
- Click "Error Details" and copy the Component Stack
- Share the error with me

#### Scenario B: Console Shows Error ✅
Check the console for red error messages like:
```
Uncaught TypeError: Cannot read property 'X' of undefined
Error rendering result for analyze-results: ...
React error: ...
```

**What to do:**
- Copy the error message(s)
- Note at what point it occurs
- Share the console output

#### Scenario C: No Error, Just Blanks ❓
If the screen just goes blank with NO error shown:

**What to do:**
1. Check if the page is completely blank or just the results section
2. Try scrolling - maybe results are rendering below viewport
3. Check browser console for ANY messages
4. Try a different browser (Chrome vs Firefox)
5. Check if browser console shows any network errors

### Step 4: Check Network Tab

1. In DevTools, click **Network** tab
2. Filter by **WS** (WebSocket)
3. Click on the WebSocket connection
4. Click **Messages** sub-tab
5. Look for the "complete" message

**What to check:**
- Is the agent result present in the WebSocket message?
- How large is the message?
- Is the JSON valid?

### Step 5: Specific Things to Look For

**Console should show (in order):**
```javascript
WebSocket connected
Execution complete, result: {...}
Result for port-scan: object {...}
Result for service-detection: object {...}
Result for analyze-results: object {...}  ← Look at this one!
Result for save-report: object {...}
```

**For analyze-results, check:**
- Is it `object {reasoning: "...", model: "..."}` ?
- Or is it something else?
- Is reasoning a string?
- How long is the reasoning?

## Debug Commands You Can Run

### Check if agent is returning valid data:
```bash
cd ~/Desktop/adcl/demo-sandbox/test3-dev-team
python3 test_agent_response.py
```

This should show:
```
=== AGENT RESULT ===
{
  "reasoning": "...",
  "model": "claude-3-5-sonnet-20241022"
}

Reasoning length: XXXX chars
```

### Check WebSocket messages:
```bash
# In one terminal, monitor frontend logs
./logs.sh frontend

# In another terminal, run the workflow via browser
```

## What Each Error Means

### If you see "⚠️ Something went wrong"
- React crashed during rendering
- Error Boundary caught it
- Check "Error Details" for the specific error
- This is progress! We can now see what's breaking

### If Console shows "Error rendering result for analyze-results"
- The ResultRenderer try-catch caught the error
- Check console for the specific error message
- Likely an issue with the data structure

### If Console shows "Failed to parse execution update"
- WebSocket message was malformed
- Check Network tab → WS → Messages
- Look at the raw message content

### If Browser freezes/hangs
- Possibly too much data causing memory issue
- Check Network tab for message size
- May need to truncate agent reasoning further

## Possible Root Causes

Based on the symptoms, here are the most likely causes:

### 1. **React StrictMode Issue**
- React 18+ runs effects twice in development
- Could cause double-rendering issues
- **Fix:** Check if StrictMode is enabled in main.jsx

### 2. **CSS Issue**
- `.reasoning-content` or `.agent-result` might have `display: none`
- Or `height: 0` / `overflow: hidden`
- **Fix:** Check computed styles in browser inspector

### 3. **State Update Timing**
- `setResult` might be called multiple times rapidly
- Causing React to batch updates incorrectly
- **Fix:** Add debouncing or check if state is valid before setting

### 4. **Special Characters in Reasoning**
- Reasoning might contain characters that break JSX
- Like unescaped `<`, `>`, or `{}`
- **Fix:** Already using type-safe rendering, but check actual content

### 5. **Memory Issue**
- Very long reasoning text (>50KB)
- Browser runs out of memory rendering it
- **Fix:** Already truncating at 10KB, but may need lower threshold

## Quick Tests

### Test 1: Simple Agent Response
Edit nmap workflow to use shorter prompt:
```json
{
  "id": "analyze-results",
  "params": {
    "prompt": "Say 'test' in one word"
  }
}
```

If this works → problem is with long responses
If this fails → problem is with agent rendering in general

### Test 2: Skip Agent Step
Edit workflow to comment out analyze-results node temporarily.

If this works → confirms problem is with agent.think
If this fails → problem is elsewhere

### Test 3: Different Browser
Try in:
- Chrome
- Firefox
- Safari (if on Mac)

If it works in one browser → browser-specific issue
If it fails in all → code issue

## Next Steps After You Find The Error

Once you share the actual error message, I can:
1. Fix the specific bug causing the crash
2. Add better error handling for that case
3. Modify the rendering to avoid the issue
4. Add fallbacks for problematic data

## Current Frontend State

✅ All defenses in place:
- Error Boundary (top level)
- Try-catch in ResultRenderer
- Try-catch in results mapping
- Try-catch in WebSocket handler
- Type checking for reasoning field
- Result size truncation
- Console logging everywhere

**The blank screen should now be replaced with an error message!**

---

**Please run the workflow again and tell me:**
1. What error message appears (if any)
2. What the console shows
3. Screenshots if possible

This will help me fix the exact issue!

---

**Status:** Awaiting user testing with Error Boundary
**Version:** 2.0
**Date:** 2025-10-13
