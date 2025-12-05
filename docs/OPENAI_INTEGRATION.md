# OpenAI Integration Status

## Current Status: INCOMPLETE

OpenAI models are **partially integrated** but **not functional** for agent execution.

## What Works ✅

1. **Model Configuration**
   - OpenAI models can be configured in `configs/models.yaml`
   - API keys loaded from `OPENAI_API_KEY` environment variable
   - Models display in UI with configuration status

2. **Client Initialization**
   - `OpenAI` client instantiated in `main.py:461`
   - Client passed to `AgentRuntime` constructor

3. **Provider Detection**
   - `_get_client_for_model()` correctly routes to OpenAI for `gpt-*` and `o1-*` models

## What Doesn't Work ❌

### Critical Issue: Tool Calling Format Mismatch

**Location**: `backend/app/agent_runtime.py:133-139`

**Problem**: Anthropic and OpenAI use **different formats** for tool calling:

#### Anthropic Format (Currently Used)
```python
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    system="You are a helpful assistant",
    messages=[{"role": "user", "content": "Hello"}],
    tools=[{
        "name": "search",
        "description": "Search the web",
        "input_schema": {
            "type": "object",
            "properties": {...}
        }
    }]
)
```

#### OpenAI Format (Required)
```python
response = client.chat.completions.create(
    model="gpt-4-turbo-preview",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"}
    ],
    tools=[{
        "type": "function",
        "function": {
            "name": "search",
            "description": "Search the web",
            "parameters": {
                "type": "object",
                "properties": {...}
            }
        }
    }]
)
```

### Key Differences

1. **System Message**
   - Anthropic: Separate `system` parameter
   - OpenAI: System message in `messages` array

2. **Tool Definition Structure**
   - Anthropic: `input_schema` at top level
   - OpenAI: Wrapped in `function` object with `type: "function"`
   - OpenAI: Uses `parameters` instead of `input_schema`

3. **Response Format**
   - Anthropic: `response.content[].type == "tool_use"`
   - OpenAI: `response.choices[0].message.tool_calls[]`

4. **Stop Reasons**
   - Anthropic: `stop_reason == "tool_use"` or `"end_turn"`
   - OpenAI: `finish_reason == "tool_calls"` or `"stop"`

## Implementation Requirements

To complete OpenAI integration, the following changes are needed:

### 1. Tool Format Conversion (`agent_runtime.py`)

```python
def _convert_tools_to_openai_format(self, anthropic_tools: List[Dict]) -> List[Dict]:
    """Convert Anthropic tool format to OpenAI format"""
    openai_tools = []
    for tool in anthropic_tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"]
            }
        })
    return openai_tools
```

### 2. Message Format Conversion

```python
def _build_openai_messages(self, messages: List[Dict], system_prompt: str) -> List[Dict]:
    """Build OpenAI message format with system message"""
    openai_messages = [{"role": "system", "content": system_prompt}]

    for msg in messages:
        if msg["role"] == "user":
            openai_messages.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            # Handle tool calls in OpenAI format
            ...

    return openai_messages
```

### 3. Response Handling

```python
if provider == "openai":
    response = client.chat.completions.create(
        model=model_name,
        messages=self._build_openai_messages(messages, system_prompt),
        tools=self._convert_tools_to_openai_format(tools),
        temperature=temperature,
        max_tokens=max_tokens
    )

    # Extract token usage
    token_usage = {
        "input_tokens": response.usage.prompt_tokens,
        "output_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens
    }

    # Check finish reason
    if response.choices[0].finish_reason == "tool_calls":
        # Extract and execute tool calls
        tool_calls = response.choices[0].message.tool_calls
        ...
    elif response.choices[0].finish_reason == "stop":
        # Agent is done
        final_text = response.choices[0].message.content
        ...
```

### 4. Tool Result Format

OpenAI requires tool results in this format:
```python
{
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": json.dumps(result)
}
```

vs Anthropic:
```python
{
    "role": "user",
    "content": [{
        "type": "tool_result",
        "tool_use_id": tool_call.id,
        "content": json.dumps(result)
    }]
}
```

## Current Behavior

When an OpenAI model is selected for an agent:

1. Agent configuration loads successfully
2. UI shows OpenAI models as configured
3. **Agent execution fails** with:
   ```
   NotImplementedError: OpenAI models not fully integrated yet.
   Model 'gpt-4-turbo-preview' requires additional implementation.
   Please use Claude models (claude-sonnet-4-5-20250929, etc.)
   or implement OpenAI tool calling format.
   ```

## Recommended Actions

### Option 1: Complete the Integration (Recommended if OpenAI support needed)

1. Implement format conversion functions above
2. Add OpenAI-specific response handling
3. Test with MCP tool calls
4. Update token usage tracking
5. Add unit tests for OpenAI code paths

**Estimated effort**: 4-6 hours

### Option 2: Remove OpenAI Until Ready (Recommended for MVP)

1. Remove OpenAI models from `configs/models.yaml`
2. Remove `openai==1.54.0` from `requirements.txt`
3. Remove OpenAI client initialization
4. Update UI to only show Anthropic models
5. Document as "Coming Soon" feature

**Estimated effort**: 30 minutes

### Option 3: Document as Experimental (Current Approach)

Keep current code with clear warnings:
- Add `(Experimental - Not Functional)` label to OpenAI models in UI
- Show warning when user tries to select OpenAI model
- Document limitations in user-facing docs

**Estimated effort**: 1 hour

## Testing Requirements

Once implemented, test:

1. ✅ GPT-4 model configuration loads
2. ✅ Agent definition with `gpt-4-turbo-preview` validates
3. ❌ Agent execution with simple task (no tools)
4. ❌ Agent execution with MCP tool calls
5. ❌ Tool result handling and conversation continuation
6. ❌ Token usage reporting
7. ❌ Error handling for OpenAI API errors

## References

- OpenAI Tool Calling Docs: https://platform.openai.com/docs/guides/function-calling
- Anthropic Tool Use Docs: https://docs.anthropic.com/en/docs/build-with-claude/tool-use
- Current Implementation: `backend/app/agent_runtime.py:38-48, 117-141`

## Last Updated

2025-11-09 - Status: Incomplete, NotImplementedError raised for OpenAI models
