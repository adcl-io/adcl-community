#!/usr/bin/env python3
# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
E2E Test: Team Execution with Performance Metrics
Tests the complete workflow of running a multi-agent team
Records KPIs: execution time, token count, speed, cost
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import httpx
import logging

logger = logging.getLogger(__name__)


class PlaygroundTeamTest:
    """
    End-to-end test for team execution with performance metrics
    Tracks execution time, tokens, cost, throughput
    """

    def __init__(
        self,
        base_url: str = "http://localhost:3000",
        api_url: str = "http://localhost:8000",
    ):
        self.base_url = base_url
        self.api_url = api_url
        self.test_results: List[Dict[str, Any]] = []

        # Load cost estimates from config
        config_path = Path(__file__).parent.parent.parent.parent / "configs" / "runtime.json"
        with open(config_path, 'r') as f:
            config = json.load(f)
            self.cost_estimates = config.get("cost_estimates", {}).get("default", {
                "input_cost_per_1k": 0.03,
                "output_cost_per_1k": 0.06
            })

    async def test_team_execution(
        self,
        team_name: str,
        task: str,
        timeout_seconds: int = 300,
    ) -> Dict[str, Any]:
        """
        Test a team execution and capture performance KPIs

        Args:
            team_name: Name of team to test (e.g., "test-security-team")
            task: Task to give the team
            timeout_seconds: Max time to wait for completion

        Returns:
            Dict with test results and KPIs
        """
        logger.info(f"Starting performance test for team: {team_name}")

        result = {
            "test_name": f"team_{team_name}",
            "team_name": team_name,
            "task": task,
            "status": "running",
            "start_time": datetime.now().isoformat(),
            "kpis": {},
            "errors": [],
        }

        try:
            # Execute team and measure time
            logger.info(f"Executing team: {team_name}")
            start_time = time.time()

            execution_response = await self._execute_team(team_name, task, timeout_seconds)
            execution_time = time.time() - start_time

            # Extract KPIs from response
            kpis = self._extract_kpis(execution_response, execution_time)

            result["status"] = execution_response.get("status", "unknown")
            result["kpis"] = kpis
            result["execution_response"] = execution_response
            result["end_time"] = datetime.now().isoformat()
            result["total_duration_seconds"] = execution_time

            logger.info(f"Test completed with status: {result['status']}")
            logger.info(f"Execution time: {execution_time:.2f}s")
            logger.info(f"KPIs: {json.dumps(kpis, indent=2)}")

        except Exception as e:
            logger.error(f"Test failed with exception: {e}", exc_info=True)
            result["status"] = "error"
            result["errors"].append(str(e))
            result["end_time"] = datetime.now().isoformat()
            result["total_duration_seconds"] = time.time() - start_time

        self.test_results.append(result)
        return result

    async def _execute_team(self, team_name: str, task: str, timeout_seconds: int = 300) -> Dict:
        """Execute a team via API"""
        async with httpx.AsyncClient(timeout=float(timeout_seconds)) as client:
            response = await client.post(
                f"{self.api_url}/teams/run",
                json={
                    "team_id": team_name,
                    "task": task,
                    "context": {}
                },
            )
            response.raise_for_status()
            return response.json()

    def _extract_kpis(
        self, execution_response: Dict, execution_time: float
    ) -> Dict[str, Any]:
        """Extract performance KPIs from execution response"""

        kpis = {
            # Performance metrics
            "execution_time_seconds": round(execution_time, 2),
            "tokens_per_second": 0,

            # Token metrics (will calculate from agent results)
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,

            # Cost metrics (estimated)
            "total_cost_usd": 0.0,
            "cost_per_1k_tokens": 0.0,

            # Agent metrics
            "agent_count": 0,
            "successful_agents": 0,
            "failed_agents": 0,
            "iterations_total": 0,
            "tools_used_count": 0,
            "success_rate": 0.0,
        }

        try:
            agent_results = execution_response.get("agent_results", [])
            kpis["agent_count"] = len(agent_results)

            # Aggregate metrics from all agents
            for agent_result in agent_results:
                # Success tracking
                if agent_result.get("status") == "completed":
                    kpis["successful_agents"] += 1
                else:
                    kpis["failed_agents"] += 1

                # Iteration tracking
                kpis["iterations_total"] += agent_result.get("iterations", 0)

                # Tool usage tracking
                tools = agent_result.get("tools_used", [])
                kpis["tools_used_count"] += len(tools)

                # Token tracking - extract from agent's token_usage if available
                # (This will be added to agent_result in the backend enhancement)
                token_usage = agent_result.get("token_usage", {})
                if token_usage:
                    kpis["total_input_tokens"] += token_usage.get("input_tokens", 0)
                    kpis["total_output_tokens"] += token_usage.get("output_tokens", 0)

            kpis["total_tokens"] = kpis["total_input_tokens"] + kpis["total_output_tokens"]

            # Calculate derived metrics
            if execution_time > 0 and kpis["total_tokens"] > 0:
                kpis["tokens_per_second"] = round(
                    kpis["total_tokens"] / execution_time, 2
                )

            # Estimate cost using config-driven pricing
            if kpis["total_tokens"] > 0:
                input_cost = (kpis["total_input_tokens"] / 1000) * self.cost_estimates["input_cost_per_1k"]
                output_cost = (kpis["total_output_tokens"] / 1000) * self.cost_estimates["output_cost_per_1k"]
                kpis["total_cost_usd"] = round(input_cost + output_cost, 4)
                kpis["cost_per_1k_tokens"] = round(
                    (kpis["total_cost_usd"] / kpis["total_tokens"]) * 1000, 4
                )

            # Success rate
            if kpis["agent_count"] > 0:
                kpis["success_rate"] = round(
                    (kpis["successful_agents"] / kpis["agent_count"]) * 100, 2
                )

        except Exception as e:
            logger.error(f"Error extracting KPIs: {e}", exc_info=True)
            kpis["extraction_error"] = str(e)

        return kpis

    def generate_report(self, output_path: Path = None) -> Dict[str, Any]:
        """Generate test report with KPIs"""
        report = {
            "test_suite": "Team Performance Tests",
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.test_results),
            "passed": len([r for r in self.test_results if r["status"] == "completed"]),
            "failed": len(
                [r for r in self.test_results if r["status"] in ["error", "timeout"]]
            ),
            "tests": self.test_results,
            "summary_kpis": self._calculate_summary_kpis(),
        }

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)
            logger.info(f"Test report saved to {output_path}")

        return report

    def _calculate_summary_kpis(self) -> Dict[str, Any]:
        """Calculate summary KPIs across all tests"""
        if not self.test_results:
            return {}

        completed_tests = [
            r for r in self.test_results if r["status"] == "completed"
        ]

        if not completed_tests:
            return {"note": "No completed tests to summarize"}

        summary = {
            "total_execution_time": sum(
                r["kpis"].get("execution_time_seconds", 0) for r in completed_tests
            ),
            "total_cost": sum(
                r["kpis"].get("total_cost_usd", 0) for r in completed_tests
            ),
            "total_tokens": sum(
                r["kpis"].get("total_tokens", 0) for r in completed_tests
            ),
            "avg_tokens_per_second": (
                sum(r["kpis"].get("tokens_per_second", 0) for r in completed_tests)
                / len(completed_tests)
                if completed_tests
                else 0
            ),
            "avg_success_rate": (
                sum(r["kpis"].get("success_rate", 0) for r in completed_tests)
                / len(completed_tests)
                if completed_tests
                else 0
            ),
            "total_agents_tested": sum(
                r["kpis"].get("agent_count", 0) for r in completed_tests
            ),
        }

        # Round values
        for key in ["total_execution_time", "total_cost", "avg_tokens_per_second", "avg_success_rate"]:
            if key in summary:
                summary[key] = round(summary[key], 2)

        return summary

    def print_summary(self):
        """Print human-readable test summary"""
        print("\n" + "=" * 80)
        print("ADCL Team Performance Test Results")
        print("=" * 80)

        for i, result in enumerate(self.test_results, 1):
            status_emoji = {
                "completed": "✅",
                "error": "❌",
                "timeout": "⏱️",
                "running": "🔄",
            }.get(result["status"], "❓")

            print(f"\nTest #{i}: {result['test_name']} {status_emoji}")
            print(f"  Team: {result['team_name']}")
            print(f"  Status: {result['status']}")
            print(f"  Duration: {result.get('total_duration_seconds', 0):.2f}s")

            if result["status"] == "completed":
                kpis = result.get("kpis", {})
                print(f"\n  📊 Performance KPIs:")
                print(f"    ⏱️  Execution Time: {kpis.get('execution_time_seconds', 0)}s")
                print(f"    🚀 Throughput: {kpis.get('tokens_per_second', 0)} tokens/sec")
                print(f"\n  💰 Cost Metrics:")
                print(f"    💵 Total Cost: ${kpis.get('total_cost_usd', 0):.4f}")
                print(f"    📈 Cost Efficiency: ${kpis.get('cost_per_1k_tokens', 0):.4f} per 1K tokens")
                print(f"\n  🔢 Token Metrics:")
                print(
                    f"    📥 Input Tokens: {kpis.get('total_input_tokens', 0):,}"
                )
                print(
                    f"    📤 Output Tokens: {kpis.get('total_output_tokens', 0):,}"
                )
                print(
                    f"    📊 Total Tokens: {kpis.get('total_tokens', 0):,}"
                )
                print(f"\n  🤖 Agent Metrics:")
                print(f"    👥 Agents: {kpis.get('agent_count', 0)} total")
                print(
                    f"    ✅ Success Rate: {kpis.get('success_rate', 0)}% ({kpis.get('successful_agents', 0)} succeeded)"
                )
                print(f"    🔄 Total Iterations: {kpis.get('iterations_total', 0)}")
                print(f"    🛠️  Tools Used: {kpis.get('tools_used_count', 0)}")

            if result.get("errors"):
                print(f"\n  ❌ Errors:")
                for error in result["errors"]:
                    print(f"    • {error}")

        # Print summary
        summary = self._calculate_summary_kpis()
        if summary and "note" not in summary:
            print("\n" + "-" * 80)
            print("📊 Summary Across All Tests")
            print("-" * 80)
            print(f"  ⏱️  Total Execution Time: {summary['total_execution_time']}s")
            print(f"  💵 Total Cost: ${summary['total_cost']:.4f}")
            print(f"  📊 Total Tokens: {summary['total_tokens']:,}")
            print(f"  🚀 Average Throughput: {summary['avg_tokens_per_second']} tokens/sec")
            print(f"  ✅ Average Success Rate: {summary['avg_success_rate']}%")
            print(f"  👥 Total Agents Tested: {summary['total_agents_tested']}")

        print("\n" + "=" * 80 + "\n")


# Convenience function
async def run_team_test(
    team_name: str = "test-security-team",
    task: str = "Analyze the security of a simple web application.",
    timeout: int = 300,
) -> Dict[str, Any]:
    """Run a single team test"""
    tester = PlaygroundTeamTest()
    result = await tester.test_team_execution(team_name, task, timeout)
    tester.print_summary()

    # Save report
    output_dir = Path(__file__).parent / "results"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"performance_report_{timestamp}.json"
    tester.generate_report(report_path)

    return result


if __name__ == "__main__":
    asyncio.run(
        run_team_test(
            team_name="test-security-team",
            task="Perform a basic security assessment of a REST API endpoint.",
        )
    )
