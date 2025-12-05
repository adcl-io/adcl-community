# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Unit tests for Token Tracker
Tests token accumulation, cost calculation, persistence, and audit logging
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

from app.token_tracker import TokenTracker, get_token_tracker


class TestTokenTrackerInit:
    """Test TokenTracker initialization"""

    def test_init_creates_state_directory(self, tmp_path):
        """Test that TokenTracker creates state directory on init"""
        state_dir = tmp_path / "token-state"
        tracker = TokenTracker(state_dir=state_dir)

        assert state_dir.exists()
        assert tracker.state_dir == state_dir

    def test_init_loads_pricing_config(self, tmp_path):
        """Test that TokenTracker loads pricing configuration"""
        state_dir = tmp_path / "token-state"

        # Create a test pricing config
        config_dir = tmp_path / "configs"
        config_dir.mkdir()
        pricing_file = config_dir / "pricing.json"

        test_pricing = {
            "models": {
                "test-model": {
                    "input_per_million": 2.0,
                    "output_per_million": 10.0
                }
            },
            "default_model": "test-model"
        }

        with open(pricing_file, 'w') as f:
            json.dump(test_pricing, f)

        with patch('pathlib.Path.exists') as mock_exists:
            with patch('builtins.open', create=True) as mock_open:
                mock_exists.return_value = True
                mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(test_pricing)

                tracker = TokenTracker(state_dir=state_dir)

                # Should have loaded pricing
                assert "models" in tracker.pricing

    def test_init_fallback_pricing_if_config_missing(self, tmp_path):
        """Test that TokenTracker uses fallback pricing if config missing"""
        state_dir = tmp_path / "token-state"
        tracker = TokenTracker(state_dir=state_dir)

        # Should have fallback pricing
        assert "models" in tracker.pricing
        assert "default_model" in tracker.pricing


class TestTokenAccumulation:
    """Test token accumulation and tracking"""

    @pytest.fixture
    def tracker(self, tmp_path):
        """Create a tracker with temporary state directory"""
        state_dir = tmp_path / "token-state"
        return TokenTracker(state_dir=state_dir)

    def test_add_tokens_creates_session_state(self, tracker):
        """Test that add_tokens creates new session state"""
        result = tracker.add_tokens(
            session_id="session-1",
            input_tokens=100,
            output_tokens=50,
            model="claude-sonnet-4-20250514"
        )

        assert result["session_id"] == "session-1"
        assert result["total_input_tokens"] == 100
        assert result["total_output_tokens"] == 50
        assert result["total_cost"] > 0

    def test_add_tokens_accumulates_correctly(self, tracker):
        """Test that multiple add_tokens calls accumulate correctly"""
        # First call
        tracker.add_tokens("session-1", 100, 50, "claude-sonnet-4-20250514")

        # Second call
        tracker.add_tokens("session-1", 200, 100, "claude-sonnet-4-20250514")

        # Third call
        result = tracker.add_tokens("session-1", 150, 75, "claude-sonnet-4-20250514")

        # Should have cumulative totals
        assert result["total_input_tokens"] == 450  # 100 + 200 + 150
        assert result["total_output_tokens"] == 225  # 50 + 100 + 75

    def test_add_tokens_tracks_per_model(self, tracker):
        """Test that tokens are tracked per model"""
        tracker.add_tokens("session-1", 100, 50, "claude-sonnet-4-20250514")
        tracker.add_tokens("session-1", 200, 100, "claude-opus-4-20250514")

        result = tracker.get_session_tokens("session-1")

        assert "claude-sonnet-4-20250514" in result["models_used"]
        assert "claude-opus-4-20250514" in result["models_used"]
        assert result["models_used"]["claude-sonnet-4-20250514"]["input_tokens"] == 100
        assert result["models_used"]["claude-opus-4-20250514"]["input_tokens"] == 200

    def test_add_tokens_validates_negative_counts(self, tracker):
        """Test that negative token counts are handled"""
        # Should not raise, but should clamp to zero
        result = tracker.add_tokens("session-1", -100, -50, "claude-sonnet-4-20250514")

        # Negative values should be clamped to 0
        assert result["total_input_tokens"] == 0
        assert result["total_output_tokens"] == 0
        assert result["total_cost"] == 0

    def test_add_tokens_handles_zero_tokens(self, tracker):
        """Test that zero token counts are handled"""
        result = tracker.add_tokens("session-1", 0, 0, "claude-sonnet-4-20250514")

        assert result["total_input_tokens"] == 0
        assert result["total_output_tokens"] == 0
        assert result["total_cost"] == 0


