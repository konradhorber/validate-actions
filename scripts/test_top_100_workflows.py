#!/usr/bin/env python3
"""
Test script for top-100 GitHub workflows.

This script processes all workflows in scripts/top-100-workflows/
and provides detailed analysis and debugging capabilities.
# Test all workflows
python scripts/test_top_100_workflows.py

# Test specific repository
python scripts/test_top_100_workflows.py --repo facebook_react

# Test specific workflow across all repos
python scripts/test_top_100_workflows.py --workflow ci.yml

# Debug specific workflow
python scripts/test_top_100_workflows.py --repo facebook_react
--workflow ci.yml --debug --verbose

# Export results to JSON
python scripts/test_top_100_workflows.py --output results.json
"""

import argparse
import json
import logging
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()
# Add the project root to sys.path so we can import validate_actions
sys.path.insert(0, str(Path(__file__).parent.parent))

from validate_actions.cli import StandardCLI  # noqa: E402
from validate_actions.globals.cli_config import CLIConfig  # noqa: E402


class WorkflowTestResult:
    """Represents the result of testing a single workflow."""

    def __init__(self, file_path: Path, repo_name: str = ""):
        self.file_path = file_path
        self.repo_name = repo_name
        self.success = False
        self.processing_time = 0.0
        self.error_count = 0
        self.warning_count = 0
        self.exception: Optional[Exception] = None
        self.exit_code = 0

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


