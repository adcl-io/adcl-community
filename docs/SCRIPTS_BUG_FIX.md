# Scripts Bug Fix - Project Directory Awareness

## Issue Reported

User: "confused; so we have a port conflict with api; is it being used or not?"
User: "status script gives negative result; saying not running; so maybe bug there in not looking at correct stack"

## Root Cause

The management scripts (start.sh, stop.sh, status.sh, etc.) were using `docker-compose ps` which checks whatever `docker-compose.yml` file exists in the **current working directory**.

**Problem:**
- If you ran `test3-dev-team/status.sh` from the `test2` directory
- The script would check `test2/docker-compose.yml` services
- But would still show endpoints for test3-dev-team (ports 7000, 7002, 7003, 8000)
- This caused confusion about which project was actually running

## The Confusion

```bash
# User was in test2 directory
cd ~/Desktop/adcl/demo-sandbox/test2

# Ran test2's status check
./status.sh
# Output: "API Server: NOT RUNNING" ← test2's API

# But test3-dev-team's API WAS running on port 8000
docker ps | grep orchestrator
# test3-dev-team_orchestrator_1   Up   0.0.0.0:8000->8000/tcp
```

Both projects wanted to use port 8000, but test3 was the one actually using it.

## Fix Applied

Added project directory awareness to ALL scripts:

### Before
```bash
#!/bin/bash
# Status script

docker-compose ps  # Checks CWD's docker-compose.yml
```

### After
```bash
#!/bin/bash
# Status script

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📁 Project: $SCRIPT_DIR"

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: docker-compose.yml not found"
    exit 1
fi

docker-compose ps  # Now checks script's directory
```

## Changes Made

Updated all 7 scripts to be directory-aware:

1. ✅ **start.sh** - Auto-navigates to test3-dev-team directory
2. ✅ **stop.sh** - Auto-navigates to test3-dev-team directory
3. ✅ **status.sh** - Auto-navigates to test3-dev-team directory
4. ✅ **logs.sh** - Auto-navigates to test3-dev-team directory
5. ✅ **restart-api.sh** - Auto-navigates to test3-dev-team directory
6. ✅ **restart-agent.sh** - Auto-navigates to test3-dev-team directory
7. ✅ **restart-frontend.sh** - Auto-navigates to test3-dev-team directory

Each script now:
- Determines its own location
- Changes to that directory
- Shows "📁 Project: /path/to/test3-dev-team"
- Validates docker-compose.yml exists
- Operates on the correct project

## Testing

### Test 1: Run from different directory ✅
```bash
# Run from /tmp
cd /tmp
~/Desktop/adcl/demo-sandbox/test3-dev-team/status.sh

# Output correctly shows:
# 📁 Project: /home/jason/Desktop/adcl/demo-sandbox/test3-dev-team
# ✅ All test3-dev-team services UP
```

### Test 2: Run from test2 directory ✅
```bash
# Run from test2
cd ~/Desktop/adcl/demo-sandbox/test2
~/Desktop/adcl/demo-sandbox/test3-dev-team/status.sh

# Output clearly shows:
# 📁 Project: /home/jason/Desktop/adcl/demo-sandbox/test3-dev-team
# ✅ API Server (port 8000) - UP
# ✅ All test3-dev-team services UP
```

### Test 3: Run from test3-dev-team directory ✅
```bash
cd ~/Desktop/adcl/demo-sandbox/test3-dev-team
./status.sh

# Output:
# 📁 Project: /home/jason/Desktop/adcl/demo-sandbox/test3-dev-team
# ✅ All services UP
```

## Benefits

✅ **No more confusion** - Script always shows which project it's checking
✅ **Run from anywhere** - Scripts work regardless of current directory
✅ **Clear feedback** - Shows project path in output
✅ **Error checking** - Validates docker-compose.yml exists
✅ **Consistent behavior** - All scripts work the same way

## Usage Examples

### Check test3-dev-team status from anywhere:
```bash
~/Desktop/adcl/demo-sandbox/test3-dev-team/status.sh
```

### Or use absolute path in alias:
```bash
# Add to ~/.bashrc
alias mcp-status='~/Desktop/adcl/demo-sandbox/test3-dev-team/status.sh'
alias mcp-logs='~/Desktop/adcl/demo-sandbox/test3-dev-team/logs.sh'

# Then from anywhere:
mcp-status
mcp-logs api
```

## How to Verify Fix

1. Check test3-dev-team is running:
   ```bash
   docker ps | grep test3-dev-team
   ```

2. Run status from test2 directory:
   ```bash
   cd ~/Desktop/adcl/demo-sandbox/test2
   ~/Desktop/adcl/demo-sandbox/test3-dev-team/status.sh
   ```

3. Verify output shows:
   - ✅ Project path: test3-dev-team
   - ✅ API Server (port 8000) - UP
   - ✅ All test3-dev-team services UP

## Summary

**Before:** Scripts checked whatever docker-compose.yml was in your current directory
**After:** Scripts always check their own project's docker-compose.yml

This eliminates confusion when working with multiple projects (test2, test3-dev-team, etc.) that may use the same port numbers.

---

**Status:** ✅ Fixed and Tested
**All Scripts Updated:** 7/7
**Version:** 1.1
**Date:** 2025-10-13