class TestCostCalculation:
    """Test cost calculation with different models"""

    @pytest.fixture
    def tracker_with_pricing(self, tmp_path):
        """Create tracker with custom pricing"""
        state_dir = tmp_path / "token-state"
        tracker = TokenTracker(state_dir=state_dir)

        # Override pricing for testing
        tracker.pricing = {
            "models": {
                "claude-sonnet-4-20250514": {
                    "input_per_million": 3.00,
                    "output_per_million": 15.00,
                    "aliases": ["sonnet-4"]
                },
                "claude-opus-4-20250514": {
                    "input_per_million": 15.00,
                    "output_per_million": 75.00,
                    "aliases": ["opus-4"]
                },
                "claude-haiku-3-5-20241022": {
                    "input_per_million": 0.25,
                    "output_per_million": 1.25,
                    "aliases": ["haiku-3.5"]
                }
            },
            "default_model": "claude-sonnet-4-20250514"
        }

        return tracker

    def test_calculate_cost_sonnet(self, tracker_with_pricing):
        """Test cost calculation for Sonnet model"""
        # 1M input tokens at $3.00 + 1M output tokens at $15.00 = $18.00
        cost = tracker_with_pricing._calculate_cost(
            1_000_000, 1_000_000, "claude-sonnet-4-20250514"
        )
        assert cost == 18.00

    def test_calculate_cost_opus(self, tracker_with_pricing):
        """Test cost calculation for Opus model"""
        # 1M input tokens at $15.00 + 1M output tokens at $75.00 = $90.00
        cost = tracker_with_pricing._calculate_cost(
            1_000_000, 1_000_000, "claude-opus-4-20250514"
        )
        assert cost == 90.00

    def test_calculate_cost_haiku(self, tracker_with_pricing):
        """Test cost calculation for Haiku model"""
        # 1M input tokens at $0.25 + 1M output tokens at $1.25 = $1.50
        cost = tracker_with_pricing._calculate_cost(
            1_000_000, 1_000_000, "claude-haiku-3-5-20241022"
        )
        assert cost == 1.50

    def test_calculate_cost_small_amounts(self, tracker_with_pricing):
        """Test cost calculation for small token amounts"""
        # 1000 input + 500 output tokens (Sonnet)
        # Input: (1000/1M) * $3.00 = $0.003
        # Output: (500/1M) * $15.00 = $0.0075
        # Total: $0.0105
        cost = tracker_with_pricing._calculate_cost(
            1000, 500, "claude-sonnet-4-20250514"
        )
        assert abs(cost - 0.0105) < 0.0001  # Allow tiny floating point error

    def test_cost_accumulates_correctly(self, tracker_with_pricing):
        """Test that costs accumulate correctly over multiple calls"""
        # Add tokens 3 times
        tracker_with_pricing.add_tokens("session-1", 1000, 500, "claude-sonnet-4-20250514")
        tracker_with_pricing.add_tokens("session-1", 2000, 1000, "claude-sonnet-4-20250514")
        result = tracker_with_pricing.add_tokens("session-1", 1500, 750, "claude-sonnet-4-20250514")

        # Total tokens: 4500 input, 2250 output
        # Expected cost: (4500/1M)*3.00 + (2250/1M)*15.00 = 0.0135 + 0.03375 = 0.04725
        expected_cost = 0.04725
        assert abs(result["total_cost"] - expected_cost) < 0.0001


class TestModelAliasResolution:
    """Test model alias resolution for pricing"""

    @pytest.fixture
    def tracker_with_aliases(self, tmp_path):
        """Create tracker with alias support"""
        state_dir = tmp_path / "token-state"
        tracker = TokenTracker(state_dir=state_dir)

        tracker.pricing = {
            "models": {
                "claude-sonnet-4-20250514": {
                    "input_per_million": 3.00,
                    "output_per_million": 15.00,
                    "aliases": ["sonnet-4", "claude-sonnet-4"]
                }
            },
            "default_model": "claude-sonnet-4-20250514"
        }

        return tracker

    def test_get_model_pricing_by_full_name(self, tracker_with_aliases):
        """Test getting pricing by full model name"""
        pricing = tracker_with_aliases._get_model_pricing("claude-sonnet-4-20250514")
        assert pricing["input_per_million"] == 3.00
        assert pricing["output_per_million"] == 15.00

    def test_get_model_pricing_by_alias(self, tracker_with_aliases):
        """Test getting pricing by model alias"""
        pricing = tracker_with_aliases._get_model_pricing("sonnet-4")
        assert pricing["input_per_million"] == 3.00

        pricing = tracker_with_aliases._get_model_pricing("claude-sonnet-4")
        assert pricing["input_per_million"] == 3.00

    def test_get_model_pricing_unknown_model_uses_default(self, tracker_with_aliases):
        """Test that unknown model uses default pricing"""
        pricing = tracker_with_aliases._get_model_pricing("unknown-model")
        # Should fall back to default
        assert "input_per_million" in pricing
        assert "output_per_million" in pricing


