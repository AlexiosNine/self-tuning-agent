#!/usr/bin/env python3
"""
Master script for automated bug detection.

Runs all checks and produces a unified report with severity levels.

Usage:
    python3 scripts/auto_bug_detection.py
    python3 scripts/auto_bug_detection.py --help

Checks performed:
1. Prometheus metrics usage validation
2. @retry decorator test coverage
3. asyncio.run() usage inside async contexts
4. Unsafe int()/float() conversions without try-except
5. Potentially unsafe path construction patterns

Exit codes:
    0 - No critical issues found
    1 - One or more critical issues found
"""

import subprocess
import sys
from pathlib import Path


def run_check(script_name: str) -> tuple[int, str]:
    """Run a check script and return exit code and output."""
    try:
        result = subprocess.run(
            ["python", script_name],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode, result.stdout
    except Exception as e:
        return 1, f"Error running {script_name}: {e}"


def check_asyncio_run() -> list[str]:
    """Check for asyncio.run() inside async functions."""
    issues = []
    try:
        result = subprocess.run(
            ["rg", r"asyncio\.run\(", "src/", "--no-heading", "--line-number"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                parts = line.split(":", 2)
                if len(parts) >= 3:
                    file_path, line_num, content = parts[0], parts[1], parts[2]
                    issues.append(
                        f"  [{file_path}:{line_num}]\n"
                        f"       asyncio.run() detected: {content.strip()}\n"
                        f"       → Consider using await directly"
                    )
    except FileNotFoundError:
        pass
    return issues


def check_unsafe_conversions() -> list[str]:
    """Check for int()/float() without try-except."""
    issues = []
    try:
        # Find int( and float( calls
        result = subprocess.run(
            ["rg", r"\b(int|float)\(", "src/", "--no-heading", "--line-number", "-A", "5"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.stdout.strip():
            lines = result.stdout.strip().split("\n")
            i = 0
            while i < len(lines):
                line = lines[i]
                parts = line.split(":", 2)
                if len(parts) >= 3:
                    file_path, line_num, content = parts[0], parts[1], parts[2]

                    # Check next 5 lines for try-except
                    has_try_except = False
                    for j in range(max(0, i - 5), min(len(lines), i + 5)):
                        if "try:" in lines[j] or "except" in lines[j]:
                            has_try_except = True
                            break

                    if not has_try_except and ("int(" in content or "float(" in content):
                        issues.append(
                            f"  [{file_path}:{line_num}]\n"
                            f"       {content.strip()}\n"
                            f"       → Wrap in try-except ValueError"
                        )
                i += 1
    except FileNotFoundError:
        pass
    return issues


def check_path_construction() -> list[str]:
    """Check for unsafe path construction."""
    issues = []
    try:
        # Find path construction with user input
        result = subprocess.run(
            ["rg", r'(Path|\/)\s*\w+_id|user_input', "src/", "--no-heading", "--line-number"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                parts = line.split(":", 2)
                if len(parts) >= 3:
                    file_path, line_num, content = parts[0], parts[1], parts[2]
                    # Check if validation exists nearby
                    if "resolve()" not in content and "is_relative_to" not in content:
                        issues.append(
                            f"  [{file_path}:{line_num}]\n"
                            f"       {content.strip()}\n"
                            f"       → Validate path to prevent traversal"
                        )
    except FileNotFoundError:
        pass
    return issues


def main() -> int:
    """Main entry point."""
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return 0

    print("╔══════════════════════════════════════════╗")
    print("║     Auto Bug Detection Report            ║")
    print("╚══════════════════════════════════════════╝\n")

    critical_issues = []
    warnings = []
    info_issues = []

    # Run metrics check
    exit_code, output = run_check("scripts/check_metrics_usage.py")
    if exit_code != 0:
        for line in output.split("\n"):
            if "CRITICAL" in line:
                critical_issues.append(f"  [Metrics] {line}")
            elif "WARNING" in line:
                warnings.append(f"  [Metrics] {line}")

    # Run retry check
    exit_code, output = run_check("scripts/check_retry_coverage.py")
    if exit_code != 0:
        for line in output.split("\n"):
            if "MISSING" in line:
                warnings.append(f"  [Retry] {line}")

    # Run additional checks
    asyncio_issues = check_asyncio_run()
    if asyncio_issues:
        warnings.extend(asyncio_issues)

    conversion_issues = check_unsafe_conversions()
    if conversion_issues:
        warnings.extend(conversion_issues)

    path_issues = check_path_construction()
    if path_issues:
        warnings.extend(path_issues)

    # Print results
    print(f"🔴 CRITICAL ({len(critical_issues)} issues)")
    if critical_issues:
        for issue in critical_issues:
            print(issue)
    else:
        print("  None found ✓")

    print(f"\n🟡 WARNING ({len(warnings)} issues)")
    if warnings:
        for i, issue in enumerate(warnings, 1):
            print(f"  [W{i}] {issue}")
    else:
        print("  None found ✓")

    print(f"\n🟢 INFO ({len(info_issues)} issues)")
    if info_issues:
        for i, issue in enumerate(info_issues, 1):
            print(f"  [I{i}] {issue}")
    else:
        print("  None found ✓")

    # Summary
    print("\n══════════════════════════════════════════")
    print(f"Total: {len(critical_issues)} critical, {len(warnings)} warnings, {len(info_issues)} info")

    if critical_issues:
        print("Status: ❌ FAILED (critical issues found)")
        return 1
    else:
        print("Status: ✅ PASSED (no critical issues)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
