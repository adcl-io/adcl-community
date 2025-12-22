# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""Unit tests for ZAP MCP Server"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from mcp_servers.zap.zap_server import ZapMCPServer


@pytest.fixture
def mock_zap_process():
    """Mock ZAP process for testing"""
    with patch('subprocess.Popen') as mock_popen, \
         patch('requests.get') as mock_get:
        
        # Mock process
        mock_proc = Mock()
        mock_proc.poll.return_value = None  # Process running
        mock_popen.return_value = mock_proc
        
        # Mock health check responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        yield mock_proc


@pytest.fixture
def zap_server(mock_zap_process):
    """ZAP MCP server instance for testing"""
    with patch('mcp_servers.zap.zap_server.ZAPv2') as mock_zap_client:
        mock_client = Mock()
        mock_zap_client.return_value = mock_client
        
        server = ZapMCPServer(port=7008)
        server.zap = mock_client
        
        yield server


@pytest.mark.asyncio
async def test_start_proxy(zap_server):
    """Test: ZAP proxy starts successfully"""
    result = await zap_server.start_proxy(port=8080)
    
    assert result["status"] == "running"
    assert "proxy_url" in result


@pytest.mark.asyncio
async def test_get_urls_empty(zap_server):
    """Test: get_urls returns empty list initially"""
    zap_server.zap.core.urls.return_value = []
    
    urls = await zap_server.get_urls()
    
    assert isinstance(urls["urls"], list)
    assert urls["count"] == 0


@pytest.mark.asyncio
async def test_active_scan_start(zap_server):
    """Test: Active scan starts successfully"""
    os.environ["ALLOWED_SCAN_TARGETS"] = "http://localhost:*"
    zap_server.zap.ascan.scan.return_value = "12345"
    
    result = await zap_server.active_scan(
        target="http://localhost:3000/api/test",
        scan_policy="Light"
    )
    
    assert "scan_id" in result
    assert result["status"] == "started"


@pytest.mark.asyncio
async def test_get_scan_status(zap_server):
    """Test: Scan status returns progress"""
    zap_server.zap.ascan.status.return_value = "50"
    
    status = await zap_server.get_scan_status(scan_id="12345")
    
    assert "progress" in status
    assert status["progress"] == 50
    assert status["status"] == "running"


@pytest.mark.asyncio
async def test_get_alerts(zap_server):
    """Test: get_alerts returns alert structure"""
    zap_server.zap.core.alerts.return_value = [
        {"risk": "3", "alert": "SQL Injection"},
        {"risk": "2", "alert": "XSS"}
    ]
    
    alerts = await zap_server.get_alerts(risk_level="High")
    
    assert "alerts" in alerts
    assert isinstance(alerts["alerts"], list)
    assert len(alerts["alerts"]) == 1  # Only High risk


@pytest.mark.asyncio
async def test_generate_report(zap_server):
    """Test: Report generation"""
    zap_server.zap.core.alerts.return_value = []
    zap_server.zap.core.urls.return_value = []
    
    report = await zap_server.generate_report(format="json")
    
    assert "alerts" in report
    assert "urls" in report


@pytest.mark.asyncio
async def test_target_whitelist_validation(zap_server):
    """Test: Target whitelist enforcement"""
    os.environ["ALLOWED_SCAN_TARGETS"] = "http://localhost:*"
    
    # Should fail - not in whitelist
    with pytest.raises(ValueError, match="not in whitelist"):
        await zap_server.active_scan(target="http://evil.com")
    
    # Should succeed - in whitelist
    zap_server.zap.ascan.scan.return_value = "12345"
    result = await zap_server.active_scan(target="http://localhost:3000")
    assert result["status"] == "started"


@pytest.mark.asyncio
async def test_scan_policy_validation(zap_server):
    """Test: scan_policy input validation"""
    os.environ["ALLOWED_SCAN_TARGETS"] = "http://localhost:*"
    
    # Should fail - invalid policy
    with pytest.raises(ValueError, match="Invalid scan_policy"):
        await zap_server.active_scan(
            target="http://localhost:3000",
            scan_policy="InvalidPolicy"
        )
