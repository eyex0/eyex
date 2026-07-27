"""Run all performance benchmarks and generate a report."""
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

if __name__ == "__main__":
    start = time.perf_counter()
    exit_code = pytest.main([
        "tests/benchmarks/",
        "-v",
        "--tb=short",
        "--no-header",
        "-q",
    ])
    elapsed = time.perf_counter() - start
    print(f"\n{'='*60}")
    print(f"Benchmark suite completed in {elapsed:.2f}s")
    print(f"{'='*60}")
    sys.exit(exit_code)
