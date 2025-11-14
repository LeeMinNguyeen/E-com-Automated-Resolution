"""
Test script to verify the MCP client integration.
Run this to ensure the MCP server and client are working correctly.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.mcp_client.client import get_mcp_client, close_mcp_client
import json


async def test_mcp_integration():
    """Test the full MCP integration."""
    print("=" * 70)
    print("Testing MCP Server Integration")
    print("=" * 70)
    
    try:
        # Connect to MCP server
        print("\n1. Connecting to MCP server...")
        client = await get_mcp_client()
        print("   ✓ Connected successfully!")
        
        # List available tools
        print("\n2. Listing available tools...")
        tools = await client.list_tools()
        print(f"   ✓ Found {len(tools)} tools:")
        for tool in tools:
            print(f"     - {tool.name}: {tool.description[:50]}...")
        
        # Test smart_triage_nlu
        print("\n3. Testing smart_triage_nlu...")
        test_messages = [
            "My order is very late and I'm extremely frustrated!",
            "Thank you for the quick delivery, everything was perfect!",
            "Where is my order ORD000010?"
        ]
        
        for msg in test_messages:
            print(f"\n   Input: '{msg}'")
            result = await client.smart_triage_nlu(msg)
            if "error" not in result:
                print(f"   Intent: {result.get('intent')} (confidence: {result.get('intent_confidence')})")
                print(f"   Sentiment: {result.get('sentiment')} (confidence: {result.get('sentiment_confidence')})")
            else:
                print(f"   ✗ Error: {result['error']}")
        
        # Test query_order_database
        print("\n4. Testing query_order_database...")
        test_order_ids = ["ORD000001", "ORD000003", "INVALID123"]
        
        for order_id in test_order_ids:
            print(f"\n   Querying: {order_id}")
            result = await client.query_order_database(order_id)
            if "error" not in result:
                print(f"   ✓ Found order:")
                print(f"     Platform: {result.get('Platform')}")
                print(f"     Product: {result.get('Product Category')}")
                print(f"     Value: ₹{result.get('Order Value (INR)')}")
                print(f"     Status: Refund Requested = {result.get('Refund Requested')}")
            else:
                print(f"   ✗ {result['error']}")
        
        # Test process_refund
        print("\n5. Testing process_refund...")
        print("   Processing refund for ORD000003 (₹599)...")
        result = await client.process_refund("ORD000003", 599, "Items missing from order")
        if "error" not in result:
            print(f"   ✓ Refund processed successfully!")
            print(f"     Transaction ID: {result.get('transaction_id')}")
            print(f"     Amount: ₹{result.get('amount_refunded')}")
            print(f"     Message: {result.get('message')}")
        else:
            print(f"   ✗ Error: {result['error']}")
        
        print("\n" + "=" * 70)
        print("✓ All tests completed!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Close the client
        print("\nClosing MCP client...")
        await close_mcp_client()
        print("Done!")


if __name__ == "__main__":
    asyncio.run(test_mcp_integration())
