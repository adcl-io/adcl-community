# History MCP Server

Unix-philosophy compliant conversation history system using append-only JSONL files.

## Features

- **Append-only JSONL storage** - Human-readable, grep-friendly message logs
- **ULID-based session IDs** - Natural time-based sorting
- **Byte offset indexes** - O(1) message seeks for large conversations
- **Write-ahead logging** - Crash recovery with guaranteed durability
- **Full-text search** - Search titles and message content
- **Atomic operations** - File locking for concurrent writes
- **Pagination support** - Efficient retrieval of large conversations
- **Real-time streaming** - Watch messages as they're written

## Architecture

### Directory Structure

```
volumes/conversations/
├── sessions.jsonl          # Master session list (append-only)
├── active/                 # Current conversations
│   └── {session_id}/
│       ├── metadata.json   # Session metadata
│       ├── messages.jsonl  # Message log (append-only)
│       ├── index.json      # Byte offset index
│       └── .lock          # Write lock file
├── archive/                # Archived conversations
├── indexes/                # Search indexes
└── wal/                    # Write-ahead log
    └── pending.jsonl
```

### Core Modules

1. **SessionManager** - Create and manage conversation sessions
2. **MessageWriter** - Append messages with WAL support
3. **MessageReader** - Efficient message retrieval with pagination
4. **SearchEngine** - Title and full-text search
5. **IndexBuilder** - Build byte offset indexes
6. **WALManager** - Crash recovery

## MCP Tools

### Session Management

- `create_session` - Create new conversation
- `get_session` - Get session metadata
- `list_sessions` - List conversations with pagination

### Message Management

- `append_message` - Add message to conversation
- `get_messages` - Retrieve messages with pagination
- `get_message` - Get specific message by ID

### Search

- `search_titles` - Search conversation titles (fast)
- `search_messages` - Full-text search across messages

### Maintenance

- `rebuild_index` - Rebuild byte offset index for a session

## Usage Examples

### Create a session and add messages

```python
import httpx

# Create session
response = httpx.post("http://mcp-history:7004/mcp/call_tool", json={
    "tool": "create_session",
    "arguments": {
        "title": "Security Assessment",
        "metadata": {"tags": ["security", "audit"]}
    }
})
session_id = response.json()["content"][0]["text"]["session_id"]

# Append message
httpx.post("http://mcp-history:7004/mcp/call_tool", json={
    "tool": "append_message",
    "arguments": {
        "session_id": session_id,
        "message_type": "user",
        "content": "Scan the network for vulnerabilities"
    }
})
```

### Retrieve messages

```python
# Get latest 50 messages (newest first)
response = httpx.post("http://mcp-history:7004/mcp/call_tool", json={
    "tool": "get_messages",
    "arguments": {
        "session_id": session_id,
        "limit": 50,
        "reverse": True
    }
})
messages = response.json()["content"][0]["text"]["messages"]
```

### Search

```python
# Search titles
response = httpx.post("http://mcp-history:7004/mcp/call_tool", json={
    "tool": "search_titles",
    "arguments": {
        "query": "security",
        "limit": 20
    }
})

# Full-text search
response = httpx.post("http://mcp-history:7004/mcp/call_tool", json={
    "tool": "search_messages",
    "arguments": {
        "query": "vulnerability",
        "limit": 100
    }
})
```

## Command-Line Inspection

Because everything is plain text, you can use standard Unix tools:

```bash
# List all sessions
cat volumes/conversations/sessions.jsonl | jq .

# View messages in a conversation
cat volumes/conversations/active/{session_id}/messages.jsonl | jq .

# Search for specific content
grep -r "vulnerability" volumes/conversations/active/

# Count messages in a session
wc -l volumes/conversations/active/{session_id}/messages.jsonl

# Get last 10 messages
tail -10 volumes/conversations/active/{session_id}/messages.jsonl | jq .

# Watch messages in real-time
tail -f volumes/conversations/active/{session_id}/messages.jsonl | jq .
```

## Performance

- **Create session**: <10ms
- **Append message**: <20ms
- **List 50 sessions**: <10ms
- **Load 50 messages**: <20ms with index, <50ms without
- **Search titles**: <50ms
- **Full-text search**: ~2s for 10GB of messages

## Configuration

See `configs/history.conf` for settings:

```ini
[storage]
base_path = /app/volumes/conversations
max_message_size_kb = 100
max_session_size_mb = 1000

[performance]
wal_enabled = true
wal_flush_interval_sec = 5
index_build_threshold = 1000

[archival]
archive_after_days = 7
```

## Testing

Run the test suite:

```bash
cd mcp_servers/history
python test_history.py
```

## Deployment

The history MCP is available in the default registry:

```bash
# Install via orchestrator
curl -X POST http://localhost:8000/registries/install/mcp/history-1.0.0
```

Or manually via docker-compose:

```yaml
services:
  mcp-history:
    build: ./mcp_servers/history
    ports:
      - "7004:7004"
    volumes:
      - ./volumes/conversations:/app/volumes/conversations
    environment:
      - HISTORY_PORT=7004
      - HISTORY_STORAGE=/app/volumes/conversations
```

## Crash Recovery

The system uses a write-ahead log (WAL) for durability. On startup, the server automatically recovers any uncommitted writes:

```bash
# Check WAL status
cat volumes/conversations/wal/pending.jsonl

# Manual recovery (if needed)
python -c "from wal import WALManager; WALManager().recover_from_wal()"
```

## Maintenance

### Rebuild indexes

```bash
# Rebuild index for a specific session
python -c "from indexer import IndexBuilder; IndexBuilder().build_message_index('SESSION_ID')"

# Rebuild all indexes
python -c "from indexer import IndexBuilder; IndexBuilder().rebuild_all_indexes()"
```

### Archive old sessions

```bash
# Archive a session
python -c "from session_manager import SessionManager; SessionManager().archive_session('SESSION_ID')"
```

## Design Philosophy

Following ADCL Unix philosophy:

- **One thing well**: Store and retrieve conversation history
- **Text streams**: Everything is human-readable JSONL
- **Composability**: Works with grep, cat, jq, tail
- **No hidden state**: All data inspectable with standard tools
- **Configuration as code**: Plain text config files
- **Fail fast**: Clear errors, comprehensive logging

## Integration

The history MCP integrates seamlessly with other MCP servers:

- **Agent MCP**: Log agent thinking and responses
- **File Tools MCP**: Store conversation transcripts as files
- **Vector MCP**: Index conversation history for semantic search
- **Nmap MCP**: Log security scan results in conversation context

## Future Enhancements

- Compression for archived sessions
- Bloom filters for negative search caching
- Vector embeddings for semantic search
- Export to common formats (Markdown, PDF)
- Real-time WebSocket streaming API
