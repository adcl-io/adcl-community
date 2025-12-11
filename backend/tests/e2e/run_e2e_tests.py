#!/usr/bin/env python3
# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
E2E Test Runner for ADCL Platform
Runs comprehensive end-to-end tests and generates reports
"""

import asyncio
import argparse
import sys
from datetime import datetime
from pathlib import Path
from test_playground_team import PlaygroundTeamTest
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Test scenarios
TEST_SCENARIOS = [
    {
        "name": "Quick Security Test",
        "team": "test-security-team",
        "task": "Analyze the security of a simple login endpoint at /api/auth/login",
        "timeout": 180,
    },
    {
        "name": "Code Review Test",
        "team": "code-review-team",
        "task": "Review a simple Python function for security vulnerabilities and code quality issues.",
        "timeout": 120,
    },
]


async def run_all_tests(
    base_url: str = "http://localhost:3000",
    api_url: str = "http://localhost:8000",
    scenarios: list = None,
):
    """
    Run all E2E test scenarios

    Args:
        base_url: Frontend URL
        api_url: Backend API URL
        scenarios: List of test scenarios to run (defaults to TEST_SCENARIOS)
    """
    if scenarios is None:
        scenarios = TEST_SCENARIOS

    tester = PlaygroundTeamTest(base_url=base_url, api_url=api_url)

    logger.info(f"Starting E2E tests against {api_url}")
    logger.info(f"Running {len(scenarios)} test scenarios")

    for i, scenario in enumerate(scenarios, 1):
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Test Scenario {i}/{len(scenarios)}: {scenario['name']}")
        logger.info(f"{'=' * 80}")

        try:
            result = await tester.test_team_execution(
                team_name=scenario["team"],
                task=scenario["task"],
                timeout_seconds=scenario.get("timeout", 300),
            )

            status_emoji = {
                "completed": "✅",
                "error": "❌",
                "timeout": "⏱️",
            }.get(result["status"], "❓")

            logger.info(f"Result: {status_emoji} {result['status']}")

        except Exception as e:
            logger.error(f"Test scenario failed: {e}", exc_info=True)

    # Generate and print report
    print("\n")
    tester.print_summary()

    # Save detailed JSON report
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"e2e_report_{timestamp}.json"

    tester.generate_report(report_path)

    logger.info(f"\n📊 Full report saved to: {report_path}")

    # Return exit code based on test results
    failed_count = len([r for r in tester.test_results if r["status"] != "completed"])
    if failed_count > 0:
        logger.error(f"\n❌ {failed_count} test(s) failed")
        return 1
    else:
        logger.info(f"\n✅ All {len(tester.test_results)} tests passed!")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Run ADCL E2E tests")
    parser.add_argument(
        "--base-url",
        default="http://localhost:3000",
        help="Frontend base URL (default: http://localhost:3000)",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Backend API URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--team",
        help="Run single team test instead of all scenarios",
    )
    parser.add_argument(
        "--task",
        help="Task to give the team (required if --team is specified)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout in seconds (default: 300)",
    )

    args = parser.parse_args()

    # Single team test mode
    if args.team:
        if not args.task:
            parser.error("--task is required when --team is specified")

        scenarios = [
            {
                "name": f"Custom Test: {args.team}",
                "team": args.team,
                "task": args.task,
                "timeout": args.timeout,
            }
        ]
    else:
        scenarios = TEST_SCENARIOS

    # Run tests
    exit_code = asyncio.run(
        run_all_tests(
            base_url=args.base_url,
            api_url=args.api_url,
            scenarios=scenarios,
        )
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
