# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Unit Tests for Webhook Signature Verification

Tests HMAC signature verification for GitHub and Linear webhooks,
including timing attack resistance and edge cases.
"""

import pytest
import hmac
import hashlib
import time
from unittest.mock import Mock, patch


class TestGitHubSignatureVerification:
    """Test suite for GitHub webhook signature verification"""

    @pytest.fixture
    def github_secret(self):
        """GitHub webhook secret"""
        return "test_github_secret_key"

    @pytest.fixture
    def sample_payload(self):
        """Sample GitHub webhook payload"""
        return b'{"action":"opened","number":123}'

    def compute_github_signature(self, secret: str, payload: bytes) -> str:
        """Helper to compute valid GitHub signature"""
        mac = hmac.new(
            secret.encode(),
            msg=payload,
            digestmod=hashlib.sha256
        )
        return f"sha256={mac.hexdigest()}"

    def test_valid_github_signature(self, github_secret, sample_payload):
        """Test that valid GitHub signature passes verification"""
        from triggers.webhook.github_webhook_trigger import verify_github_signature

        valid_signature = self.compute_github_signature(github_secret, sample_payload)

        # Mock the secret env var
        with patch('triggers.webhook.github_webhook_trigger.GITHUB_WEBHOOK_SECRET', github_secret):
            result = verify_github_signature(sample_payload, valid_signature)

        assert result is True

    def test_invalid_github_signature(self, github_secret, sample_payload):
        """Test that invalid GitHub signature fails verification"""
        from triggers.webhook.github_webhook_trigger import verify_github_signature

        invalid_signature = "sha256=invalid_signature_hash"

        with patch('triggers.webhook.github_webhook_trigger.GITHUB_WEBHOOK_SECRET', github_secret):
            result = verify_github_signature(sample_payload, invalid_signature)

        assert result is False

    def test_missing_sha256_prefix(self, github_secret, sample_payload):
        """Test that signature without 'sha256=' prefix fails"""
        from triggers.webhook.github_webhook_trigger import verify_github_signature

        # Valid hash but missing prefix
        mac = hmac.new(github_secret.encode(), sample_payload, hashlib.sha256)
        signature_without_prefix = mac.hexdigest()

        with patch('triggers.webhook.github_webhook_trigger.GITHUB_WEBHOOK_SECRET', github_secret):
            result = verify_github_signature(sample_payload, signature_without_prefix)

        assert result is False

    def test_empty_signature_header(self, github_secret, sample_payload):
        """Test that empty signature header fails"""
        from triggers.webhook.github_webhook_trigger import verify_github_signature

        with patch('triggers.webhook.github_webhook_trigger.GITHUB_WEBHOOK_SECRET', github_secret):
            result = verify_github_signature(sample_payload, "")

        assert result is False

    def test_none_signature_header(self, github_secret, sample_payload):
        """Test that None signature header fails"""
        from triggers.webhook.github_webhook_trigger import verify_github_signature

        with patch('triggers.webhook.github_webhook_trigger.GITHUB_WEBHOOK_SECRET', github_secret):
            result = verify_github_signature(sample_payload, None)

        assert result is False

    def test_no_secret_configured(self, sample_payload):
        """Test behavior when no secret is configured"""
        from triggers.webhook.github_webhook_trigger import verify_github_signature

        valid_signature = "sha256=somehash"

        # Empty secret should allow webhooks (warning mode)
        with patch('triggers.webhook.github_webhook_trigger.GITHUB_WEBHOOK_SECRET', ""):
            result = verify_github_signature(sample_payload, valid_signature)

        assert result is True  # Allows through with warning

    def test_timing_attack_resistance(self, github_secret, sample_payload):
        """Test that signature comparison is constant-time"""
        from triggers.webhook.github_webhook_trigger import verify_github_signature

        valid_signature = self.compute_github_signature(github_secret, sample_payload)
        # Create signature that differs only in last character
        invalid_signature_similar = valid_signature[:-1] + "0"
        # Create completely different signature
        invalid_signature_different = "sha256=" + "0" * 64

        with patch('triggers.webhook.github_webhook_trigger.GITHUB_WEBHOOK_SECRET', github_secret):
            # Time both invalid comparisons
            start1 = time.perf_counter()
            result1 = verify_github_signature(sample_payload, invalid_signature_similar)
            time1 = time.perf_counter() - start1

            start2 = time.perf_counter()
            result2 = verify_github_signature(sample_payload, invalid_signature_different)
            time2 = time.perf_counter() - start2

        # Both should fail
        assert result1 is False
        assert result2 is False

        # Timing difference should be minimal (constant-time comparison)
        # Allow 10x difference as threshold (constant-time should be much closer)
        time_ratio = max(time1, time2) / min(time1, time2) if min(time1, time2) > 0 else 1
        assert time_ratio < 10, f"Timing difference suggests non-constant-time comparison: {time_ratio}x"

    def test_different_payload_same_secret(self, github_secret):
        """Test that different payload generates different signature"""
        from triggers.webhook.github_webhook_trigger import verify_github_signature

        payload1 = b'{"action":"opened"}'
        payload2 = b'{"action":"closed"}'

        sig1 = self.compute_github_signature(github_secret, payload1)
        sig2 = self.compute_github_signature(github_secret, payload2)

        assert sig1 != sig2

        # Verify cross-checking fails
        with patch('triggers.webhook.github_webhook_trigger.GITHUB_WEBHOOK_SECRET', github_secret):
            # Signature for payload1 should not validate payload2
            result = verify_github_signature(payload2, sig1)

        assert result is False


class TestLinearSignatureVerification:
    """Test suite for Linear webhook signature verification"""

    @pytest.fixture
    def linear_secret(self):
        """Linear webhook secret"""
        return "test_linear_secret_key"

    @pytest.fixture
    def sample_payload(self):
        """Sample Linear webhook payload"""
        return b'{"type":"agentSession","action":"created"}'

    def compute_linear_signature(self, secret: str, payload: bytes) -> str:
        """Helper to compute valid Linear signature"""
        mac = hmac.new(
            secret.encode(),
            msg=payload,
            digestmod=hashlib.sha256
        )
        return mac.hexdigest()

    def test_valid_linear_signature(self, linear_secret, sample_payload):
        """Test that valid Linear signature passes verification"""
        from triggers.webhook.linear_webhook_trigger import verify_linear_signature

        valid_signature = self.compute_linear_signature(linear_secret, sample_payload)

        with patch('triggers.webhook.linear_webhook_trigger.LINEAR_WEBHOOK_SECRET', linear_secret):
            result = verify_linear_signature(sample_payload, valid_signature)

        assert result is True

    def test_invalid_linear_signature(self, linear_secret, sample_payload):
        """Test that invalid Linear signature fails verification"""
        from triggers.webhook.linear_webhook_trigger import verify_linear_signature

        invalid_signature = "invalid_signature_hash"

        with patch('triggers.webhook.linear_webhook_trigger.LINEAR_WEBHOOK_SECRET', linear_secret):
            result = verify_linear_signature(sample_payload, invalid_signature)

        assert result is False

    def test_linear_no_secret_configured(self, sample_payload):
        """Test Linear webhook with no secret configured (rejects webhook)"""
        from triggers.webhook.linear_webhook_trigger import verify_linear_signature

        with patch('triggers.webhook.linear_webhook_trigger.LINEAR_WEBHOOK_SECRET', ""):
            result = verify_linear_signature(sample_payload, "any_signature")

        assert result is False  # Rejects unsigned webhooks

    def test_linear_empty_signature_header(self, linear_secret, sample_payload):
        """Test Linear webhook with empty signature header"""
        from triggers.webhook.linear_webhook_trigger import verify_linear_signature

        with patch('triggers.webhook.linear_webhook_trigger.LINEAR_WEBHOOK_SECRET', linear_secret):
            result = verify_linear_signature(sample_payload, "")

        assert result is False

    def test_linear_timing_attack_resistance(self, linear_secret, sample_payload):
        """Test that Linear signature comparison is constant-time"""
        from triggers.webhook.linear_webhook_trigger import verify_linear_signature

        valid_signature = self.compute_linear_signature(linear_secret, sample_payload)
        invalid_signature_similar = valid_signature[:-1] + "0"
        invalid_signature_different = "0" * 64

        with patch('triggers.webhook.linear_webhook_trigger.LINEAR_WEBHOOK_SECRET', linear_secret):
            start1 = time.perf_counter()
            result1 = verify_linear_signature(sample_payload, invalid_signature_similar)
            time1 = time.perf_counter() - start1

            start2 = time.perf_counter()
            result2 = verify_linear_signature(sample_payload, invalid_signature_different)
            time2 = time.perf_counter() - start2

        assert result1 is False
        assert result2 is False

        # Timing should be similar (constant-time)
        time_ratio = max(time1, time2) / min(time1, time2) if min(time1, time2) > 0 else 1
        assert time_ratio < 10, f"Timing difference suggests non-constant-time comparison: {time_ratio}x"


class TestDeduplication:
    """Test suite for Linear webhook deduplication"""

    def test_first_delivery_processes(self):
        """Test that first delivery with delivery_id processes"""
        from triggers.webhook.linear_webhook_trigger import is_duplicate_delivery

        delivery_id = "delivery-123"
        result = is_duplicate_delivery(delivery_id)

        assert result is False  # First time, not duplicate

    def test_duplicate_delivery_detected(self):
        """Test that duplicate delivery_id is detected"""
        from triggers.webhook.linear_webhook_trigger import is_duplicate_delivery

        delivery_id = "delivery-456"

        # First delivery
        result1 = is_duplicate_delivery(delivery_id)
        assert result1 is False

        # Second delivery with same ID
        result2 = is_duplicate_delivery(delivery_id)
        assert result2 is True

    def test_none_delivery_id(self):
        """Test that None delivery_id is not considered duplicate"""
        from triggers.webhook.linear_webhook_trigger import is_duplicate_delivery

        result = is_duplicate_delivery(None)

        assert result is False

    def test_empty_delivery_id(self):
        """Test that empty delivery_id is not considered duplicate"""
        from triggers.webhook.linear_webhook_trigger import is_duplicate_delivery

        result = is_duplicate_delivery("")

        assert result is False

    def test_cache_overflow_fifo(self):
        """Test that cache uses TTL-based cleanup instead of size limit"""
        from triggers.webhook.linear_webhook_trigger import is_duplicate_delivery, processed_deliveries
        from datetime import datetime, timedelta

        # Clear cache first
        processed_deliveries.clear()

        # Add some deliveries
        for i in range(10):
            delivery_id = f"delivery-{i}"
            is_duplicate_delivery(delivery_id)

        # Verify all are in cache
        assert len(processed_deliveries) == 10

        # Manually set one to be old (beyond TTL)
        old_delivery = "delivery-0"
        processed_deliveries[old_delivery] = datetime.now() - timedelta(hours=25)

        # Trigger cleanup by adding a new delivery
        is_duplicate_delivery("new-delivery")

        # Old delivery should be cleaned up
        assert old_delivery not in processed_deliveries
        assert "new-delivery" in processed_deliveries


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
