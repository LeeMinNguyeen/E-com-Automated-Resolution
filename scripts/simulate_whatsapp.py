"""
WhatsApp Simulator - Test the bot without sending real WhatsApp messages

This script simulates WhatsApp API calls to test the bot's conversational flow,
tool calling, and response generation.

Usage:
    python scripts/simulate_whatsapp.py
    
    # Or test specific scenario:
    python scripts/simulate_whatsapp.py --scenario refund
"""

import sys
import os
from pathlib import Path
import logging
from datetime import datetime
import time
import argparse

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


def clear_chat_history(user_id: str):
    """Clear all chat history for a specific user from MongoDB."""
    try:
        mongo_client = get_mongo_client()
        if mongo_client:
            db = mongo_client[DATABASE_NAME]
            chat_collection = db.get_collection("chat_history")
            result = chat_collection.delete_many({"user_id": user_id})
            logger.info(f"Cleared {result.deleted_count} messages for user {user_id}")
            print(f"🗑️  Cleared {result.deleted_count} previous messages from database")
    except Exception as e:
        logger.exception(f"Error clearing chat history: {e}")
        print(f"⚠️  Warning: Could not clear chat history: {e}")


class WhatsAppSimulator:
    """Simulates WhatsApp user interactions for testing."""
    
    def __init__(self, user_id="sim_user_12345"):
        self.user_id = user_id
        self.conversation_history = []
        
        # Clear previous chat history and context on initialization
        print(f"\n🔄 Initializing simulator for user: {user_id}")
        clear_chat_history(user_id)
        
        # Clear conversation context
        context_manager = get_conversation_context()
        context_manager.clear_context(user_id)
        print("✅ Ready for testing\n")
        
    def send_message(self, message: str, delay: float = 1.0):
        """
        Simulate sending a message from the user.
        
        Args:
            message: User's message text
            delay: Delay before processing (simulates typing)
        """
        print("\n" + "="*70)
        print(f"👤 USER: {message}")
        print("="*70)
        
        # Simulate typing delay
        if delay > 0:
            print(f"⏳ Processing... (waiting {delay}s)")
            time.sleep(delay)
        
        # Save user message
        timestamp = int(datetime.now().timestamp())
        save_message(self.user_id, "user", "system", message, timestamp)
        
        # Generate bot response
        try:
            response = generate_response(self.user_id, message)
            
            # Save bot response
            save_message(self.user_id, "system", self.user_id, response, timestamp)
            
            # Display response
            print(f"\n🤖 BOT: {response}")
            print("="*70)
            
            # Store in conversation history
            self.conversation_history.append({
                "user": message,
                "bot": response,
                "timestamp": timestamp
            })
            
            return response
            
        except Exception as e:
            logger.exception(f"Error generating response: {e}")
            error_msg = "Sorry, I encountered an error. Please try again."
            print(f"\n🤖 BOT: {error_msg}")
            print("="*70)
            return error_msg
    
    def show_context(self):
        """Display current conversation context."""
        context_manager = get_conversation_context()
        context = context_manager.get_context(self.user_id)
        
        print("\n📊 CONVERSATION CONTEXT:")
        print(f"  Waiting for: {context.get('waiting_for')}")
        print(f"  Pending action: {context.get('pending_action')}")
        print(f"  Extracted info: {context.get('extracted_info')}")
        print()
    
    def clear_history(self):
        """Clear conversation history and context."""
        self.conversation_history = []
        
        # Clear from database
        clear_chat_history(self.user_id)
        
        # Clear context
        context_manager = get_conversation_context()
        context_manager.clear_context(self.user_id)
        
        logger.info("Conversation history cleared")
        print("\n🔄 Conversation history cleared\n")


def scenario_order_lookup_with_missing_id(sim: WhatsAppSimulator):
    """Test scenario: User asks about order without providing Order ID."""
    print("\n" + "🎬 SCENARIO 1: Order Lookup - Missing Order ID" + "\n")
    
    sim.send_message("Where is my order?")
    time.sleep(1)
    
    sim.send_message("ORD000001")
    time.sleep(1)
    
    sim.show_context()


def scenario_refund_request(sim: WhatsAppSimulator):
    """Test scenario: User requests refund with full conversation flow."""
    print("\n" + "🎬 SCENARIO 2: Refund Request - Full Flow" + "\n")
    
    sim.send_message("I want a refund")
    time.sleep(1)
    
    sim.send_message("ORD000003")
    time.sleep(1)
    
    sim.send_message("Yes, please process it")
    time.sleep(1)
    
    sim.show_context()


def scenario_order_lookup_with_id(sim: WhatsAppSimulator):
    """Test scenario: User provides Order ID immediately."""
    print("\n" + "🎬 SCENARIO 3: Order Lookup - With Order ID" + "\n")
    
    sim.send_message("Check order ORD000010")
    time.sleep(1)
    
    sim.show_context()


