# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""Tests for Linear webhook trigger security improvements"""
import pytest
import time
import hmac
import hashlib
from datetime import datetime, timedelta
from unittest.mock import patch
import sys
import os

# Add triggers directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'triggers', 'webhook'))

from linear_webhook_trigger import (
    verify_linear_signature,
    verify_timestamp,
    is_duplicate_delivery,
    cleanup_old_deliveries,
    validate_webhook_config,
    processed_deliveries,
    TIMESTAMP_TOLERANCE_SECONDS
)


class TestSignatureVerification:
    """Test webhook signature verification"""
    
    def test_valid_signature(self):
        """Test that valid signatures are accepted"""
        secret = "test_secret_key_12345678901234567890"
        payload = b'{"type": "agentSession", "action": "created"}'
        
        # Compute valid signature
        mac = hmac.new(secret.encode(), payload, hashlib.sha256)
        signature = mac.hexdigest()
        
        # Patch the module-level variable directly
        import linear_webhook_trigger
        with patch.object(linear_webhook_trigger, 'LINEAR_WEBHOOK_SECRET', secret):
            assert verify_linear_signature(payload, signature) is True
    
    def test_invalid_signature(self):
        """Test that invalid signatures are rejected"""
        secret = "test_secret_key_12345678901234567890"
        payload = b'{"type": "agentSession", "action": "created"}'
        
        import linear_webhook_trigger
        with patch.object(linear_webhook_trigger, 'LINEAR_WEBHOOK_SECRET', secret):
            assert verify_linear_signature(payload, "invalid_signature") is False
    
    def test_signature_with_whitespace(self):
        """Test that signatures with whitespace are handled"""
        secret = "test_secret_key_12345678901234567890"
        payload = b'{"type": "agentSession", "action": "created"}'
        
        mac = hmac.new(secret.encode(), payload, hashlib.sha256)
        signature = mac.hexdigest()
        
        import linear_webhook_trigger
        with patch.object(linear_webhook_trigger, 'LINEAR_WEBHOOK_SECRET', secret):
            # Should work with leading/trailing whitespace
            assert verify_linear_signature(payload, f"  {signature}  ") is True
    
    def test_missing_secret(self):
        """Test that missing secret rejects webhooks"""
        payload = b'{"type": "agentSession", "action": "created"}'
        
        import linear_webhook_trigger
        with patch.object(linear_webhook_trigger, 'LINEAR_WEBHOOK_SECRET', ""):
            assert verify_linear_signature(payload, "any_signature") is False


class TestTimestampVerification:
    """Test webhook timestamp verification"""
    
    def test_valid_timestamp(self):
        """Test that recent timestamps are accepted"""
        current_time = int(time.time())
        assert verify_timestamp(str(current_time)) is True
    
    def test_old_timestamp(self):
        """Test that old timestamps are rejected"""
        old_time = int(time.time()) - (TIMESTAMP_TOLERANCE_SECONDS + 60)
        assert verify_timestamp(str(old_time)) is False
    
    def test_future_timestamp(self):
        """Test that future timestamps within tolerance are accepted"""
        future_time = int(time.time()) + 60  # 1 minute in future
        assert verify_timestamp(str(future_time)) is True
    
    def test_missing_timestamp(self):
        """Test that missing timestamp is gracefully handled"""
        assert verify_timestamp(None) is True
    
    def test_invalid_timestamp_format(self):
        """Test that invalid timestamp format is rejected"""
        assert verify_timestamp("not_a_number") is False


class TestDeduplication:
    """Test webhook deduplication"""
    
    def setup_method(self):
        """Clear cache before each test"""
        processed_deliveries.clear()
    
    def test_first_delivery(self):
        """Test that first delivery is not duplicate"""
        assert is_duplicate_delivery("delivery-123") is False
    
    def test_duplicate_delivery(self):
        """Test that duplicate delivery is detected"""
        delivery_id = "delivery-456"
        assert is_duplicate_delivery(delivery_id) is False
        assert is_duplicate_delivery(delivery_id) is True
    
    def test_missing_delivery_id(self):
        """Test that missing delivery ID is not considered duplicate"""
        assert is_duplicate_delivery(None) is False
    
    def test_ttl_cleanup(self):
        """Test that old deliveries are cleaned up"""
        # Add old delivery
        old_delivery = "old-delivery"
        processed_deliveries[old_delivery] = datetime.now() - timedelta(hours=25)
        
        # Add recent delivery
        recent_delivery = "recent-delivery"
        processed_deliveries[recent_delivery] = datetime.now()
        
        # Run cleanup
        cleanup_old_deliveries()
        
        # Old should be removed, recent should remain
        assert old_delivery not in processed_deliveries
        assert recent_delivery in processed_deliveries


class TestConfigValidation:
    """Test configuration validation"""
    
    def test_valid_config(self):
        """Test that valid config passes validation"""
        import linear_webhook_trigger
        with patch.object(linear_webhook_trigger, 'LINEAR_WEBHOOK_SECRET', "a" * 32):
            assert validate_webhook_config() is True
    
    def test_missing_secret(self):
        """Test that missing secret fails validation"""
        import linear_webhook_trigger
        with patch.object(linear_webhook_trigger, 'LINEAR_WEBHOOK_SECRET', ""):
            assert validate_webhook_config() is False
    
    def test_short_secret_warning(self, caplog):
        """Test that short secret generates warning"""
        import linear_webhook_trigger
        with patch.object(linear_webhook_trigger, 'LINEAR_WEBHOOK_SECRET', "short"):
            result = validate_webhook_config()
            # Should still return True but log warning
            assert result is True
            assert "seems short" in caplog.text.lower()