class TestStatePersistence:
    """Test state persistence to disk"""

    @pytest.fixture
    def tracker(self, tmp_path):
        """Create tracker with temporary state directory"""
        state_dir = tmp_path / "token-state"
        return TokenTracker(state_dir=state_dir)

    def test_state_persists_to_disk(self, tracker):
        """Test that session state is written to disk"""
        tracker.add_tokens("session-1", 100, 50, "claude-sonnet-4-20250514")

        # Check that file was created
        session_file = tracker._get_session_file("session-1")
        assert session_file.exists()

        # Verify content
        with open(session_file, 'r') as f:
            state = json.load(f)

        assert state["session_id"] == "session-1"
        assert state["total_input_tokens"] == 100
        assert state["total_output_tokens"] == 50

    def test_state_loads_from_disk(self, tracker):
        """Test that session state is loaded from disk"""
        # Add tokens
        tracker.add_tokens("session-1", 100, 50, "claude-sonnet-4-20250514")

        # Create new tracker instance (simulates restart)
        new_tracker = TokenTracker(state_dir=tracker.state_dir)

        # Should load existing state
        state = new_tracker.get_session_tokens("session-1")
        assert state["total_input_tokens"] == 100
        assert state["total_output_tokens"] == 50

    def test_state_updates_timestamp(self, tracker):
        """Test that state updates timestamp on each save"""
        tracker.add_tokens("session-1", 100, 50, "claude-sonnet-4-20250514")

        state1 = tracker.get_session_tokens("session-1")
        updated_at_1 = state1["updated_at"]

        # Add more tokens
        import time
        time.sleep(0.01)  # Ensure timestamp changes
        tracker.add_tokens("session-1", 50, 25, "claude-sonnet-4-20250514")

        state2 = tracker.get_session_tokens("session-1")
        updated_at_2 = state2["updated_at"]

        # Timestamp should be different
        assert updated_at_1 != updated_at_2

    def test_multiple_sessions_persist_separately(self, tracker):
        """Test that multiple sessions have separate state files"""
        tracker.add_tokens("session-1", 100, 50, "claude-sonnet-4-20250514")
        tracker.add_tokens("session-2", 200, 100, "claude-sonnet-4-20250514")
        tracker.add_tokens("session-3", 150, 75, "claude-sonnet-4-20250514")

        # All should have separate files
        assert tracker._get_session_file("session-1").exists()
        assert tracker._get_session_file("session-2").exists()
        assert tracker._get_session_file("session-3").exists()

        # Each should have correct data
        assert tracker.get_session_tokens("session-1")["total_input_tokens"] == 100
        assert tracker.get_session_tokens("session-2")["total_input_tokens"] == 200
        assert tracker.get_session_tokens("session-3")["total_input_tokens"] == 150

    def test_reset_session_deletes_state(self, tracker):
        """Test that reset_session deletes state file"""
        tracker.add_tokens("session-1", 100, 50, "claude-sonnet-4-20250514")

        session_file = tracker._get_session_file("session-1")
        assert session_file.exists()

        tracker.reset_session("session-1")

        assert not session_file.exists()


class TestGetSessionTokens:
    """Test get_session_tokens method"""

    @pytest.fixture
    def tracker(self, tmp_path):
        """Create tracker with temporary state directory"""
        state_dir = tmp_path / "token-state"
        return TokenTracker(state_dir=state_dir)

    def test_get_session_tokens_existing_session(self, tracker):
        """Test getting tokens for existing session"""
        tracker.add_tokens("session-1", 100, 50, "claude-sonnet-4-20250514")

        result = tracker.get_session_tokens("session-1")

        assert result["session_id"] == "session-1"
        assert result["total_input_tokens"] == 100
        assert result["total_output_tokens"] == 50
        assert "models_used" in result
        assert "created_at" in result
        assert "updated_at" in result

    def test_get_session_tokens_new_session(self, tracker):
        """Test getting tokens for non-existent session returns empty state"""
        result = tracker.get_session_tokens("new-session")

        assert result["session_id"] == "new-session"
        assert result["total_input_tokens"] == 0
        assert result["total_output_tokens"] == 0
        assert result["total_cost"] == 0.0
        assert result["models_used"] == {}


