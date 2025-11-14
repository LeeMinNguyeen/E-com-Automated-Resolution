"""
Quick test for human intervention alert with user_id fix
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.mcp_client.client import request_human_intervention_sync
from dashboard.db_analytics import get_human_intervention_alerts

# Test 1: Create alert with explicit user_id
print("🧪 Test 1: Creating alert with user_id 'test_user_123'")
result = request_human_intervention_sync(
    user_id="test_user_123",
    reason="Testing user_id fix",
    last_message="I want to test if user_id is saved correctly",
    priority="medium"
)
print(f"✅ Alert created: {result}")

# Test 2: Verify alert in database
print("\n🧪 Test 2: Checking alerts in database")
alerts_df = get_human_intervention_alerts()
if not alerts_df.empty:
    latest_alert = alerts_df.iloc[0]
    print(f"\n📋 Latest Alert Details:")
    print(f"   User ID: {latest_alert['user_id']}")
    print(f"   Reason: {latest_alert['reason']}")
    print(f"   Message: {latest_alert['last_message']}")
    print(f"   Priority: {latest_alert['priority']}")
    print(f"   Status: {latest_alert['status']}")
    
    if latest_alert['user_id'] == 'test_user_123':
        print("\n✅ SUCCESS: User ID is correctly saved!")
    else:
        print(f"\n❌ FAIL: Expected 'test_user_123' but got '{latest_alert['user_id']}'")
else:
    print("❌ No alerts found in database")

print("\n" + "="*60)
print("All recent alerts:")
print(alerts_df[['user_id', 'reason', 'priority', 'status']].head(10))
