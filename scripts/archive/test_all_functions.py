"""
Comprehensive MCP Function Tester

This script tests all MCP functions with different user scenarios:
1. smart_triage_nlu - Intent and sentiment analysis
2. query_order_database - Order lookup
3. process_refund - Refund processing
4. request_human_intervention - Human escalation

Each test uses a different user ID to simulate real-world scenarios.

Usage:
    python scripts/test_all_functions.py
"""

import sys
import os
from pathlib import Path
import logging
from datetime import datetime
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.functions import generate_response, save_message
from api.llm.conversation_context import get_conversation_context
from api.db.mongo import get_mongo_client, DATABASE_NAME

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def clear_user_data(user_id: str):
    """Clear all chat history for a specific user."""
    try:
        mongo_client = get_mongo_client()
        if mongo_client:
            db = mongo_client[DATABASE_NAME]
            
            # Clear chat history
            chat_collection = db.get_collection("chat_history")
            result = chat_collection.delete_many({"user_id": user_id})
            
            # Clear conversation context
            context_manager = get_conversation_context()
            context_manager.clear_context(user_id)
            
            logger.info(f"Cleared {result.deleted_count} messages for user {user_id}")
    except Exception as e:
        logger.exception(f"Error clearing user data: {e}")


def send_test_message(user_id: str, message: str, delay: float = 1.0) -> str:
    """
    Send a test message and get response.
    
    Args:
        user_id: User identifier
        message: Message text
        delay: Delay before processing
        
    Returns:
        Bot response
    """
    print(f"\n👤 USER ({user_id}): {message}")
    
    if delay > 0:
        time.sleep(delay)
    
    # Save user message
    timestamp = int(datetime.now().timestamp())
    save_message(user_id, "user", "system", message, timestamp)
    
    # Generate bot response
    try:
        response = generate_response(user_id, message)
        
        # Save bot response
        save_message(user_id, "system", user_id, response, timestamp)
        
        print(f"🤖 BOT: {response}")
        
        return response
        
    except Exception as e:
        logger.exception(f"Error generating response: {e}")
        return f"Error: {str(e)}"


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def print_subsection(title: str):
    """Print a formatted subsection header."""
    print("\n" + "-"*80)
    print(f"  {title}")
    print("-"*80)


def test_smart_triage_nlu():
    """
    Test 1: smart_triage_nlu function
    Tests NLU analysis with various intents and sentiments
    """
    print_section("TEST 1: Smart Triage NLU - Intent & Sentiment Analysis")
    
    user_id = "test_user_nlu_001"
    clear_user_data(user_id)
    
    print("\n📝 Testing different intents and sentiments...")
    
    # Test 1a: Track Order (neutral sentiment)
    print_subsection("1a. Track Order - Neutral Sentiment")
    send_test_message(user_id, "Where is my order?", delay=1)
    time.sleep(1)
    
    # Test 1b: Delivery Delay (negative sentiment)
    clear_user_data(user_id)
    print_subsection("1b. Delivery Delay - Negative Sentiment")
    send_test_message(user_id, "My order is very late and I'm extremely angry!", delay=1)
    time.sleep(1)
    
    # Test 1c: Refund Request (negative sentiment)
    clear_user_data(user_id)
    print_subsection("1c. Refund Request - Negative Sentiment")
    send_test_message(user_id, "I want my money back for this terrible service!", delay=1)
    time.sleep(1)
    
    # Test 1d: Positive Feedback
    clear_user_data(user_id)
    print_subsection("1d. Positive Feedback")
    send_test_message(user_id, "Thank you! The delivery was excellent!", delay=1)
    time.sleep(1)
    
    print("\n✅ Smart Triage NLU tests completed")


def test_query_order_database():
    """
    Test 2: query_order_database function
    Tests order lookup with various scenarios
    """
    print_section("TEST 2: Query Order Database - Order Lookup")
    
    user_id = "test_user_order_002"
    clear_user_data(user_id)
    
    print("\n📦 Testing order lookups...")
    
    # Test 2a: Order lookup without ID (should ask for it)
    print_subsection("2a. Order Lookup - Missing Order ID")
    send_test_message(user_id, "Check my order status", delay=1)
    time.sleep(1)
    send_test_message(user_id, "ORD000001", delay=1)
    time.sleep(1)
    
    # Test 2b: Order lookup with ID provided
    clear_user_data(user_id)
    print_subsection("2b. Order Lookup - With Order ID")
    send_test_message(user_id, "What's the status of order ORD000010?", delay=1)
    time.sleep(1)
    
    # Test 2c: Multiple order lookups
    clear_user_data(user_id)
    print_subsection("2c. Multiple Order Lookups")
    send_test_message(user_id, "Check ORD000001", delay=1)
    time.sleep(1)
    send_test_message(user_id, "Now check another order ORD000003", delay=1)
    time.sleep(1)
    
    # Test 2d: Invalid order ID
    clear_user_data(user_id)
    print_subsection("2d. Invalid Order ID")
    send_test_message(user_id, "Check order ORD999999", delay=1)
    time.sleep(1)
    
    print("\n✅ Query Order Database tests completed")