class Top100WorkflowTester:
    """Main testing class for top-100 workflows."""

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
        self, base_path: Path, specific_workflow: Optional[str] = None, repo: Optional[str] = None
    ) -> List[tuple[Path, str]]:
        """
        Get list of workflow files to test.

        Returns list of (file_path, repo_name) tuples.
        """
        workflow_files = []

        # Get all workflow files from the flattened directory
        all_workflows = []
        for workflow_file in base_path.glob("*.yml"):
            all_workflows.append(workflow_file)
        for workflow_file in base_path.glob("*.yaml"):
            all_workflows.append(workflow_file)

        if specific_workflow:
            # Test specific workflow by name
            if repo:
                # Look for files starting with repo name and containing workflow name
                matching_files = [
                    f for f in all_workflows
                    if f.name.startswith(f"{repo}_") and specific_workflow in f.name
                ]
                if matching_files:
                    for workflow_file in matching_files:
                        repo_name = self._extract_repo_name(workflow_file.name)
                        workflow_files.append((workflow_file, repo_name))
                else:
                    self.logger.error(f"Workflow not found: {repo}/{specific_workflow}")
                    return []
            else:
                # Search for any workflow containing the specific name
                matching_files = [f for f in all_workflows if specific_workflow in f.name]
                if matching_files:
                    for workflow_file in matching_files:
                        repo_name = self._extract_repo_name(workflow_file.name)
                        workflow_files.append((workflow_file, repo_name))
                else:
                    self.logger.error(f"Workflow not found: {specific_workflow}")
                    return []
        elif repo:
            # Test all workflows from specific repo
            repo_files = [f for f in all_workflows if f.name.startswith(f"{repo}_")]
            if repo_files:
                for workflow_file in repo_files:
                    repo_name = self._extract_repo_name(workflow_file.name)
                    workflow_files.append((workflow_file, repo_name))
            else:
                self.logger.error(f"No workflows found for repository: {repo}")
                return []
        else:
            # Get all workflows
            for workflow_file in all_workflows:
                repo_name = self._extract_repo_name(workflow_file.name)
                workflow_files.append((workflow_file, repo_name))

        return sorted(workflow_files, key=lambda x: (x[1], x[0].name))

    def _extract_repo_name(self, filename: str) -> str:
        """Extract repository name from filename prefix."""
        # Files are now named like: facebook_react_ci.yml
        parts = filename.split('_')
        if len(parts) >= 2:
            # Take first two parts as repo name (handles cases like ant-design_ant-design)
            return '_'.join(parts[:2])
        return parts[0] if parts else "unknown"

    def test_single_workflow(self, file_path: Path, repo_name: str) -> WorkflowTestResult:
        """Test a single workflow file and return detailed results."""
        result = WorkflowTestResult(file_path, repo_name)
        start_time = time.time()

        try:
            self.logger.debug(f"Processing {repo_name}/{file_path.name}")

            # Create CLI config for single file validation
            config = CLIConfig(
                workflow_file=str(file_path),
                fix=False,
                github_token=os.getenv("GH_TOKEN"),
                max_warnings=sys.maxsize
            )

            # Use StandardCLI to validate the single file
            cli = StandardCLI(config)
            result.exit_code = cli._run_single_file(file_path)

            # Extract error and warning counts from aggregator
            result.error_count = cli.aggregator.get_total_errors()
            result.warning_count = cli.aggregator.get_total_warnings()
            result.success = result.error_count == 0

            if self.verbose or self.debug:
                self.log_workflow_details(result)

        except Exception as e:
            result.exception = e
            self.logger.error(f"Exception processing {repo_name}/{file_path.name}: {e}")
            if self.debug:
                import traceback
                self.logger.debug(traceback.format_exc())

        result.processing_time = time.time() - start_time
        return result

    def log_workflow_details(self, result: WorkflowTestResult):
        """Log detailed information for a workflow result."""
        status_symbol = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗", "EXCEPTION": "💥"}
        symbol = status_symbol.get(result.status, "?")

        self.logger.info(
            f"{symbol} {result.repo_name}/{result.file_path.name} "
            f"({result.processing_time:.3f}s) - "
            f"Errors: {result.error_count}, Warnings: {result.warning_count}"
        )

    def run_tests(
        self,
        workflows_dir: Path,
        specific_workflow: Optional[str] = None,
        repo: Optional[str] = None
    ) -> List[WorkflowTestResult]:
        """Run tests on selected workflows."""
        workflow_files = self.get_workflow_files(
            workflows_dir, specific_workflow, repo
        )

        if not workflow_files:
            self.logger.error("No workflow files found to test")
            return []

        self.logger.info(f"Testing {len(workflow_files)} workflows...")

        self.results = []
        for file_path, repo_name in workflow_files:
            result = self.test_single_workflow(file_path, repo_name)
            self.results.append(result)

        return self.results

    def generate_summary(self) -> Dict:
        """Generate summary statistics from test results."""
        if not self.results:
            return {}

        summary: Dict = {
            "total_workflows": len(self.results),
            "by_status": defaultdict(int),
            "by_repo": defaultdict(
                lambda: {"total": 0, "pass": 0, "warn": 0, "fail": 0, "exception": 0}
            ),
            "total_errors": sum(r.error_count for r in self.results),
            "total_warnings": sum(r.warning_count for r in self.results),
            "processing_time": sum(r.processing_time for r in self.results),
            "slowest_workflows": [],
            "most_problematic": [],
        }

        for result in self.results:
            status = result.status
            summary["by_status"][status] += 1

            repo_stats = summary["by_repo"][result.repo_name]
            repo_stats["total"] += 1
            repo_stats[status.lower()] += 1

        # Get slowest workflows
        summary["slowest_workflows"] = [
            {
                "file": f"{r.repo_name}/{r.file_path.name}",
                "time": r.processing_time,
            }
            for r in sorted(self.results, key=lambda x: x.processing_time, reverse=True)[:10]
        ]

        # Get most problematic workflows
        summary["most_problematic"] = [
            {
                "file": f"{r.repo_name}/{r.file_path.name}",
                "errors": r.error_count,
                "warnings": r.warning_count,
            }
            for r in sorted(
                self.results, key=lambda x: (x.error_count, x.warning_count), reverse=True
            )[:15]
            if r.error_count > 0 or r.warning_count > 0
        ]

        return summary

    def print_summary(self):
        """Print a human-readable summary of test results."""
        summary = self.generate_summary()

        if not summary:
            print("No test results to summarize")
            return

        print(f"\n{'='*70}")
        print("TOP-100 WORKFLOWS TEST SUMMARY")
        print(f"{'='*70}")

        print(f"Total workflows tested: {summary['total_workflows']}")
        print(f"Processing time: {summary['processing_time']:.2f}s")
        print()

        print("Results by status:")
        for status, count in summary["by_status"].items():
            percentage = (count / summary["total_workflows"]) * 100
            print(f"  {status}: {count} ({percentage:.1f}%)")
        print()

        print("Total problems found:")
        print(f"  Errors: {summary['total_errors']}")
        print(f"  Warnings: {summary['total_warnings']}")
        print()

        if summary["by_repo"]:
            print("Results by repository (top 10 by total workflows):")
            sorted_repos = sorted(
                summary["by_repo"].items(),
                key=lambda x: x[1]["total"],
                reverse=True
            )[:10]
            for repo_name, stats in sorted_repos:
                print(f"  {repo_name}: {stats['total']} workflows "
                      f"({stats['pass']} pass, {stats['warn']} warn, "
                      f"{stats['fail']} fail, {stats['exception']} exception)")

        if summary["most_problematic"]:
            print("\nMost problematic workflows (top 15):")
            for item in summary["most_problematic"]:
                print(f"  {item['file']}: {item['errors']} errors, {item['warnings']} warnings")

        if summary["slowest_workflows"]:
            print("\nSlowest workflows (top 10):")
            for item in summary["slowest_workflows"]:
                print(f"  {item['file']}: {item['time']:.3f}s")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Test top-100 GitHub workflows for validation issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test all workflows
  python scripts/test_top_100_workflows.py

  # Test specific repository
  python scripts/test_top_100_workflows.py --repo facebook_react

  # Test specific workflow
  python scripts/test_top_100_workflows.py --workflow ci.yml

  # Test specific workflow in specific repo
  python scripts/test_top_100_workflows.py --repo facebook_react \
    --workflow runtime_build_and_test.yml

  # Debug mode with verbose output
  python scripts/test_top_100_workflows.py --debug --verbose --repo facebook_react

  # Export results to JSON
  python scripts/test_top_100_workflows.py --output results.json
        """,
    )

    parser.add_argument(
        "--repo", help="Test workflows from specific repository (e.g., 'facebook_react')"
    )
    parser.add_argument("--workflow", help="Test specific workflow (e.g., 'ci.yml')")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output with per-workflow details"
    )
    parser.add_argument("--output", "-o", help="Output results to JSON file")

    args = parser.parse_args()

    # Find the workflows directory
    script_dir = Path(__file__).parent
    workflows_dir = script_dir / "top-100-workflows"

    if not workflows_dir.exists():
        print(f"Error: Top-100 workflows directory not found at {workflows_dir}")
        print("Please ensure the 'top-100-workflows' directory exists in the scripts folder.")
        sys.exit(1)

    # Create tester and run tests
    tester = Top100WorkflowTester(debug=args.debug, verbose=args.verbose)
    results = tester.run_tests(workflows_dir, specific_workflow=args.workflow, repo=args.repo)

    if not results:
        sys.exit(1)

    # Print summary
    tester.print_summary()

    # Export to JSON if requested
    if args.output:
        summary = tester.generate_summary()
        summary["detailed_results"] = [
            {
                "file": f"{r.repo_name}/{r.file_path.name}",
                "repo": r.repo_name,
                "status": r.status,
                "processing_time": r.processing_time,
                "error_count": r.error_count,
                "warning_count": r.warning_count,
                "exit_code": r.exit_code,
            }
            for r in results
        ]

        output_path = Path(args.output)
        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\nDetailed results exported to {output_path}")

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
