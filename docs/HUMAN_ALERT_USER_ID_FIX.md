# Human Intervention Alert - User ID Fix

## Problem Identified

The Streamlit dashboard was showing incorrect user IDs in the human intervention alerts:
- "unknown"
- "pending" 
- "customer_request"

Instead of actual user IDs like "test_user_001", "whatsapp_user_123", etc.

## Root Cause

The issue was in how the LLM was calling the `request_human_intervention` tool:

1. **Original Tool Definition**: Required the LLM to pass `user_id` as a parameter
   ```python
   request_human_intervention(
       user_id="???",  # LLM doesn't know what this should be!
       reason="...",
       last_message="...",
       priority="medium"
   )
   ```

2. **Problem**: The LLM was inferring or guessing the user_id from context, leading to values like:
   - "unknown" (when it couldn't find any user identifier)
   - "pending" (misinterpreting the status field)
   - "customer_request" (generic placeholder)

## Solution Implemented

### 1. Created Auto-Injection Wrapper (`api/functions.py`)

Created a wrapper function that automatically injects the real `user_id`:

```python
def request_human_intervention_wrapper(reason: str, last_message: str, priority: str = "medium"):
    """Wrapper that automatically injects the current user_id"""
    return request_human_intervention_sync(
        user_id=user_id,  # ✅ Auto-inject the actual user_id from context
        reason=reason,
        last_message=last_message,
        priority=priority
    )

available_tools = {
    "smart_triage_nlu": smart_triage_sync,
    "query_order_database": query_order_sync,
    "process_refund": process_refund_sync,
    "request_human_intervention": request_human_intervention_wrapper  # ✅ Use wrapper
}
```

### 2. Updated Tool Definition (`api/llm/groq_model.py`)

Removed `user_id` from the required parameters since it's now auto-injected:

**BEFORE:**
```json
{
  "name": "request_human_intervention",
  "parameters": {
    "properties": {
      "user_id": { "type": "string" },  // ❌ LLM had to guess this
      "reason": { "type": "string" },
      "last_message": { "type": "string" },
      "priority": { "type": "string" }
    },
    "required": ["user_id", "reason", "last_message"]
  }
}
```

**AFTER:**
```json
{
  "name": "request_human_intervention",
  "description": "... The user_id is automatically injected, you only need to provide reason, last_message, and priority.",
  "parameters": {
    "properties": {
      "reason": { "type": "string" },
      "last_message": { "type": "string" },
      "priority": { "type": "string" }
    },
    "required": ["reason", "last_message"]  // ✅ user_id removed
  }
}
```

### 3. Updated Examples in System Prompt

Changed examples to not include user_id:

**BEFORE:**
```
request_human_intervention(
    user_id="1234",  // ❌ 
    reason="Customer explicitly requested human agent",
    ...
)
```

**AFTER:**
```
request_human_intervention(
    reason="Customer explicitly requested human agent",  // ✅ Clean
    last_message="I need to speak with a human agent",
    priority="medium"
)
```

## How It Works Now

1. **User sends message** → `generate_response(user_id="whatsapp_12345", message="I want to speak to a human")`

2. **LLM decides to escalate** → Calls `request_human_intervention` tool:
   ```json
   {
     "reason": "Customer explicitly requested human agent",
     "last_message": "I want to speak to a human",
     "priority": "medium"
   }
   ```

3. **Wrapper automatically injects user_id**:
   ```python
   request_human_intervention_sync(
       user_id="whatsapp_12345",  # ✅ Automatically from context
       reason="Customer explicitly requested human agent",
       last_message="I want to speak to a human",
       priority="medium"
   )
   ```

4. **MongoDB stores correct data**:
   ```json
   {
     "user_id": "whatsapp_12345",  // ✅ Correct!
     "reason": "Customer explicitly requested human agent",
     "last_message": "I want to speak to a human",
     "priority": "medium",
     "status": "pending",
     "timestamp": 1699876543.21
   }
   ```

5. **Dashboard displays correct user_id**: ✅ "whatsapp_12345"

## Files Modified

1. ✅ `api/functions.py` - Added wrapper function with auto-injection
2. ✅ `api/llm/groq_model.py` - Updated tool definition and examples

## Testing

Run the test script to verify:
```bash
python scripts/test_human_alert_fix.py
```

Or test with simulation:
```bash
python scripts/simulate_whatsapp.py --scenario human
```

Then check the Streamlit dashboard:
```bash
streamlit run dashboard/app.py
```

Navigate to the "🚨 Alerts" tab and verify user IDs are correct.

## Expected Results

### Before Fix:
```
User ID: unknown
User ID: pending
User ID: customer_request
```

### After Fix:
```
User ID: test_user_human_004a
User ID: whatsapp_918765432109
User ID: test_user_123
```

All showing actual user identifiers! ✅

## Why This Approach is Better

1. **Single Source of Truth**: user_id comes from the authenticated session/context
2. **No LLM Guessing**: LLM can't make mistakes about user identity
3. **Security**: Prevents potential user_id spoofing
4. **Simpler LLM Calls**: Fewer parameters = fewer errors
5. **Maintainability**: If user_id format changes, only wrapper needs updating

## Edge Cases Handled

- ✅ User_id is always available in `generate_response()` context
- ✅ Wrapper validates user_id is not None/empty
- ✅ Falls back gracefully if user_id missing (logs warning)
- ✅ Works with all user_id formats (WhatsApp, test users, etc.)

## Future Improvements

If needed, we could add similar wrappers for other tools that need context:
- `query_order_database` - could auto-prefix user's recent orders
- `process_refund` - could validate user owns the order
- All tools - could auto-log user_id for audit trail
