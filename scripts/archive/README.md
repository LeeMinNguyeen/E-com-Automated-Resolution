# Archived Test Scripts

This folder contains older test scripts that have been consolidated into `test_comprehensive.py`.

## Archived Files

### test_all_functions.py
- **Purpose**: Tests all MCP functions with different user scenarios
- **Replaced by**: `test_comprehensive.py` (includes all functionality plus more)
- **Status**: Kept for reference

### test_mcp_integration.py
- **Purpose**: Tests MCP server and client integration
- **Replaced by**: `test_comprehensive.py` Suite 1 (MCP Server & Client Integration)
- **Status**: Kept for reference

### test_refund_logic.py
- **Purpose**: Tests refund eligibility and processing logic
- **Replaced by**: `test_comprehensive.py` Suite 2 (Refund Logic)
- **Status**: Kept for reference

### test_human_alert_fix.py
- **Purpose**: Quick test for human intervention alerts
- **Replaced by**: `test_comprehensive.py` Suite 4 (Human Intervention)
- **Status**: Kept for reference

## Why Were These Archived?

Having multiple test scripts was:
- ❌ Confusing - users didn't know which to run
- ❌ Redundant - testing the same features multiple times
- ❌ Inconsistent - different output formats and test methods
- ❌ Time-consuming - had to run multiple scripts

The new `test_comprehensive.py` provides:
- ✅ Single entry point for all tests
- ✅ Consistent output format
- ✅ Command-line options for targeted testing
- ✅ Better organization and documentation
- ✅ Complete coverage of all features

## Using the New Comprehensive Test

```bash
# Run all tests
python scripts/test_comprehensive.py

# Run only quick tests
python scripts/test_comprehensive.py --quick

# Test only MCP integration
python scripts/test_comprehensive.py --mcp-only

# Test only refund logic
python scripts/test_comprehensive.py --refund
```

## If You Need the Old Scripts

These files are preserved here for reference. They still work and can be run individually if needed:

```bash
python scripts/archive/test_all_functions.py
python scripts/archive/test_mcp_integration.py
python scripts/archive/test_refund_logic.py
python scripts/archive/test_human_alert_fix.py
```

However, we recommend using `test_comprehensive.py` for all testing needs.
