#!/usr/bin/env python3
"""
Detect @retry decorators without test coverage.

Scans src/ for @retry decorators and checks if tests verify:
1. Retry is triggered on expected exceptions
2. Retry exhaustion is tested

Usage:
    python3 scripts/check_retry_coverage.py
    python3 scripts/check_retry_coverage.py --help

Exit codes:
    0 - All retry decorators have test coverage
    1 - One or more retry decorators lack tests
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple


class RetryInfo(NamedTuple):
    function_name: str
    class_name: str | None
    file_path: str
    line_num: int
    retry_exceptions: list[str]


def run_rg(pattern: str, path: str = "src/", context: int = 0) -> list[str]:
    """Run ripgrep and return output lines."""
    try:
        cmd = ["rg", pattern, path, "--no-heading", "--line-number"]
        if context > 0:
            cmd.extend(["-A", str(context)])
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.stdout.strip().split("\n") if result.stdout.strip() else []
    except FileNotFoundError:
        # Fallback to grep
        cmd = ["grep", "-rn", "-E", pattern, path]
        if context > 0:
            cmd.extend(["-A", str(context)])
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.stdout.strip().split("\n") if result.stdout.strip() else []


def find_retry_decorators() -> list[RetryInfo]:
    """Find all @retry decorators in src/."""
    retries = []

    # Find @retry decorators with context
    lines = run_rg(r'@retry\(', context=10)

    i = 0
    while i < len(lines):
        line = lines[i]
        if not line or "@retry(" not in line:
            i += 1
            continue

        # Parse file:line_num:content
        parts = line.split(":", 2)
        if len(parts) < 3:
            i += 1
            continue

        file_path, line_num, content = parts[0], parts[1], parts[2]

        # Look ahead for function definition
        function_name = None
        class_name = None
        retry_exceptions = []

        # Extract retry exceptions from decorator
        j = i
        decorator_lines = []
        while j < len(lines) and j < i + 10:
            decorator_lines.append(lines[j])
            if "def " in lines[j]:
                func_match = re.search(r'def\s+(\w+)\s*\(', lines[j])
                if func_match:
                    function_name = func_match.group(1)
                break
            j += 1

        # Extract exception types from retry_if_exception_type
        decorator_text = "\n".join(decorator_lines)
        exc_match = re.search(r'retry_if_exception_type\(\(([^)]+)\)\)', decorator_text)
        if exc_match:
            exc_str = exc_match.group(1)
            retry_exceptions = [e.strip() for e in exc_str.split(",")]

        # Try to find class name (look backwards in file)
        try:
            with open(file_path) as f:
                file_lines = f.readlines()
                for k in range(int(line_num) - 1, max(0, int(line_num) - 50), -1):
                    if k < len(file_lines):
                        class_match = re.search(r'class\s+(\w+)', file_lines[k])
                        if class_match:
                            class_name = class_match.group(1)
                            break
        except (FileNotFoundError, ValueError):
            pass

        if function_name:
            retries.append(RetryInfo(
                function_name=function_name,
                class_name=class_name,
                file_path=file_path,
                line_num=int(line_num),
                retry_exceptions=retry_exceptions,
            ))

        i = j + 1

    return retries


def check_retry_tests(retry: RetryInfo) -> tuple[bool, bool]:
    """
    Check if retry has test coverage.

    Returns:
        (has_trigger_test, has_exhaustion_test)
    """
    # Build function identifier
    if retry.class_name:
        func_id = f"{retry.class_name}.{retry.function_name}"
    else:
        func_id = retry.function_name

    # Check for tests that mention this function
    test_lines = run_rg(func_id, "tests/")

    if not test_lines or not test_lines[0]:
        return False, False

    # Check for retry trigger test (side_effect with exceptions)
    has_trigger = False
    has_exhaustion = False

    for line in test_lines:
        if "side_effect" in line.lower():
            has_trigger = True
        if "retry" in line.lower() or "attempt" in line.lower():
            has_exhaustion = True

    return has_trigger, has_exhaustion


def main() -> int:
    """Main entry point."""
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return 0

    print("Checking @retry decorator test coverage...\n")

    retries = find_retry_decorators()

    if not retries:
        print("✅ No @retry decorators found (or unable to scan)")
        return 0

    missing_tests = []

    for retry in retries:
        has_trigger, has_exhaustion = check_retry_tests(retry)

        func_id = f"{retry.class_name}.{retry.function_name}" if retry.class_name else retry.function_name

        if not has_trigger:
            exc_str = ", ".join(retry.retry_exceptions) if retry.retry_exceptions else "exceptions"
            missing_tests.append(
                f"❌ MISSING: {func_id}() - no test verifies retry triggers on {exc_str}"
            )

        if not has_exhaustion:
            missing_tests.append(
                f"❌ MISSING: {func_id}() - no test verifies retry exhaustion"
            )

    # Print results
    for issue in missing_tests:
        print(issue)

    # Summary
    print(f"\nSummary: {len(missing_tests)} missing retry test(s)")

    return 1 if missing_tests else 0


if __name__ == "__main__":
    sys.exit(main())
