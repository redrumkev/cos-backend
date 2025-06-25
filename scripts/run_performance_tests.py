#!/usr/bin/env python3
# ruff: noqa: T201, S603, S607, SIM105, PTH123, D205, D400, D415, D401, F841, B007
# mypy: ignore-errors
"""Performance Test Runner for Task 15.2
COS Phase 2 Sprint 2 - Production Readiness Validation

This script runs comprehensive performance benchmarking and failure scenario testing
to validate system readiness for production deployment.

Style bypasses applied for performance test runner:
- F841/B007: Unused variables and loop controls (common in test parsing)
- Additional style bypasses inherited from base configuration

Usage:
    python scripts/run_performance_tests.py [--verbose] [--report-only]

Options:
    --verbose     Show detailed test output
    --report-only Generate report without running tests
    --quick       Run abbreviated test suite for faster validation
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


class PerformanceTestRunner:
    """Coordinates execution of performance tests and generates reports."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.project_root = Path(__file__).parent.parent
        self.test_results = {}
        self.start_time = None
        self.end_time = None

    def run_test_suite(self, test_pattern: str, description: str) -> dict:
        """Run a specific test suite and capture results."""
        print(f"\n🧪 Running {description}...")

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
                    # Look for pattern like "3 passed in 0.72s"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "passed":
                            try:
                                passed_count = int(parts[i - 1])
                            except (ValueError, IndexError):
                                pass
                elif "failed" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "failed":
                            try:
                                failed_count = int(parts[i - 1])
                            except (ValueError, IndexError):
                                pass

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

    def check_infrastructure(self) -> dict:
        """Check that all required infrastructure services are running."""
        print("🔍 Checking infrastructure status...")

        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}"],
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

        print("🚀 Starting COS Performance Test Suite - Task 15.2")
        print(f"📅 Started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Check infrastructure first
        infra_status = self.check_infrastructure()
        self.test_results["infrastructure"] = infra_status

        if not infra_status["success"]:
            print("❌ Infrastructure check failed!")
            print(f"Error: {infra_status.get('error', 'Unknown error')}")
            return

        print(f"✅ Infrastructure healthy - {infra_status['running_count']} services running")

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
            print(f"{status} - {result['passed']}/{result['test_count']} tests passed in {result['duration']:.1f}s")

            if result["errors"]:
                print(f"⚠️  Errors: {result['errors']}")

        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()

        # Overall results
        overall_success = all(
            result["success"]
            for result in self.test_results.values()
            if isinstance(result, dict) and "success" in result
        )

        print(f"\n📊 Test Suite Complete in {duration:.1f}s")
        print(f"📈 Overall Results: {total_passed}/{total_tests} tests passed")

        if overall_success:
            print("🎉 ALL TESTS PASSED - System is Production Ready!")
        else:
            print("💥 SOME TESTS FAILED - Review results before production deployment")

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

        print("⚡ Starting Quick Performance Validation")

        # Check infrastructure
        infra_status = self.check_infrastructure()
        self.test_results["infrastructure"] = infra_status

        if not infra_status["success"]:
            print("❌ Infrastructure check failed!")
            return

        print("✅ Infrastructure healthy")

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
            print(f"{status} {test['description']}")

        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()

        overall_success = total_passed == total_tests

        print(f"\n⚡ Quick validation complete in {duration:.1f}s")
        print(f"📈 Results: {total_passed}/{total_tests} tests passed")

        if overall_success:
            print("✅ Core performance validated - System ready for full testing")
        else:
            print("❌ Performance issues detected - Review before proceeding")

    def generate_report(self) -> None:
        """Generate a summary report of test results."""
        if not self.test_results:
            print("⚠️  No test results available for report generation")
            return

        print("\n📋 PERFORMANCE TEST REPORT - TASK 15.2")
        print("=" * 60)

        if "summary" in self.test_results:
            summary = self.test_results["summary"]
            print(f"🕐 Test Duration: {summary['duration']:.1f} seconds")
            print(f"📊 Test Results: {summary['total_passed']}/{summary['total_tests']} passed")
            print(f"🎯 Overall Status: {'✅ PASS' if summary['overall_success'] else '❌ FAIL'}")

        print("\n📈 Component Test Results:")

        for key, result in self.test_results.items():
            if key in ["infrastructure", "summary"]:
                continue

            if isinstance(result, dict) and "success" in result:
                status = "✅ PASS" if result["success"] else "❌ FAIL"
                print(f"  {key.replace('_', ' ').title()}: {status} ({result['passed']}/{result['test_count']} tests)")

        # Infrastructure status
        if "infrastructure" in self.test_results:
            infra = self.test_results["infrastructure"]
            if infra["success"]:
                print(f"\n🔧 Infrastructure: ✅ All {infra['running_count']} services healthy")
            else:
                print(f"\n🔧 Infrastructure: ❌ {infra.get('error', 'Services not ready')}")

        print("\n" + "=" * 60)

        # Save detailed report
        report_file = self.project_root / "tests" / "performance" / "latest_test_results.json"
        try:
            with open(report_file, "w") as f:
                json.dump(self.test_results, f, indent=2, default=str)
            print(f"📄 Detailed results saved to: {report_file}")
        except Exception as e:
            print(f"⚠️  Failed to save detailed report: {e}")


def main():
    """Main entry point for performance test runner."""
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
                with open(report_file) as f:
                    runner.test_results = json.load(f)
                runner.generate_report()
                return
            except Exception as e:
                print(f"❌ Failed to load existing results: {e}")
                sys.exit(1)
        else:
            print("❌ No existing test results found")
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
        print("\n🛑 Test execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Unexpected error during test execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
