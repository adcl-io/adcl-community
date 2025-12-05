# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Token Tracking Service
Tracks token usage per session with persistence and audit logging
"""
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, date
import logging

# Configure audit logger
audit_logger = logging.getLogger("billing")
audit_logger.setLevel(logging.INFO)

# Create logs directory with fallback chain
def get_logs_dir():
    """Try multiple log directory locations"""
    candidates = [
        Path("/app/logs"),
        Path("logs"),
        Path.cwd() / "logs",
        Path("/tmp/adcl-logs")
    ]

    for path in candidates:
        try:
            path.mkdir(parents=True, exist_ok=True)
            # Test write permission
            test_file = path / ".write_test"
            test_file.touch()
            test_file.unlink()
            return path
        except (PermissionError, OSError):
            continue

    # If all fail, use /tmp
    fallback = Path("/tmp")
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback

logs_dir = get_logs_dir()

# Daily log file for billing audit trail
log_file = logs_dir / f"billing-{date.today().isoformat()}.log"
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(
    logging.Formatter('{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}')
)
audit_logger.addHandler(file_handler)


class TokenTracker:
    """
    Tracks token usage per session with persistence.
    Single responsibility: maintain token counts.
    """

    def __init__(self, state_dir: Path = None):
        """Initialize token tracker with state persistence directory"""
        if state_dir is None:
            state_dir = Path("/app/volumes/data/token-state") if Path("/app/volumes/data").exists() else Path("volumes/data/token-state")
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Pricing configuration
        self.pricing = self._load_pricing()

    def _load_pricing(self) -> dict:
        """Load pricing from configs/pricing.json"""
        pricing_file = Path("/app/configs/pricing.json") if Path("/app/configs").exists() else Path("configs/pricing.json")

        try:
            with open(pricing_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            audit_logger.error(json.dumps({
                "error": "pricing_config_not_found",
                "file": str(pricing_file)
            }))
            # Return default pricing as fallback
            return {
                "models": {
                    "claude-sonnet-4-20250514": {
                        "input_per_million": 3.00,
                        "output_per_million": 15.00
                    }
                },
                "default_model": "claude-sonnet-4-20250514"
            }

    def _get_session_file(self, session_id: str) -> Path:
        """Get the state file path for a session"""
        return self.state_dir / f"{session_id}.json"

    def _load_session(self, session_id: str) -> dict:
        """Load session token state from disk"""
        session_file = self._get_session_file(session_id)
        if session_file.exists():
            with open(session_file, 'r') as f:
                return json.load(f)
        return {
            "session_id": session_id,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0.0,
            "models_used": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

    def _save_session(self, session_id: str, state: dict):
        """Persist session state to disk"""
        state["updated_at"] = datetime.utcnow().isoformat()
        session_file = self._get_session_file(session_id)
        with open(session_file, 'w') as f:
            json.dump(state, f, indent=2)

    def _get_model_pricing(self, model: str) -> dict:
        """Get pricing for a model, checking aliases"""
        # Direct match
        if model in self.pricing["models"]:
            return self.pricing["models"][model]

        # Check aliases
        for model_id, config in self.pricing["models"].items():
            if "aliases" in config and model in config["aliases"]:
                return config

        # Fall back to default
        default_model = self.pricing.get("default_model", "claude-sonnet-4-20250514")
        return self.pricing["models"].get(default_model, {
            "input_per_million": 3.00,
            "output_per_million": 15.00
        })

    def _calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """Calculate cost for token usage"""
        pricing = self._get_model_pricing(model)
        input_cost = (input_tokens / 1_000_000) * pricing["input_per_million"]
        output_cost = (output_tokens / 1_000_000) * pricing["output_per_million"]
        return input_cost + output_cost

    def add_tokens(self, session_id: str, input_tokens: int, output_tokens: int, model: str) -> dict:
        """
        Add tokens to session and return updated totals.
        This is the single source of truth for token tracking.

        Args:
            session_id: Session identifier
            input_tokens: Input tokens for this iteration
            output_tokens: Output tokens for this iteration
            model: Model identifier

        Returns:
            Updated session state with cumulative totals
        """
        # Validate inputs
        if input_tokens < 0 or output_tokens < 0:
            audit_logger.warning(json.dumps({
                "event": "invalid_token_count",
                "session_id": session_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            }))
            input_tokens = max(0, input_tokens)
            output_tokens = max(0, output_tokens)

        # Load current state
        state = self._load_session(session_id)

        # Calculate cost for this iteration
        iteration_cost = self._calculate_cost(input_tokens, output_tokens, model)

        # Update totals
        state["total_input_tokens"] += input_tokens
        state["total_output_tokens"] += output_tokens
        state["total_cost"] += iteration_cost

        # Track model usage
        if model not in state["models_used"]:
            state["models_used"][model] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0
            }
        state["models_used"][model]["input_tokens"] += input_tokens
        state["models_used"][model]["output_tokens"] += output_tokens
        state["models_used"][model]["cost"] += iteration_cost

        # Persist to disk
        self._save_session(session_id, state)

        # Audit log every token addition
        audit_logger.info(json.dumps({
            "event": "tokens_added",
            "session_id": session_id,
            "model": model,
            "iteration_input_tokens": input_tokens,
            "iteration_output_tokens": output_tokens,
            "iteration_cost": round(iteration_cost, 6),
            "cumulative_input_tokens": state["total_input_tokens"],
            "cumulative_output_tokens": state["total_output_tokens"],
            "cumulative_cost": round(state["total_cost"], 6)
        }))

        return state

    def get_session_tokens(self, session_id: str) -> dict:
        """Get current token state for a session"""
        return self._load_session(session_id)

    def reset_session(self, session_id: str):
        """Reset/delete session token state"""
        session_file = self._get_session_file(session_id)
        if session_file.exists():
            audit_logger.info(json.dumps({
                "event": "session_reset",
                "session_id": session_id
            }))
            session_file.unlink()


# Global singleton instance
_tracker = None

def get_token_tracker() -> TokenTracker:
    """Get or create the global token tracker instance"""
    global _tracker
    if _tracker is None:
        _tracker = TokenTracker()
    return _tracker
