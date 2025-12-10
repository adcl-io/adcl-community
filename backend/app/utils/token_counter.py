# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Token counting utilities for multi-agent context management
Prevents rate limit errors by counting tokens before API calls
"""

import tiktoken
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Load configuration at module level (not in __init__) to avoid sync I/O in async context
_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "configs" / "runtime.json"
_DEFAULT_CONFIG = {
    "context_limits": {
        "agent_output_preview_tokens": 100,
        "additional_context_max_tokens": 500,
        "max_request_tokens": {
            "gpt-5": 400000,
            "gpt-4o": 128000,
            "gpt-4-turbo": 128000,
            "gpt-4": 8000,
            "claude-sonnet-4-5": 200000,
            "claude-sonnet-4": 200000,
            "claude-3-5-sonnet": 200000,
        },
        "safety_margin": 0.75,
    }
}

try:
    with open(_CONFIG_PATH, 'r') as f:
        _RUNTIME_CONFIG = json.load(f)
    logger.info(f"Loaded runtime config from {_CONFIG_PATH}")
except FileNotFoundError:
    logger.warning(f"Runtime config not found at {_CONFIG_PATH}, using defaults")
    _RUNTIME_CONFIG = _DEFAULT_CONFIG
except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON in runtime config: {e}, using defaults")
    _RUNTIME_CONFIG = _DEFAULT_CONFIG
except Exception as e:
    logger.error(f"Error loading runtime config: {e}, using defaults")
    _RUNTIME_CONFIG = _DEFAULT_CONFIG


class TokenCounter:
    """
    Counts tokens for different AI models to prevent rate limit errors
    Thread-safe singleton with async support
    """

    def __init__(self):
        """Initialize TokenCounter with runtime configuration"""
        self.config = _RUNTIME_CONFIG
        self.limits = self.config["context_limits"]
        self._encoders: Dict[str, tiktoken.Encoding] = {}  # Cache tokenizer instances

    def _get_encoder(self, model: str) -> tiktoken.Encoding:
        """Get or create tiktoken encoder for a model"""
        if model in self._encoders:
            return self._encoders[model]

        # All modern models use cl100k_base encoding (GPT-4, GPT-3.5, Claude approximation)
        # Note: For Claude models, this is an approximation. Actual Claude tokenization
        # can differ by up to 20%. We apply extra safety margin to compensate.
        encoding_name = "cl100k_base"

        encoder = tiktoken.get_encoding(encoding_name)
        self._encoders[model] = encoder
        return encoder

    def count_tokens(self, text: str, model: str) -> int:
        """
        Count tokens in a text string for a specific model

        Args:
            text: Text to count tokens for
            model: Model name (e.g., "gpt-4", "claude-3-sonnet")

        Returns:
            Number of tokens
        """
        if not text:
            return 0
        encoder = self._get_encoder(model)
        return len(encoder.encode(text))

    def count_messages_tokens(self, messages: List[Dict[str, Any]], model: str) -> int:
        """
        Count tokens in a messages array (OpenAI/Anthropic format)

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name

        Returns:
            Total token count including message formatting overhead
        """
        encoder = self._get_encoder(model)
        num_tokens = 0

        # Message overhead: 4 tokens per message (approximation for modern models)
        for message in messages:
            num_tokens += 4  # Every message has overhead

            # Count content
            if isinstance(message.get("content"), str):
                num_tokens += len(encoder.encode(message["content"]))
            elif isinstance(message.get("content"), list):
                # Handle multi-part content (text + images, etc.)
                for part in message["content"]:
                    if isinstance(part, dict) and "text" in part:
                        num_tokens += len(encoder.encode(part["text"]))

        num_tokens += 2  # Every conversation has 2 extra tokens
        return num_tokens

    def truncate_to_token_limit(self, text: str, max_tokens: int, model: str) -> str:
        """
        Truncate text to fit within token limit

        Args:
            text: Text to truncate
            max_tokens: Maximum tokens allowed
            model: Model name for tokenization

        Returns:
            Truncated text that fits within token limit
        """
        if not text:
            return text

        encoder = self._get_encoder(model)

        # Reserve tokens for truncation indicator
        truncation_suffix = "\n... [truncated to fit token limit]"
        suffix_tokens = len(encoder.encode(truncation_suffix))
        effective_limit = max_tokens - suffix_tokens

        if effective_limit <= 0:
            return truncation_suffix

        tokens = encoder.encode(text)

        if len(tokens) <= max_tokens:
            return text

        # Truncate and add indicator
        truncated_tokens = tokens[:effective_limit]
        truncated_text = encoder.decode(truncated_tokens)
        return truncated_text + truncation_suffix

    def get_max_request_tokens(self, model: str) -> int:
        """
        Get maximum request tokens for a model (with safety margin applied)

        Args:
            model: Model name

        Returns:
            Maximum tokens allowed for this model's requests
        """
        max_tokens = None

        # Sort by length descending to match longer prefixes first
        # This ensures "gpt-4-turbo" matches before "gpt-4"
        sorted_models = sorted(
            self.limits["max_request_tokens"].items(),
            key=lambda x: len(x[0]),
            reverse=True
        )

        for model_prefix, tokens in sorted_models:
            if model.startswith(model_prefix):
                max_tokens = tokens
                break

        if max_tokens is None:
            # Ultra-conservative default for unknown models
            logger.warning(f"Unknown model {model}, using conservative 4K token limit")
            max_tokens = 4000

        # Apply safety margin (leave room for response)
        safety_margin = self.limits["safety_margin"]

        # For Claude models, apply additional 20% safety margin due to tokenization approximation
        if model.startswith("claude"):
            safety_margin *= 0.8  # Reduce effective limit by another 20%
            logger.debug(f"Applying Claude tokenization safety factor for {model}")

        return int(max_tokens * safety_margin)

    def validate_request_size(self, messages: List[Dict], model: str) -> Dict[str, Any]:
        """
        Validate that a request fits within token limits

        Args:
            messages: Messages to send to API
            model: Model name

        Returns:
            Dict with 'valid': bool, 'token_count': int, 'limit': int, 'error': Optional[str]
        """
        token_count = self.count_messages_tokens(messages, model)
        limit = self.get_max_request_tokens(model)

        if token_count <= limit:
            return {
                "valid": True,
                "token_count": token_count,
                "limit": limit,
                "error": None
            }
        else:
            return {
                "valid": False,
                "token_count": token_count,
                "limit": limit,
                "error": (
                    f"Request too large: {token_count} tokens exceeds limit of {limit} tokens "
                    f"for model {model}. "
                    f"Reduce context size or use a model with higher limits."
                )
            }

    def get_config_limits(self) -> Dict[str, Any]:
        """Get the current configuration limits"""
        return self.limits.copy()


# Thread-safe singleton with async support
_token_counter: Optional[TokenCounter] = None
_token_counter_lock = asyncio.Lock()

async def get_token_counter_async() -> TokenCounter:
    """Get or create the global TokenCounter instance (async-safe)"""
    global _token_counter
    async with _token_counter_lock:
        if _token_counter is None:
            _token_counter = TokenCounter()
        return _token_counter

def get_token_counter() -> TokenCounter:
    """Get or create the global TokenCounter instance (sync version)"""
    global _token_counter
    if _token_counter is None:
        _token_counter = TokenCounter()
    return _token_counter
