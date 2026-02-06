#!/usr/bin/env python3
"""Validate repository structure and imports."""
import os
import sys

def check_file(path, description):
    exists = os.path.exists(path)
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {path}")
    return exists

def main():
    print("=" * 60)
    print("REPOSITORY STRUCTURE VALIDATION")
    print("=" * 60)
    
    checks = [
        ("src/features/strategy.py", "V2 Strategy (MUST EXIST)"),
        ("src/bot/main.py", "Live Trading Entry Point"),
        ("scripts/backtest/backtest_enhanced_v2.py", "V2 Backtest"),
        ("scripts/trading/dry_run.py", "Paper Trading"),
        ("results/slippage_test_results.txt", "Slippage Results"),
        ("archive/v1_baseline/README.md", "V1 Archive Docs"),
        ("VERSION.txt", "Version Marker"),
        ("QUICK_START.md", "Quick Reference"),
    ]
    
    passed = sum(check_file(path, desc) for path, desc in checks)
    total = len(checks)
    
    print("=" * 60)
    print(f"RESULT: {passed}/{total} checks passed")
    
    if passed == total:
        print("✅ Repository structure is CORRECT")
        return 0
    else:
        print("❌ Repository structure has ISSUES")
        return 1

if __name__ == "__main__":
    sys.exit(main())