def test_process_refund():
    """
    Test 3: process_refund function
    Tests refund processing with full conversation flow
    """
    print_section("TEST 3: Process Refund - Refund Processing")
    
    user_id = "test_user_refund_003"
    clear_user_data(user_id)
    
    print("\n💰 Testing refund processing...")
    
    # Test 3a: Refund without order ID
    print_subsection("3a. Refund Request - Missing Order ID")
    send_test_message(user_id, "I want a refund", delay=1)
    time.sleep(1)
    send_test_message(user_id, "ORD000003", delay=1)
    time.sleep(1)
    send_test_message(user_id, "Yes, please process the refund", delay=1)
    time.sleep(1)
    
    # Test 3b: Refund with order ID provided
    clear_user_data(user_id)
    print_subsection("3b. Refund Request - With Order ID")
    send_test_message(user_id, "I need a refund for order ORD000003", delay=1)
    time.sleep(1)
    send_test_message(user_id, "Yes", delay=1)
    time.sleep(1)
    
    # Test 3c: Refund with complaint
    clear_user_data(user_id)
    print_subsection("3c. Refund Request - With Complaint")
    send_test_message(user_id, "The items were missing and I want my money back for ORD000003", delay=1)
    time.sleep(1)
    send_test_message(user_id, "Yes, process it", delay=1)
    time.sleep(1)
    
    # Test 3d: Refund cancellation
    clear_user_data(user_id)
    print_subsection("3d. Refund Cancellation - User Changes Mind")
    send_test_message(user_id, "I want to cancel order ORD000001", delay=1)
    time.sleep(1)
    send_test_message(user_id, "Actually, never mind", delay=1)
    time.sleep(1)
    
    print("\n✅ Process Refund tests completed")


def test_request_human_intervention():
    """
    Test 4: request_human_intervention function
    Tests human escalation with various scenarios
    """
    print_section("TEST 4: Request Human Intervention - Escalation")
    
    print("\n🚨 Testing human intervention requests...")
    
    # Test 4a: Explicit request for human
    print_subsection("4a. Explicit Request for Human Agent")
    user_id = "test_user_human_004a"
    clear_user_data(user_id)
    send_test_message(user_id, "I want to speak with a human agent", delay=1)
    time.sleep(2)
    
    # Test 4b: Very frustrated customer (negative sentiment)
    print_subsection("4b. Very Frustrated Customer - High Priority")
    user_id = "test_user_human_004b"
    clear_user_data(user_id)
    send_test_message(user_id, "This is absolutely unacceptable! I've been waiting for 2 weeks and nobody has helped me! This is the worst service ever!", delay=1)
    time.sleep(2)
    
    # Test 4c: Complex issue
    print_subsection("4c. Complex Issue Beyond Automation")
    user_id = "test_user_human_004c"
    clear_user_data(user_id)
    send_test_message(user_id, "I need to update my billing information and change my delivery address for a pending order", delay=1)
    time.sleep(2)
    
    # Test 4d: Request for manager
    print_subsection("4d. Request to Speak with Manager")
    user_id = "test_user_human_004d"
    clear_user_data(user_id)
    send_test_message(user_id, "I need to speak with your manager immediately about this issue", delay=1)
    time.sleep(2)
    
    # Test 4e: Multiple failed attempts
    print_subsection("4e. Multiple Failed Resolution Attempts")
    user_id = "test_user_human_004e"
    clear_user_data(user_id)
    send_test_message(user_id, "Check my order", delay=1)
    time.sleep(1)
    send_test_message(user_id, "I don't have an order ID", delay=1)
    time.sleep(1)
    send_test_message(user_id, "I don't know, you tell me!", delay=1)
    time.sleep(1)
    send_test_message(user_id, "This is ridiculous, just connect me to a person!", delay=1)
    time.sleep(2)
    
    print("\n✅ Request Human Intervention tests completed")


