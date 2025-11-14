"""
Quick MCP Server Health Check

This script tests if the MCP client can start and communicate with the server.
NOTE: The MCP server is automatically started as a subprocess by the client.
You do NOT need to run the server separately!
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.mcp_client.client import MCPClient


async def check_mcp_server():
    """Check if MCP client can start the server and communicate."""
    print("\n" + "="*70)
    print("  MCP CLIENT & SERVER HEALTH CHECK")
    print("="*70)
    print("\n  ℹ️  The MCP server runs as a subprocess - no need to start it manually")
    
    print("\n  [1] Creating MCP client and starting server subprocess...")
    
    client = MCPClient()
    
    try:
        # Try to connect (this starts the server subprocess)
        success = await client.connect()
        
        if not success:
            print("  ❌ Failed to connect!")
            print("\n" + "="*70)
            print("  ⚠️  MCP CONNECTION FAILED")
            print("="*70)
            print("\n  Possible issues:")
            print("    1. Python environment not configured correctly")
            print("    2. Required packages not installed")
            print("    3. MCP server script has errors")
            print("\n  Try running the server directly to see errors:")
            print("    python api/mcp_server/mcp_server.py")
            print("\n")
            return False
        
        print("  ✅ Successfully started MCP server subprocess!")
        
        # Test a simple tool call
        print("\n  [2] Listing available tools...")
        tools = await client.list_tools()
        print(f"  ✅ Server is responsive! Found {len(tools)} tools:")
        for tool in tools:
            print(f"      • {tool.name}")
        
        # Quick NLU test
        print("\n  [3] Testing NLU tool...")
        result = await client.smart_triage_nlu("I want a refund")
        if "error" not in result:
            print(f"  ✅ NLU tool working!")
            print(f"      Intent: {result.get('intent')} ({result.get('intent_confidence', 0):.1%})")
            print(f"      Sentiment: {result.get('sentiment')} ({result.get('sentiment_confidence', 0):.1%})")
        else:
            print(f"  ⚠️  NLU tool returned error: {result.get('error')}")
        
        # Test order query
        print("\n  [4] Testing order query tool...")
        result = await client.query_order_database("ORD000001")
        if "error" not in result:
            print(f"  ✅ Order query working!")
            print(f"      Product: {result.get('Product Category')}")
            print(f"      Value: ₹{result.get('Order Value (INR)')}")
        else:
            print(f"  ⚠️  Order query error: {result.get('error')}")
        
        # Test refund eligibility
        print("\n  [5] Testing refund eligibility tool...")
        result = await client.check_refund_eligibility("ORD000006")
        if "error" not in result:
            eligible = result.get('eligible')
            print(f"  ✅ Refund eligibility check working!")
            print(f"      Order: {result.get('order_id')}")
            print(f"      Eligible: {eligible}")
            if eligible:
                print(f"      Refund Amount: ₹{result.get('refund_amount')}")
        else:
            print(f"  ⚠️  Refund check error: {result.get('error')}")
        
        print("\n" + "="*70)
        print("  ✅ MCP CLIENT & SERVER ARE HEALTHY")
        print("="*70)
        print("\n  You can now run the comprehensive test suite:")
        print("    python scripts/test_comprehensive.py")
        print("\n  The MCP server will be automatically started when needed.")
        print("\n")
        
        # Clean disconnect
        await client.disconnect()
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        print("\n" + "="*70)
        print("  ⚠️  MCP HEALTH CHECK FAILED")
        print("="*70)
        print(f"\n  Error details: {type(e).__name__}: {e}")
        print("\n  This might indicate:")
        print("    • Missing dependencies (run: pip install -r requirements.txt)")
        print("    • Database connection issues (check MongoDB)")
        print("    • Model files missing (check model/ directory)")
        print("\n  For detailed error info, try:")
        print("    python api/mcp_server/mcp_server.py")
        print("\n")
        
        try:
            await client.disconnect()
        except:
            pass
        
        return False


if __name__ == "__main__":
    result = asyncio.run(check_mcp_server())
    sys.exit(0 if result else 1)
