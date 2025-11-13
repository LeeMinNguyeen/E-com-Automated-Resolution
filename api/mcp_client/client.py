import asyncio
import json
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

# Get the project root to locate the MCP server script
PROJECT_ROOT = Path(__file__).parent.parent.parent
MCP_SERVER_SCRIPT = PROJECT_ROOT / "api" / "mcp_server" / "mcp_server.py"


class MCPClient:
    """Client to interact with the e-commerce MCP server."""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.server_params = StdioServerParameters(
            command=sys.executable,  # Use current Python interpreter
            args=[str(MCP_SERVER_SCRIPT)],
            env=None  # Will inherit parent environment
        )
        self._stdio_context = None
        self._read_stream = None
        self._write_stream = None
        
    async def connect(self):
        """Connect to the MCP server."""
        try:
            logger.info(f"Connecting to MCP server: {MCP_SERVER_SCRIPT}")
            logger.info(f"Using Python: {sys.executable}")
            
            # Create stdio client context manager
            self._stdio_context = stdio_client(self.server_params)
            self._read_stream, self._write_stream = await self._stdio_context.__aenter__()
            
            # Create and initialize client session
            self.session = ClientSession(self._read_stream, self._write_stream)
            await self.session.__aenter__()
            await self.session.initialize()
            
            logger.info("Successfully connected to MCP server")
            return True
            
        except Exception as e:
            logger.exception(f"Failed to connect to MCP server: {e}")
            # Cleanup on failure
            await self._cleanup()
            return False
    
    async def _cleanup(self):
        """Internal cleanup method."""
        try:
            if self.session:
                await self.session.__aexit__(None, None, None)
                self.session = None
            if self._stdio_context:
                await self._stdio_context.__aexit__(None, None, None)
                self._stdio_context = None
            self._read_stream = None
            self._write_stream = None
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    async def disconnect(self):
        """Disconnect from the MCP server."""
        try:
            logger.info("Disconnecting from MCP server")
            await self._cleanup()
            logger.info("Disconnected from MCP server")
        except Exception as e:
            logger.exception(f"Error disconnecting from MCP server: {e}")
    
    async def list_tools(self) -> list:
        """List all available tools from the MCP server."""
        if not self.session:
            raise RuntimeError("Not connected to MCP server. Call connect() first.")
        
        try:
            response = await self.session.list_tools()
            return response.tools
        except Exception as e:
            logger.exception(f"Error listing tools: {e}")
            return []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Dictionary of arguments for the tool
            
        Returns:
            Dictionary containing the tool result
        """
        if not self.session:
            raise RuntimeError("Not connected to MCP server. Call connect() first.")
        
        try:
            logger.info(f"Calling tool '{tool_name}' with arguments: {arguments}")
            
            response = await self.session.call_tool(tool_name, arguments)
            
            # Extract the result from the response
            if response.content and len(response.content) > 0:
                content_item = response.content[0]
                # Handle TextContent type
                if hasattr(content_item, 'text'):
                    result_text = content_item.text  # type: ignore
                    result = json.loads(result_text)
                    logger.info(f"Tool '{tool_name}' returned: {result}")
                    return result
                else:
                    logger.warning(f"Tool '{tool_name}' returned non-text content")
                    return {"error": "Unexpected content type"}
            else:
                logger.warning(f"Tool '{tool_name}' returned no content")
                return {"error": "No content returned from tool"}
                
        except Exception as e:
            logger.exception(f"Error calling tool '{tool_name}': {e}")
            return {"error": str(e)}
    
    async def smart_triage_nlu(self, text: str) -> Dict[str, Any]:
        """
        Classify user intent and sentiment using the NLU model.
        
        Args:
            text: User's input text
            
        Returns:
            Dictionary with intent, intent_confidence, sentiment, sentiment_confidence
        """
        return await self.call_tool("smart_triage_nlu", {"text": text})
    
    async def query_order_database(self, order_id: str) -> Dict[str, Any]:
        """
        Look up order details from the database.
        
        Args:
            order_id: The order ID to look up
            
        Returns:
            Dictionary with order details or error
        """
        return await self.call_tool("query_order_database", {"order_id": order_id})
    
    async def process_refund(self, order_id: str, amount: float, reason: str) -> Dict[str, Any]:
        """
        Process a refund for an order.
        
        Args:
            order_id: The order ID to refund
            amount: The refund amount
            reason: Reason for the refund
            
        Returns:
            Dictionary with refund status and transaction details
        """
        return await self.call_tool("process_refund", {
            "order_id": order_id,
            "amount": amount,
            "reason": reason
        })


# Global MCP client instance (lazy-loaded)
_mcp_client: Optional[MCPClient] = None
_event_loop: Optional[asyncio.AbstractEventLoop] = None
_loop_thread: Optional[threading.Thread] = None


def _start_event_loop():
    """Start a background event loop for async operations."""
    global _event_loop
    
    _event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_event_loop)
    _event_loop.run_forever()


def _get_event_loop() -> asyncio.AbstractEventLoop:
    """Get or create the background event loop."""
    global _event_loop, _loop_thread
    
    if _event_loop is None or not _event_loop.is_running():
        _loop_thread = threading.Thread(target=_start_event_loop, daemon=True)
        _loop_thread.start()
        
        # Wait for loop to start
        import time
        timeout = 5
        start_time = time.time()
        while _event_loop is None or not _event_loop.is_running():
            time.sleep(0.01)
            if time.time() - start_time > timeout:
                raise RuntimeError("Failed to start event loop")
    
    return _event_loop


async def get_mcp_client() -> MCPClient:
    """
    Get or create the global MCP client instance.
    
    Returns:
        MCPClient instance
    """
    global _mcp_client
    
    if _mcp_client is None or _mcp_client.session is None:
        logger.info("Creating new MCP client instance")
        _mcp_client = MCPClient()
        success = await _mcp_client.connect()
        if not success:
            raise RuntimeError("Failed to connect to MCP server")
    
    return _mcp_client


async def close_mcp_client():
    """Close the global MCP client instance."""
    global _mcp_client, _event_loop, _loop_thread
    
    if _mcp_client is not None:
        await _mcp_client.disconnect()
        _mcp_client = None
    
    if _event_loop is not None and _event_loop.is_running():
        _event_loop.call_soon_threadsafe(_event_loop.stop)
        _event_loop = None
    
    _loop_thread = None


# Synchronous wrapper functions for easier use in non-async code
def call_mcp_tool_sync(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synchronous wrapper to call MCP tools using a persistent event loop.
    
    Args:
        tool_name: Name of the tool to call
        arguments: Dictionary of arguments
        
    Returns:
        Dictionary with tool result
    """
    async def _async_call():
        client = await get_mcp_client()
        return await client.call_tool(tool_name, arguments)
    
    # Get the persistent event loop
    loop = _get_event_loop()
    
    # Submit the coroutine to the event loop and wait for result
    future = asyncio.run_coroutine_threadsafe(_async_call(), loop)
    return future.result(timeout=30)  # 30 second timeout