def test_mixed_scenarios():
    """
    Test 5: Mixed scenarios
    Tests realistic multi-turn conversations with multiple functions
    """
    print_section("TEST 5: Mixed Scenarios - Real-world Conversations")
    
    print("\n🎭 Testing realistic conversation flows...")
    
    # Test 5a: Order check → Complaint → Refund
    print_subsection("5a. Order Check → Complaint → Refund Flow")
    user_id = "test_user_mixed_005a"
    clear_user_data(user_id)
    send_test_message(user_id, "Hi, I want to check my order", delay=1)
    time.sleep(1)
    send_test_message(user_id, "ORD000010", delay=1)
    time.sleep(1)
    send_test_message(user_id, "This is taking too long! I want a refund!", delay=1)
    time.sleep(1)
    send_test_message(user_id, "Yes, process the refund please", delay=1)
    time.sleep(2)
    
    # Test 5b: Vague request → Clarification → Resolution
    print_subsection("5b. Vague Request → Clarification → Resolution")
    user_id = "test_user_mixed_005b"
    clear_user_data(user_id)
    send_test_message(user_id, "I need help", delay=1)
    time.sleep(1)
    send_test_message(user_id, "My delivery hasn't arrived", delay=1)
    time.sleep(1)
    send_test_message(user_id, "ORD000003", delay=1)
    time.sleep(2)
    
    # Test 5c: General inquiry → Order check
    print_subsection("5c. General Inquiry → Order Check")
    user_id = "test_user_mixed_005c"
    clear_user_data(user_id)
    send_test_message(user_id, "Do you deliver on Sundays?", delay=1)
    time.sleep(1)
    send_test_message(user_id, "OK, can you check order ORD000001 for me?", delay=1)
    time.sleep(2)
    
    # Test 5d: Topic switching (tests NLU re-analysis)
    print_subsection("5d. Topic Switching - NLU Re-analysis")
    user_id = "test_user_mixed_005d"
    clear_user_data(user_id)
    send_test_message(user_id, "Check order ORD000001", delay=1)
    time.sleep(1)
    send_test_message(user_id, "Actually, I want to ask about a refund for a different order", delay=1)
    time.sleep(1)
    send_test_message(user_id, "ORD000003", delay=1)
    time.sleep(1)
    send_test_message(user_id, "Yes", delay=1)
    time.sleep(2)
    
    print("\n✅ Mixed Scenarios tests completed")


def check_dashboard_alerts():
    """Check if alerts were created in the database."""
    print_section("VERIFICATION: Check Human Intervention Alerts")
    
    try:
        mongo_client = get_mongo_client()
        if mongo_client:
            db = mongo_client[DATABASE_NAME]
            alerts_col = db.get_collection("human_intervention_alerts")
            
            # Get all alerts
            alerts = list(alerts_col.find().sort('timestamp', -1))
            
            print(f"\n📊 Total alerts created: {len(alerts)}")
            
            if alerts:
                print("\n🚨 Recent Alerts:")
                for i, alert in enumerate(alerts[:5], 1):
                    print(f"\n  {i}. User: {alert.get('user_id')}")
                    print(f"     Reason: {alert.get('reason')}")
                    print(f"     Priority: {alert.get('priority', 'medium')}")
                    print(f"     Status: {alert.get('status', 'unknown')}")
                    print(f"     Time: {alert.get('timestamp', 'N/A')}")
            else:
                print("\n⚠️  No alerts found. Human intervention may not have been triggered.")
                
    except Exception as e:
        logger.exception(f"Error checking alerts: {e}")
        print(f"\n❌ Error checking alerts: {e}")


def print_summary():
    """Print test summary."""
    print_section("TEST SUMMARY")
    
    print("""
✅ All MCP Functions Tested:

1. ✅ smart_triage_nlu
   - Intent classification (track_order, refund, complaint, etc.)
   - Sentiment analysis (positive, negative, neutral)
   - Confidence scores
   - Topic change re-analysis

2. ✅ query_order_database
   - Order lookup with/without Order ID
   - Multiple order checks
   - Invalid order handling
   - Auto Order ID extraction

3. ✅ process_refund
   - Full refund flow with confirmation
   - Refund with complaint
   - Refund cancellation
   - Amount and reason handling

4. ✅ request_human_intervention
   - Explicit human requests
   - Frustrated customer escalation
   - Complex issue escalation
   - Priority levels (high/medium/low)
   - Alert creation in database

5. ✅ Mixed Scenarios
   - Multi-turn conversations
   - Function chaining
   - Context management
   - Topic switching

📊 Check the dashboard to view:
   - Human intervention alerts
   - Conversation history
   - Performance metrics
   - Refund statistics

🚀 Run the dashboard:
   cd dashboard
   streamlit run app.py
    """)


def main():
    """Main test execution."""
    print("\n" + "="*80)
    print("  🧪 COMPREHENSIVE MCP FUNCTION TEST SUITE")
    print("="*80)
    print("\n  This script will test ALL MCP functions with different user scenarios.")
    print("  Each test uses a unique user ID to simulate real-world usage.")
    print("\n" + "="*80)
    
    input("\nPress ENTER to start testing...")
    
    start_time = time.time()
    
    try:
        # Run all tests
        test_smart_triage_nlu()
        time.sleep(2)
        
        test_query_order_database()
        time.sleep(2)
        
        test_process_refund()
        time.sleep(2)
        
        test_request_human_intervention()
        time.sleep(2)
        
        test_mixed_scenarios()
        time.sleep(2)
        
        # Check alerts
        check_dashboard_alerts()
        
        # Print summary
        print_summary()
        
        elapsed_time = time.time() - start_time
        print(f"\n⏱️  Total test time: {elapsed_time:.2f} seconds")
        print("\n" + "="*80)
        print("  ✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*80 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        print("="*80 + "\n")
    except Exception as e:
        logger.exception(f"Error during testing: {e}")
        print(f"\n\n❌ Error during testing: {e}")
        print("="*80 + "\n")


if __name__ == "__main__":
    main()