def scenario_delivery_complaint(sim: WhatsAppSimulator):
    """Test scenario: User complains about late delivery."""
    print("\n" + "🎬 SCENARIO 4: Delivery Complaint - Sentiment Detection" + "\n")
    
    sim.send_message("My delivery is very late and I'm extremely frustrated!")
    time.sleep(1)
    
    sim.send_message("ORD000010")
    time.sleep(1)
    
    sim.show_context()


def scenario_vague_request(sim: WhatsAppSimulator):
    """Test scenario: User makes vague request."""
    print("\n" + "🎬 SCENARIO 5: Vague Request" + "\n")
    
    sim.send_message("I need help")
    time.sleep(1)
    
    sim.send_message("My items didn't arrive")
    time.sleep(1)
    
    sim.send_message("ORD000003")
    time.sleep(1)
    
    sim.show_context()


def scenario_general_inquiry(sim: WhatsAppSimulator):
    """Test scenario: General question without needing tools."""
    print("\n" + "🎬 SCENARIO 6: General Inquiry" + "\n")
    
    sim.send_message("Do you deliver on weekends?")
    time.sleep(1)
    
    sim.show_context()


def scenario_multi_order_check(sim: WhatsAppSimulator):
    """Test scenario: User checks multiple orders."""
    print("\n" + "🎬 SCENARIO 7: Multiple Order Checks" + "\n")
    
    sim.send_message("Check ORD000001")
    time.sleep(1)
    
    sim.send_message("Now check ORD000003")
    time.sleep(1)
    
    sim.show_context()


def interactive_mode(sim: WhatsAppSimulator):
    """Interactive mode - user can type messages."""
    print("\n" + "🎮 INTERACTIVE MODE" + "\n")
    print("Type your messages (or 'quit' to exit, 'context' to see context, 'clear' to reset)")
    print("="*70 + "\n")
    
    while True:
        try:
            user_input = input("👤 YOU: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'quit':
                print("\n👋 Goodbye!\n")
                break
            
            if user_input.lower() == 'context':
                sim.show_context()
                continue
            
            if user_input.lower() == 'clear':
                sim.clear_history()
                continue
            
            sim.send_message(user_input, delay=0.5)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!\n")
            break
        except Exception as e:
            logger.exception(f"Error in interactive mode: {e}")


def run_all_scenarios(sim: WhatsAppSimulator):
    """Run all test scenarios."""
    print("\n" + "🚀 RUNNING ALL TEST SCENARIOS" + "\n")
    print("This will test various conversation flows and edge cases.")
    print("="*70)
    
    scenarios = [
        scenario_order_lookup_with_missing_id,
        scenario_refund_request,
        scenario_order_lookup_with_id,
        scenario_delivery_complaint,
        scenario_vague_request,
        scenario_general_inquiry,
        scenario_multi_order_check,
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        if i > 1:
            print("\n" + "-"*70)
            print("Clearing context for next scenario...")
            sim.clear_history()
            time.sleep(2)
        
        scenario(sim)
        time.sleep(2)
    
    print("\n" + "="*70)
    print("✅ ALL SCENARIOS COMPLETED")
    print("="*70 + "\n")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="WhatsApp Bot Simulator")
    parser.add_argument(
        '--scenario',
        choices=['all', 'order', 'refund', 'complaint', 'vague', 'general', 'multi', 'interactive'],
        default='interactive',
        help='Scenario to run (default: interactive)'
    )
    parser.add_argument(
        '--user-id',
        default='sim_user_12345',
        help='Simulated user ID'
    )
    
    args = parser.parse_args()
    
    # Create simulator
    sim = WhatsAppSimulator(user_id=args.user_id)
    
    print("\n" + "="*70)
    print("  📱 WhatsApp Bot Simulator")
    print("="*70)
    print(f"  User ID: {sim.user_id}")
    print("="*70)
    
    # Run selected scenario
    if args.scenario == 'all':
        run_all_scenarios(sim)
    elif args.scenario == 'order':
        scenario_order_lookup_with_missing_id(sim)
    elif args.scenario == 'refund':
        scenario_refund_request(sim)
    elif args.scenario == 'complaint':
        scenario_delivery_complaint(sim)
    elif args.scenario == 'vague':
        scenario_vague_request(sim)
    elif args.scenario == 'general':
        scenario_general_inquiry(sim)
    elif args.scenario == 'multi':
        scenario_multi_order_check(sim)
    elif args.scenario == 'interactive':
        interactive_mode(sim)
    
    print("\n📊 Session Summary:")
    print(f"  Total exchanges: {len(sim.conversation_history)}")
    print(f"  User ID: {sim.user_id}")
    print()


if __name__ == "__main__":
    main()
