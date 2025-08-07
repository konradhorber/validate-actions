#!/usr/bin/env python3
"""End-to-end tests using official GitHub Actions workflows.
Test script for official GitHub workflows.

This script processes the official workflows in tests/fixtures/workflows/official_workflows/
and provides detailed analysis and debugging capabilities without interfering
with the main test suite.
"""


import argparse
import json
import logging
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

# Add the project root to sys.path so we can import validate_actions
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import validate_actions  # noqa: E402
from validate_actions import ProblemLevel  # noqa: E402
from validate_actions.globals.fixer import NoFixer  # noqa: E402
from validate_actions.globals.web_fetcher import WebFetcher  # noqa: E402
from validate_actions.pipeline import Pipeline  # noqa: E402


class WorkflowTestResult:
    """Represents the result of testing a single workflow."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.success = False
        self.processing_time = 0.0
        self.problems: List[validate_actions.Problem] = []
        self.exception: Optional[Exception] = None

    @property
    def error_count(self) -> int:
        return sum(1 for p in self.problems if p.level == ProblemLevel.ERR)

    @property
    def warning_count(self) -> int:
        return sum(1 for p in self.problems if p.level == ProblemLevel.WAR)

    @property
    def status(self) -> str:
        if self.exception:
            return "EXCEPTION"
        elif self.error_count > 0:
            return "FAIL"
        elif self.warning_count > 0:
            return "WARN"
        else:
            return "PASS"


class OfficialWorkflowTester:
    """Main testing class for official workflows."""

    def __init__(self, debug: bool = False, verbose: bool = False):
        self.debug = debug
        self.verbose = verbose
        self.setup_logging()
        self.results: List[WorkflowTestResult] = []

    def setup_logging(self):
        """Configure logging based on debug/verbose settings."""
        level = logging.DEBUG if self.debug else logging.INFO
        format_str = "%(asctime)s - %(levelname)s - %(message)s" if self.debug else "%(message)s"

        logging.basicConfig(level=level, format=format_str, handlers=[logging.StreamHandler()])
        self.logger = logging.getLogger(__name__)

    def get_workflow_files(
        self, base_path: Path, specific_workflow: Optional[str] = None
    ) -> List[Path]:
        """
        Get list of workflow files to test.

        Returns list of file paths.
        """
        workflow_files = []

        if specific_workflow:
            # Test specific workflow
            workflow_path = base_path / specific_workflow
            if workflow_path.exists():
                workflow_files.append(workflow_path)
            else:
                self.logger.error(f"Workflow not found: {specific_workflow}")
                return []
        else:
            # Get all workflows recursively
            for workflow_file in base_path.rglob("*.yml"):
                workflow_files.append(workflow_file)
            for workflow_file in base_path.rglob("*.yaml"):
                workflow_files.append(workflow_file)

        return sorted(workflow_files)

    def test_single_workflow(self, file_path: Path) -> WorkflowTestResult:
        """Test a single workflow file and return detailed results."""
        result = WorkflowTestResult(file_path)
        start_time = time.time()

        try:
            self.logger.debug(f"Processing {file_path.relative_to(file_path.parents[4])}")

            # Use the pipeline to process the workflow
            web_fetcher = WebFetcher()
            fixer = NoFixer()
            pipe = Pipeline(web_fetcher, fixer)

            problems = pipe.process(file_path)

            result.problems = problems.problems
            result.success = result.error_count == 0

            if self.verbose or self.debug:
                self.log_workflow_details(result)

        except Exception as e:
            result.exception = e
            self.logger.error(f"Exception processing {file_path.name}: {e}")
            if self.debug:
                import traceback

                self.logger.debug(traceback.format_exc())

        result.processing_time = time.time() - start_time
        return result

    def log_workflow_details(self, result: WorkflowTestResult):
        """Log detailed information for a workflow result."""
        rel_path = result.file_path.relative_to(result.file_path.parents[4])
        status_symbol = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗", "EXCEPTION": "💥"}

        symbol = status_symbol.get(result.status, "?")
        self.logger.info(f"{symbol} {rel_path} ({result.processing_time:.3f}s)")

        if result.problems:
            for problem in result.problems:
                level_symbol = "✗" if problem.level == ProblemLevel.ERR else "⚠"
                self.logger.info(f"  {level_symbol} Line {problem.pos.line}: {problem.desc}")

    def run_tests(
        self, workflows_dir: Path, specific_workflow: Optional[str] = None
    ) -> List[WorkflowTestResult]:
        """Run tests on selected workflows."""
        workflow_files = self.get_workflow_files(workflows_dir, specific_workflow)

        if not workflow_files:
            self.logger.error("No workflow files found to test")
            return []

        self.logger.info(f"Testing {len(workflow_files)} workflows...")

        self.results = []
        for file_path in workflow_files:
            result = self.test_single_workflow(file_path)
            self.results.append(result)

        return self.results

    def generate_summary(self) -> Dict:
        """Generate summary statistics from test results."""
        if not self.results:
            return {}

        summary: Dict = {
            "total_workflows": len(self.results),
            "by_status": defaultdict(int),
            "total_problems": 0,
            "total_errors": 0,
            "total_warnings": 0,
            "processing_time": sum(r.processing_time for r in self.results),
            "slowest_workflows": [],
            "most_problematic": [],
        }

        for result in self.results:
            summary["by_status"][result.status] += 1
            summary["total_problems"] += len(result.problems)
            summary["total_errors"] += result.error_count
            summary["total_warnings"] += result.warning_count

        # Get slowest workflows
        summary["slowest_workflows"] = [
            {
                "file": str(r.file_path.relative_to(r.file_path.parents[4])),
                "time": r.processing_time,
            }
            for r in sorted(self.results, key=lambda x: x.processing_time, reverse=True)[:5]
        ]

        # Get most problematic workflows
        summary["most_problematic"] = [
            {
                "file": str(r.file_path.relative_to(r.file_path.parents[4])),
                "errors": r.error_count,
                "warnings": r.warning_count,
            }
            for r in sorted(
                self.results, key=lambda x: (x.error_count, x.warning_count), reverse=True
            )[:10]
            if r.error_count > 0 or r.warning_count > 0
        ]

        return summary

    def print_summary(self):
        """Print a human-readable summary of test results."""
        summary = self.generate_summary()

        if not summary:
            print("No test results to summarize")
            return

        print(f"\n{'='*60}")
        print("OFFICIAL WORKFLOWS TEST SUMMARY")
        print(f"{'='*60}")

        print(f"Total workflows tested: {summary['total_workflows']}")
        print(f"Processing time: {summary['processing_time']:.2f}s")
        print()

        print("Results by status:")
        for status, count in summary["by_status"].items():
            percentage = (count / summary["total_workflows"]) * 100
            print(f"  {status}: {count} ({percentage:.1f}%)")
        print()

        print(f"Total problems found: {summary['total_problems']}")
        print(f"  Errors: {summary['total_errors']}")
        print(f"  Warnings: {summary['total_warnings']}")

        if summary["most_problematic"]:
            print("\nMost problematic workflows:")
            for item in summary["most_problematic"]:
                print(f"  {item['file']}: {item['errors']} errors, {item['warnings']} warnings")

        if summary["slowest_workflows"]:
            print("\nSlowest workflows:")
            for item in summary["slowest_workflows"]:
                print(f"  {item['file']}: {item['time']:.3f}s")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Test official GitHub workflows for validation issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test all workflows
  python scripts/test_official_workflows.py

  # Test specific workflow
  python scripts/test_official_workflows.py --workflow ci/python-app.yml

  # Debug mode with verbose output
  python scripts/test_official_workflows.py --debug --verbose --workflow ci/python-app.yml

  # Export results to JSON
  python scripts/test_official_workflows.py --output results.json
        """,
    )

    parser.add_argument("--workflow", help="Test specific workflow (e.g., 'ci/python-app.yml')")

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output with per-workflow details"
    )

    parser.add_argument("--output", "-o", help="Output results to JSON file")

    args = parser.parse_args()

    # Find the workflows directory
    script_dir = Path(__file__).parent
    workflows_dir = script_dir.parent / "fixtures" / "workflows" / "official_workflows"

    if not workflows_dir.exists():
        print(f"Error: Official workflows directory not found at {workflows_dir}")
        sys.exit(1)

    # Create tester and run tests
    tester = OfficialWorkflowTester(debug=args.debug, verbose=args.verbose)
    results = tester.run_tests(workflows_dir, specific_workflow=args.workflow)

    if not results:
        sys.exit(1)

    # Print summary
    tester.print_summary()

    # Export to JSON if requested
    if args.output:
        summary = tester.generate_summary()
        summary["detailed_results"] = [
            {
                "file": str(r.file_path.relative_to(r.file_path.parents[4])),
                "status": r.status,
                "processing_time": r.processing_time,
                "error_count": r.error_count,
                "warning_count": r.warning_count,
                "problems": [
                    {
                        "line": p.pos.line,
                        "column": p.pos.col,
                        "level": p.level.name,
                        "message": p.desc,
                    }
                    for p in r.problems
                ],
            }
            for r in results
        ]

        with open(args.output, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\nDetailed results exported to {args.output}")

    # Exit with appropriate code
    summary = tester.generate_summary()
    if summary["by_status"]["EXCEPTION"] > 0 or summary["by_status"]["FAIL"] > 0:
        sys.exit(1)
    elif summary["by_status"]["WARN"] > 0:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
