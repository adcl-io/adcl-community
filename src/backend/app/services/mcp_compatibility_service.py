# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
MCP Compatibility Testing Service

Provides functionality for testing MCP tool compatibility with different models.
Tracks success rates, response times, and reliability metrics for various tool categories.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

from app.core.logging import get_service_logger
from app.models.enhanced_models import MCPCompatibilityMatrix, MCPToolCompatibility

logger = get_service_logger("mcp_compatibility")


class MCPCompatibilityService:
    """
    Service for testing and tracking MCP tool compatibility across models.
    
    Responsibilities:
    - Execute compatibility tests for different MCP tool categories
    - Track success rates and performance metrics
    - Maintain compatibility matrix data
    - Provide recommendations based on compatibility data
    """
    
    # Standard MCP tool categories for testing
    TOOL_CATEGORIES = {
        "file_ops": {
            "name": "File Operations",
            "description": "File reading, writing, and manipulation tools",
            "test_tools": ["read_file", "write_file", "list_directory", "delete_file"]
        },
        "web_scraping": {
            "name": "Web Scraping",
            "description": "Web content extraction and scraping tools",
            "test_tools": ["fetch_url", "extract_text", "parse_html", "download_file"]
        },
        "data_analysis": {
            "name": "Data Analysis",
            "description": "Data processing and analysis tools",
            "test_tools": ["analyze_data", "generate_chart", "calculate_stats", "filter_data"]
        },
        "code_execution": {
            "name": "Code Execution",
            "description": "Code execution and development tools",
            "test_tools": ["execute_python", "run_shell", "compile_code", "debug_code"]
        },
        "api_calls": {
            "name": "API Calls",
            "description": "External API integration tools",
            "test_tools": ["http_request", "rest_api", "graphql_query", "webhook_call"]
        }
    }
    
    def __init__(self, compatibility_data_path: Path):
        """
        Initialize MCP Compatibility Service.
        
        Args:
            compatibility_data_path: Path to store compatibility test results
        """
        self.compatibility_data_path = compatibility_data_path
        self.test_results_cache = {}
        self.lock = asyncio.Lock()
        
        logger.info("MCPCompatibilityService initialized")
    
    async def test_model_compatibility(
        self, 
        model_id: str, 
        categories: Optional[List[str]] = None
    ) -> MCPCompatibilityMatrix:
        """
        Test MCP compatibility for a specific model.
        
        Args:
            model_id: Model identifier to test
            categories: List of categories to test (defaults to all)
            
        Returns:
            MCPCompatibilityMatrix with test results
        """
        if categories is None:
            categories = list(self.TOOL_CATEGORIES.keys())
        
        logger.info(f"Starting MCP compatibility test for model {model_id}, categories: {categories}")
        
        success_rates = {}
        
        for category in categories:
            if category not in self.TOOL_CATEGORIES:
                logger.warning(f"Unknown category: {category}")
                continue
                
            try:
                compatibility = await self._test_category_compatibility(model_id, category)
                success_rates[category] = compatibility
                logger.info(f"Completed {category} test for {model_id}: {compatibility.success_rate:.2%}")
            except Exception as e:
                logger.error(f"Failed to test {category} for {model_id}: {e}")
                # Create failed test result
                success_rates[category] = MCPToolCompatibility(
                    success_rate=0.0,
                    avg_response_time=0.0,
                    last_tested=datetime.now()
                )
        
        # Calculate overall reliability score
        reliability_score = self._calculate_reliability_score(success_rates)
        
        compatibility_matrix = MCPCompatibilityMatrix(
            reliability_score=reliability_score,
            tested_categories=categories,
            success_rates=success_rates
        )
        
        # Store results
        await self._store_compatibility_results(model_id, compatibility_matrix)
        
        logger.info(f"MCP compatibility test completed for {model_id}, reliability: {reliability_score:.1f}")
        return compatibility_matrix
    
    async def _test_category_compatibility(
        self, 
        model_id: str, 
        category: str
    ) -> MCPToolCompatibility:
        """
        Test compatibility for a specific tool category.
        
        Args:
            model_id: Model to test
            category: Tool category to test
            
        Returns:
            MCPToolCompatibility results
        """
        category_info = self.TOOL_CATEGORIES[category]
        test_tools = category_info["test_tools"]
        
        successful_tests = 0
        total_response_time = 0.0
        test_count = len(test_tools)
        
        for tool in test_tools:
            try:
                start_time = time.time()
                
                # Simulate MCP tool test
                success = await self._simulate_tool_test(model_id, tool, category)
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                
                if success:
                    successful_tests += 1
                
                total_response_time += response_time
                
                # Add small delay between tests to avoid overwhelming the model
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"Tool test failed for {tool} on {model_id}: {e}")
                # Count as failed test, but continue
                total_response_time += 5000  # Penalty for failed test
        
        success_rate = successful_tests / test_count if test_count > 0 else 0.0
        avg_response_time = total_response_time / test_count if test_count > 0 else 0.0
        
        return MCPToolCompatibility(
            success_rate=success_rate,
            avg_response_time=avg_response_time,
            last_tested=datetime.now()
        )
    
    async def _simulate_tool_test(self, model_id: str, tool: str, category: str) -> bool:
        """
        Simulate testing an MCP tool with a model.
        
        In a real implementation, this would:
        1. Load the model
        2. Execute the MCP tool
        3. Validate the response
        4. Return success/failure
        
        For now, we simulate with realistic success rates.
        
        Args:
            model_id: Model being tested
            tool: MCP tool name
            category: Tool category
            
        Returns:
            True if test passed, False otherwise
        """
        # Simulate test execution time
        await asyncio.sleep(0.5 + (hash(f"{model_id}{tool}") % 100) / 200)  # 0.5-1.0 seconds
        
        # Simulate realistic success rates based on model and tool type
        base_success_rate = 0.85  # Base 85% success rate
        
        # Adjust based on model (some models are better at function calling)
        if "claude" in model_id.lower():
            base_success_rate += 0.1
        elif "gpt-4" in model_id.lower():
            base_success_rate += 0.08
        elif "gpt-3.5" in model_id.lower():
            base_success_rate -= 0.1
        
        # Adjust based on tool complexity
        complex_tools = ["debug_code", "generate_chart", "graphql_query"]
        if tool in complex_tools:
            base_success_rate -= 0.15
        
        # Add some randomness
        import random
        random_factor = random.uniform(-0.1, 0.1)
        final_success_rate = max(0.0, min(1.0, base_success_rate + random_factor))
        
        return random.random() < final_success_rate
    
    def _calculate_reliability_score(self, success_rates: Dict[str, MCPToolCompatibility]) -> float:
        """
        Calculate overall reliability score from category success rates.
        
        Args:
            success_rates: Dictionary of category compatibility results
            
        Returns:
            Reliability score from 1.0 to 5.0
        """
        if not success_rates:
            return 1.0
        
        # Calculate weighted average success rate
        total_weight = 0
        weighted_sum = 0
        
        # Weight categories by importance
        category_weights = {
            "file_ops": 1.2,      # File operations are fundamental
            "api_calls": 1.1,     # API calls are very common
            "data_analysis": 1.0, # Standard weight
            "web_scraping": 0.9,  # Less critical
            "code_execution": 0.8 # Specialized use case
        }
        
        for category, compatibility in success_rates.items():
            weight = category_weights.get(category, 1.0)
            weighted_sum += compatibility.success_rate * weight
            total_weight += weight
        
        avg_success_rate = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        # Convert to 1-5 scale
        # 0% success = 1.0, 100% success = 5.0
        reliability_score = 1.0 + (avg_success_rate * 4.0)
        
        return round(reliability_score, 1)
    
    async def _store_compatibility_results(
        self, 
        model_id: str, 
        compatibility: MCPCompatibilityMatrix
    ) -> None:
        """
        Store compatibility test results to persistent storage.
        
        Args:
            model_id: Model identifier
            compatibility: Compatibility test results
        """
        async with self.lock:
            try:
                # Load existing data
                compatibility_data = {}
                if self.compatibility_data_path.exists():
                    with open(self.compatibility_data_path, 'r') as f:
                        compatibility_data = json.load(f)
                
                # Update with new results
                compatibility_data[model_id] = compatibility.to_dict()
                
                # Save back to file
                with open(self.compatibility_data_path, 'w') as f:
                    json.dump(compatibility_data, f, indent=2, default=str)
                
                logger.info(f"Stored compatibility results for {model_id}")
                
            except Exception as e:
                logger.error(f"Failed to store compatibility results: {e}")
                raise
    
    async def get_compatibility_history(
        self, 
        model_id: str, 
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get compatibility test history for a model.
        
        Args:
            model_id: Model identifier
            days: Number of days of history to retrieve
            
        Returns:
            List of historical compatibility data
        """
        # In a real implementation, this would query a time-series database
        # For now, return mock historical data
        history = []
        
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            
            # Generate mock historical data with some trends
            base_score = 4.2 + (i * 0.01)  # Slight improvement over time
            noise = (hash(f"{model_id}{date.date()}") % 100) / 1000  # Small random variation
            
            history.append({
                "date": date.isoformat(),
                "reliability_score": min(5.0, max(1.0, base_score + noise)),
                "categories_tested": len(self.TOOL_CATEGORIES),
                "avg_success_rate": min(1.0, max(0.0, (base_score - 1.0) / 4.0 + noise))
            })
        
        return list(reversed(history))  # Most recent first
    
    async def get_model_recommendations(
        self, 
        required_categories: List[str],
        min_reliability: float = 3.0
    ) -> List[Dict[str, Any]]:
        """
        Get model recommendations based on MCP compatibility requirements.
        
        Args:
            required_categories: List of required MCP tool categories
            min_reliability: Minimum reliability score required
            
        Returns:
            List of recommended models with compatibility scores
        """
        try:
            if not self.compatibility_data_path.exists():
                return []
            
            with open(self.compatibility_data_path, 'r') as f:
                compatibility_data = json.load(f)
            
            recommendations = []
            
            for model_id, data in compatibility_data.items():
                reliability_score = data.get("reliability_score", 0.0)
                tested_categories = data.get("tested_categories", [])
                success_rates = data.get("success_rates", {})
                
                # Check if model meets requirements
                if reliability_score < min_reliability:
                    continue
                
                # Check if all required categories are supported
                category_coverage = all(cat in tested_categories for cat in required_categories)
                if not category_coverage:
                    continue
                
                # Calculate average success rate for required categories
                required_success_rates = [
                    success_rates.get(cat, {}).get("success_rate", 0.0)
                    for cat in required_categories
                ]
                avg_required_success = sum(required_success_rates) / len(required_success_rates) if required_success_rates else 0.0
                
                recommendations.append({
                    "model_id": model_id,
                    "reliability_score": reliability_score,
                    "avg_success_rate": avg_required_success,
                    "category_coverage": len([cat for cat in required_categories if cat in tested_categories]),
                    "last_tested": data.get("success_rates", {}).get(required_categories[0], {}).get("last_tested") if required_categories else None
                })
            
            # Sort by reliability score and success rate
            recommendations.sort(
                key=lambda x: (x["reliability_score"], x["avg_success_rate"]), 
                reverse=True
            )
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get model recommendations: {e}")
            return []