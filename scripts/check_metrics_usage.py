#!/usr/bin/env python3
"""
Detect Prometheus metrics defined but never used.

Scans src/ for metric definitions and checks if they are actually used
(via .inc(), .observe(), .set() calls) and tested.

Usage:
    python3 scripts/check_metrics_usage.py
    python3 scripts/check_metrics_usage.py --help

Exit codes:
    0 - All metrics are used
    1 - One or more metrics are unused
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple


class MetricInfo(NamedTuple):
    name: str
    var_name: str
    metric_type: str
    file_path: str
    line_num: int


def run_rg(pattern: str, path: str = "src/") -> list[str]:
    """Run ripgrep and return output lines."""
    try:
        result = subprocess.run(
            ["rg", pattern, path, "--no-heading", "--line-number"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip().split("\n") if result.stdout.strip() else []
    except FileNotFoundError:
        # Fallback to grep if rg not available
        result = subprocess.run(
            ["grep", "-rn", "-E", pattern, path],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip().split("\n") if result.stdout.strip() else []


def find_metric_definitions() -> list[MetricInfo]:
    """Find all Prometheus metric definitions in src/."""
    metrics = []

    # Pattern: var_name = Counter(...) or Histogram(...) or Gauge(...)
    pattern = r'(Counter|Histogram|Gauge)\('
    lines = run_rg(pattern)

    for line in lines:
        if not line:
            continue

        # Parse: file:line_num:content
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue

        file_path, line_num, content = parts[0], parts[1], parts[2]

        # Extract variable name (e.g., "answer_requests_total = Counter(...)")
        var_match = re.search(r'(\w+)\s*=\s*(Counter|Histogram|Gauge)\(', content)
        if not var_match:
            continue

        var_name = var_match.group(1)
        metric_type = var_match.group(2)

        # Extract metric name from first string argument
        name_match = re.search(r'(Counter|Histogram|Gauge)\(\s*["\']([^"\']+)["\']', content)
        metric_name = name_match.group(2) if name_match else var_name

        metrics.append(MetricInfo(
            name=metric_name,
            var_name=var_name,
            metric_type=metric_type,
            file_path=file_path,
            line_num=int(line_num),
        ))

    return metrics


def check_metric_usage(metric: MetricInfo) -> tuple[bool, bool]:
    """
    Check if metric is used and tested.

    Returns:
        (is_used, is_tested)
    """
    # Check for usage in src/ - handle both single-line and multi-line patterns
    # Pattern 1: metric.inc() or metric.observe() or metric.set()
    # Pattern 2: metric.labels(...).inc() (may span multiple lines)

    is_used = False

    # First check: direct method call (metric.inc())
    method_name = get_method_name(metric.metric_type)
    direct_pattern = rf'{metric.var_name}\.{method_name}\('
    lines = run_rg(direct_pattern)
    if lines and lines[0]:
        is_used = True

    # Second check: labels() followed by method call (may be multi-line)
    # Just check if metric.labels( exists - if it does, assume it's used
    if not is_used:
        labels_pattern = rf'{metric.var_name}\.labels\('
        lines = run_rg(labels_pattern)
        if lines and lines[0]:
            is_used = True

    # Check for tests
    is_tested = False
    test_lines = run_rg(metric.var_name, "tests/")
    if test_lines and test_lines[0]:
        is_tested = True

    return is_used, is_tested


def main() -> int:
    """Main entry point."""
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return 0

    print("Checking Prometheus metrics usage...\n")

    metrics = find_metric_definitions()

    if not metrics:
        print("✅ No metrics found (or unable to scan)")
        return 0

    critical_issues = []
    warnings = []

    for metric in metrics:
        is_used, is_tested = check_metric_usage(metric)

        if not is_used:
            critical_issues.append(
                f"❌ CRITICAL: {metric.var_name} - defined but never used "
                f"(no .{get_method_name(metric.metric_type)}() call found)"
            )
        elif not is_tested:
            warnings.append(
                f"⚠️  WARNING:  {metric.var_name} - no test verifies it is "
                f"{get_method_name(metric.metric_type)}ed"
            )

    # Print results
    for issue in critical_issues:
        print(issue)

    for warning in warnings:
        print(warning)

    # Summary
    print(f"\nSummary: {len(critical_issues)} critical, {len(warnings)} warning(s)")

    return 1 if critical_issues else 0


def get_method_name(metric_type: str) -> str:
    """Get the method name for a metric type."""
    return {
        "Counter": "inc",
        "Histogram": "observe",
        "Gauge": "set",
    }.get(metric_type, "update")


if __name__ == "__main__":
    sys.exit(main())
