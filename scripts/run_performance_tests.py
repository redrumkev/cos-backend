#!/usr/bin/env python3
"""Performance Test Runner for Task 15.2.

Runs comprehensive performance-, resource-usage-, and failure-scenario test
suites to validate COS production readiness.
"""

# ruff: noqa

from __future__ import annotations

import argparse
import contextlib
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Standard library
from typing import Any

# Third-party
from rich.console import Console

# Rich console for consistent CLI output (no styling/markup needed here).
console: Console = Console(highlight=False, markup=False)


class PerformanceTestRunner:
    """Coordinates execution of performance tests and generates reports."""

    def __init__(self, verbose: bool = False):
        self.verbose: bool = verbose
        self.project_root: Path = Path(__file__).parent.parent
        self.test_results: dict[str, dict[str, Any]] = {}
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None

    def run_test_suite(self, test_pattern: str, description: str) -> dict[str, Any]:
        """Run a specific test suite and capture results."""
        console.print(f"\n🧪 Running {description}...")

        cmd = ["uv", "run", "pytest", f"tests/performance/{test_pattern}", "-v", "--tb=short"]

        if self.verbose:
            cmd.append("-s")

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            duration = time.time() - start_time

            # Parse test results
            success = result.returncode == 0
            output_lines = result.stdout.split("\n")

            # Extract test count from pytest output
            test_count = 0
            passed_count = 0
            failed_count = 0

            for line in output_lines:
                if "passed" in line and "failed" not in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "passed":
                            with contextlib.suppress(ValueError, IndexError):
                                passed_count = int(parts[i - 1])
                elif "failed" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "failed":
                            with contextlib.suppress(ValueError, IndexError):
                                failed_count = int(parts[i - 1])

            test_count = passed_count + failed_count

            return {
                "success": success,
                "duration": duration,
                "test_count": test_count,
                "passed": passed_count,
                "failed": failed_count,
                "output": result.stdout if self.verbose else "",
                "errors": result.stderr if result.stderr else "",
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "duration": 300,
                "test_count": 0,
                "passed": 0,
                "failed": 1,
                "output": "",
                "errors": "Test suite timed out after 5 minutes",
            }
        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "test_count": 0,
                "passed": 0,
                "failed": 1,
                "output": "",
                "errors": str(e),
            }

    def check_infrastructure(self) -> dict[str, Any]:
        """Check that all required infrastructure services are running."""
        console.print("🔍 Checking infrastructure status...")

        try:
            docker_cmd = shutil.which("docker") or "docker"
            result = subprocess.run(
                [docker_cmd, "ps", "--format", "table {{.Names}}\t{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return {"success": False, "error": "Docker not available"}

            output = result.stdout
            required_services = [
                "cos_redis",
                "cos_postgres_dev",
                "cos_postgres_prod",
                "cos_traefik",
                "cos_elasticsearch",
                "cos_neo4j",
            ]

            running_services = []
            for line in output.split("\n")[1:]:  # Skip header
                if line.strip():
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        status = parts[1].strip()
                        if any(req in name for req in required_services):
                            running_services.append({"name": name, "status": status})

            all_healthy = all("Up" in service["status"] for service in running_services)

            return {
                "success": all_healthy,
                "services": running_services,
                "required_count": len(required_services),
                "running_count": len(running_services),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_full_test_suite(self) -> None:
        """Run the complete performance test suite."""
        self.start_time = datetime.now()

        console.print("🚀 Starting COS Performance Test Suite - Task 15.2")
        console.print(f"📅 Started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Check infrastructure first
        infra_status = self.check_infrastructure()
        self.test_results["infrastructure"] = infra_status

        if not infra_status["success"]:
            console.print("❌ Infrastructure check failed!")
            console.print(f"Error: {infra_status.get('error', 'Unknown error')}")
            return

        console.print(f"✅ Infrastructure healthy - {infra_status['running_count']} services running")

        # Define test suites
        test_suites = [
            {
                "pattern": "test_production_readiness.py::TestRedisPerformance",
                "description": "Redis Performance Benchmarks",
                "key": "redis_performance",
            },
            {
                "pattern": "test_production_readiness.py::TestMemoryAndResourceUsage",
                "description": "Memory & Resource Usage Tests",
                "key": "memory_resources",
            },
            {
                "pattern": "test_production_readiness.py::TestFailureScenarios",
                "description": "Failure Scenario & Recovery Tests",
                "key": "failure_scenarios",
            },
        ]

        # Run each test suite
        total_tests = 0
        total_passed = 0
        total_failed = 0

        for suite in test_suites:
            result = self.run_test_suite(suite["pattern"], suite["description"])
            self.test_results[suite["key"]] = result

            total_tests += result["test_count"]
            total_passed += result["passed"]
            total_failed += result["failed"]

            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            console.print(
                f"{status} - {result['passed']}/{result['test_count']} tests passed in {result['duration']:.1f}s"
            )

            if result["errors"]:
                console.print(f"⚠️  Errors: {result['errors']}")

        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()

        # Overall results
        overall_success = all(
            result["success"]
            for result in self.test_results.values()
            if isinstance(result, dict) and "success" in result
        )

        console.print(f"\n📊 Test Suite Complete in {duration:.1f}s")
        console.print(f"📈 Overall Results: {total_passed}/{total_tests} tests passed")

        if overall_success:
            console.print("🎉 ALL TESTS PASSED - System is Production Ready!")
        else:
            console.print("💥 SOME TESTS FAILED - Review results before production deployment")

        self.test_results["summary"] = {
            "overall_success": overall_success,
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "duration": duration,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
        }

    def run_quick_test_suite(self) -> None:
        """Run abbreviated test suite for quick validation."""
        self.start_time = datetime.now()

        console.print("⚡ Starting Quick Performance Validation")

        # Check infrastructure
        infra_status = self.check_infrastructure()
        self.test_results["infrastructure"] = infra_status

        if not infra_status["success"]:
            console.print("❌ Infrastructure check failed!")
            return

        console.print("✅ Infrastructure healthy")

        # Run key performance tests
        quick_tests = [
            {
                "pattern": "test_production_readiness.py::TestRedisPerformance::test_redis_latency_performance",
                "description": "Redis Latency Check",
                "key": "redis_latency",
            },
            {
                "pattern": "test_production_readiness.py::TestRedisPerformance::test_redis_throughput_performance",
                "description": "Redis Throughput Check",
                "key": "redis_throughput",
            },
        ]

        total_passed = 0
        total_tests = 0

        for test in quick_tests:
            result = self.run_test_suite(test["pattern"], test["description"])
            self.test_results[test["key"]] = result

            total_tests += result["test_count"]
            total_passed += result["passed"]

            status = "✅" if result["success"] else "❌"
            console.print(f"{status} {test['description']}")

        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()

        overall_success = total_passed == total_tests

        console.print(f"\n⚡ Quick validation complete in {duration:.1f}s")
        console.print(f"📈 Results: {total_passed}/{total_tests} tests passed")

        if overall_success:
            console.print("✅ Core performance validated - System ready for full testing")
        else:
            console.print("❌ Performance issues detected - Review before proceeding")

    def generate_report(self) -> None:
        """Generate a summary report of test results."""
        if not self.test_results:
            console.print("⚠️  No test results available for report generation")
            return

        console.print("\n📋 PERFORMANCE TEST REPORT - TASK 15.2")
        console.print("=" * 60)

        if "summary" in self.test_results:
            summary = self.test_results["summary"]
            console.print(f"🕐 Test Duration: {summary['duration']:.1f} seconds")
            console.print(f"📊 Test Results: {summary['total_passed']}/{summary['total_tests']} passed")
            console.print(f"🎯 Overall Status: {'✅ PASS' if summary['overall_success'] else '❌ FAIL'}")

        console.print("\n📈 Component Test Results:")

        for key, result in self.test_results.items():
            if key in ["infrastructure", "summary"]:
                continue

            if isinstance(result, dict) and "success" in result:
                status = "✅ PASS" if result["success"] else "❌ FAIL"
                console.print(
                    f"  {key.replace('_', ' ').title()}: {status} ({result['passed']}/{result['test_count']} tests)"
                )

        # Infrastructure status
        if "infrastructure" in self.test_results:
            infra = self.test_results["infrastructure"]
            if infra["success"]:
                console.print(f"\n🔧 Infrastructure: ✅ All {infra['running_count']} services healthy")
            else:
                console.print(f"\n🔧 Infrastructure: ❌ {infra.get('error', 'Services not ready')}")

        console.print("\n" + "=" * 60)

        # Save detailed report
        report_file = self.project_root / "tests" / "performance" / "latest_test_results.json"
        try:
            with report_file.open("w") as f:
                json.dump(self.test_results, f, indent=2, default=str)
            console.print(f"📄 Detailed results saved to: {report_file}")
        except Exception as e:
            console.print(f"⚠️  Failed to save detailed report: {e}")


def main() -> None:
    """Run the performance test runner CLI."""
    parser = argparse.ArgumentParser(
        description="COS Performance Test Runner - Task 15.2", formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed test output")

    parser.add_argument(
        "--report-only", action="store_true", help="Generate report from existing results without running tests"
    )

    parser.add_argument("--quick", "-q", action="store_true", help="Run abbreviated test suite for quick validation")

    args = parser.parse_args()

    runner = PerformanceTestRunner(verbose=args.verbose)

    if args.report_only:
        # Try to load existing results
        report_file = runner.project_root / "tests" / "performance" / "latest_test_results.json"
        if report_file.exists():
            try:
                with report_file.open() as f:
                    runner.test_results = json.load(f)
                runner.generate_report()
                return
            except Exception as e:
                console.print(f"❌ Failed to load existing results: {e}")
                sys.exit(1)
        else:
            console.print("❌ No existing test results found")
            sys.exit(1)

    # Run tests
    try:
        if args.quick:
            runner.run_quick_test_suite()
        else:
            runner.run_full_test_suite()

        runner.generate_report()

        # Exit with appropriate code
        if "summary" in runner.test_results:
            sys.exit(0 if runner.test_results["summary"]["overall_success"] else 1)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n🛑 Test execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        console.print(f"💥 Unexpected error during test execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
