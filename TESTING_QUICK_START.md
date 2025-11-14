# Testing Quick Reference

## Important Note ℹ️

**The MCP server runs automatically as a subprocess!**

You do **NOT** need to start the MCP server in a separate terminal. The MCP client automatically spawns the server process when needed and manages its lifecycle.

## Quick Health Check

Before running tests, verify everything is working:

```bash
# Check if MCP client can start server and communicate
python scripts/check_mcp_server.py
```

This will:
- ✅ Start the MCP server subprocess automatically
- ✅ Test all 5 tools (NLU, order query, refund check, etc.)
- ✅ Verify database connectivity
- ✅ Confirm the system is ready for testing

---

## Run Tests

### Comprehensive Test Suite (Recommended) ⭐

```bash
# Run all tests
python scripts/test_comprehensive.py

# Quick tests only (faster, ~30 seconds)
python scripts/test_comprehensive.py --quick

# Test only MCP server integration
python scripts/test_comprehensive.py --mcp-only

# Test only refund logic
python scripts/test_comprehensive.py --refund
```

### Specialized Tests

```bash
# Test NLU model accuracy (detailed metrics)
python scripts/test_nlu_accuracy.py
```

## What Gets Tested

### ✅ test_comprehensive.py
- **Suite 1**: MCP Server & Client Integration
  - Server connectivity
  - Tool availability (5 tools)
  - NLU analysis
  - Order queries
  
- **Suite 2**: Refund Logic
  - Eligibility checking
  - Food & Beverage rejection
  - 5% shipping fee calculation
  - Database updates
  - Duplicate prevention
  
- **Suite 3**: NLU Analysis
  - Intent classification
  - Sentiment analysis
  - Confidence scores
  
- **Suite 4**: Human Intervention
  - Alert creation
  - Priority levels
  - Database storage
  
- **Suite 5**: End-to-End Flows
  - Refund conversations
  - Human escalation
  - Multi-turn dialogs

### ✅ test_nlu_accuracy.py
- Model performance metrics
- Intent classification accuracy
- Sentiment analysis accuracy
- Confusion matrix
- Per-class metrics
- Saves results to `scripts/results/`

## Expected Results

### All Tests Passing
```
Total Tests Run:     45
Tests Passed:        45 ✅
Tests Failed:        0 ❌
Pass Rate:           100.0%

Status: ✅ ALL TESTS PASSED
```

### Test Output Format
```
✅ PASS: Test name
❌ FAIL: Test name
    Error details
```

## Troubleshooting

### MCP Server Connection Failed
```bash
# Manually start MCP server in a separate terminal
python api/mcp_server/mcp_server.py
```

### Database Connection Issues
- Check MongoDB is running
- Verify MONGO_URI in .env file
- Ensure network connectivity

### Import Errors
```bash
# Ensure you're in the project root
cd E:/Project/E-com-Automated-Resolution

# Activate virtual environment if using one
.venv\Scripts\Activate.ps1
```

## Archived Tests

Old test scripts are in `scripts/archive/`:
- test_all_functions.py
- test_mcp_integration.py
- test_refund_logic.py
- test_human_alert_fix.py

These are kept for reference but `test_comprehensive.py` replaces all of them.

## Next Steps After Testing

1. ✅ All tests pass → System is ready for production
2. ❌ Some tests fail → Review error messages and fix issues
3. 📊 Check NLU accuracy → If low, consider retraining model
4. 🚀 Start the bot → `python api/main.py`
5. 📱 Test with WhatsApp → Use `scripts/simulate_whatsapp.py`