class TestAuditLogging:
    """Test audit logging functionality"""

    @pytest.fixture
    def tracker(self, tmp_path):
        """Create tracker with temporary state directory"""
        state_dir = tmp_path / "token-state"
        return TokenTracker(state_dir=state_dir)

    def test_audit_log_on_add_tokens(self, tracker, caplog):
        """Test that add_tokens creates audit log entry"""
        import logging
        caplog.set_level(logging.INFO, logger="billing")

        tracker.add_tokens("session-1", 100, 50, "claude-sonnet-4-20250514")

        # Check that audit log was created
        assert len(caplog.records) > 0

        # Find the tokens_added log entry
        token_logs = [r for r in caplog.records if "tokens_added" in r.message]
        assert len(token_logs) > 0

        # Verify log contains required fields
        log_entry = json.loads(token_logs[0].message)
        assert log_entry["event"] == "tokens_added"
        assert log_entry["session_id"] == "session-1"
        assert log_entry["model"] == "claude-sonnet-4-20250514"
        assert log_entry["iteration_input_tokens"] == 100
        assert log_entry["iteration_output_tokens"] == 50

    def test_audit_log_on_reset(self, tracker, caplog):
        """Test that reset_session creates audit log entry"""
        import logging
        caplog.set_level(logging.INFO, logger="billing")

        tracker.add_tokens("session-1", 100, 50, "claude-sonnet-4-20250514")
        caplog.clear()

        tracker.reset_session("session-1")

        # Check that reset log was created
        reset_logs = [r for r in caplog.records if "session_reset" in r.message]
        assert len(reset_logs) > 0

        log_entry = json.loads(reset_logs[0].message)
        assert log_entry["event"] == "session_reset"
        assert log_entry["session_id"] == "session-1"


class TestGlobalSingleton:
    """Test global singleton instance"""

    def test_get_token_tracker_returns_singleton(self):
        """Test that get_token_tracker returns same instance"""
        tracker1 = get_token_tracker()
        tracker2 = get_token_tracker()

        assert tracker1 is tracker2

    def test_singleton_state_persists(self):
        """Test that singleton maintains state across calls"""
        tracker = get_token_tracker()
        tracker.add_tokens("singleton-test", 100, 50, "claude-sonnet-4-20250514")

        # Get tracker again
        tracker2 = get_token_tracker()
        state = tracker2.get_session_tokens("singleton-test")

        assert state["total_input_tokens"] == 100


class TestEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.fixture
    def tracker(self, tmp_path):
        """Create tracker with temporary state directory"""
        state_dir = tmp_path / "token-state"
        return TokenTracker(state_dir=state_dir)

    def test_very_large_token_counts(self, tracker):
        """Test handling of very large token counts"""
        result = tracker.add_tokens(
            "session-1",
            10_000_000,  # 10M tokens
            5_000_000,   # 5M tokens
            "claude-sonnet-4-20250514"
        )

        assert result["total_input_tokens"] == 10_000_000
        assert result["total_output_tokens"] == 5_000_000
        assert result["total_cost"] > 0

    def test_session_id_with_special_characters(self, tracker):
        """Test session IDs with special characters"""
        # Should handle alphanumeric + hyphens
        result = tracker.add_tokens(
            "session-123-abc-xyz",
            100, 50, "claude-sonnet-4-20250514"
        )

        assert result["session_id"] == "session-123-abc-xyz"

    def test_mixed_model_usage_in_session(self, tracker):
        """Test session with multiple different models"""
        tracker.add_tokens("session-1", 100, 50, "claude-sonnet-4-20250514")
        tracker.add_tokens("session-1", 200, 100, "claude-opus-4-20250514")
        tracker.add_tokens("session-1", 50, 25, "claude-haiku-3-5-20241022")
        tracker.add_tokens("session-1", 150, 75, "claude-sonnet-4-20250514")

        result = tracker.get_session_tokens("session-1")

        # Should track all models
        assert len(result["models_used"]) == 3

        # Sonnet should have combined totals from two calls
        assert result["models_used"]["claude-sonnet-4-20250514"]["input_tokens"] == 250
        assert result["models_used"]["claude-sonnet-4-20250514"]["output_tokens"] == 125


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