def smart_triage_sync(text: str) -> Dict[str, Any]:
    """Synchronous wrapper for smart_triage_nlu."""
    return call_mcp_tool_sync("smart_triage_nlu", {"text": text})


def query_order_sync(order_id: str) -> Dict[str, Any]:
    """Synchronous wrapper for query_order_database."""
    return call_mcp_tool_sync("query_order_database", {"order_id": order_id})


def process_refund_sync(order_id: str, amount: float, reason: str) -> Dict[str, Any]:
    """Synchronous wrapper for process_refund."""
    return call_mcp_tool_sync("process_refund", {
        "order_id": order_id,
        "amount": amount,
        "reason": reason
    })


if __name__ == "__main__":
    # Test the client
    async def test():
        client = await get_mcp_client()
        
        # Test smart triage
        print("\n=== Testing Smart Triage ===")
        result = await client.smart_triage_nlu("My order is late and I'm very angry!")
        print(json.dumps(result, indent=2))
        
        # Test order query
        print("\n=== Testing Order Query ===")
        result = await client.query_order_database("ORD000001")
        print(json.dumps(result, indent=2))
        
        # Test refund processing
        print("\n=== Testing Refund Processing ===")
        result = await client.process_refund("ORD000003", 599, "Items missing from order")
        print(json.dumps(result, indent=2))
        
        await close_mcp_client()
    
    asyncio.run(test())
