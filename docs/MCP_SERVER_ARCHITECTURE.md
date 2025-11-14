# How the MCP Server Works

## Important Concept 🔑

**The MCP server is NOT a standalone network service!**

Unlike a typical web server or database server that runs independently, the MCP server in this project uses the **stdio (Standard Input/Output) protocol**. This means:

✅ **The MCP client automatically starts the server as a subprocess**
✅ **Communication happens through pipes, not network sockets**
✅ **No need to run the server in a separate terminal**
✅ **The server lifecycle is managed by the client**

## How It Works

### Traditional Client-Server (NOT how MCP works)
```
Terminal 1:                    Terminal 2:
$ python server.py      →      $ python client.py
(server runs forever)          (connects to server via network)
```

### MCP stdio Protocol (How it actually works)
```
Terminal 1:
$ python client.py
  └─> Spawns subprocess: python mcp_server.py
  └─> Communicates via stdin/stdout pipes
  └─> Server exits when client disconnects
```

## Architecture Diagram

```
┌─────────────────────────────────────┐
│   Your Code / Test Script          │
│   (test_comprehensive.py)           │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│   MCP Client                        │
│   (api/mcp_client/client.py)        │
│                                     │
│   MCPClient.connect() does:         │
│   1. Spawn subprocess                │
│   2. Start mcp_server.py            │
│   3. Create stdio pipes              │
│   4. Establish communication        │
└────────────────┬────────────────────┘
                 │
                 │ stdio pipes (not network!)
                 │
                 ▼
┌─────────────────────────────────────┐
│   MCP Server (subprocess)           │
│   (api/mcp_server/mcp_server.py)    │
│                                     │
│   • Loads NLU model                 │
│   • Connects to MongoDB             │
│   • Provides 5 tools                │
│   • Waits for requests              │
└─────────────────────────────────────┘
```

## Code Flow

### When you call `check_refund_eligibility_sync()`:

```python
# 1. Your code
result = check_refund_eligibility_sync("ORD000001")

# 2. Client wrapper (api/mcp_client/client.py)
def check_refund_eligibility_sync(order_id):
    # Gets or creates global MCP client
    client = get_mcp_client()  
    # ↓ If client doesn't exist, this happens:
    #   - Spawns subprocess: python mcp_server.py
    #   - Waits for server to load model & connect to DB
    #   - Establishes stdio communication
    
    # Sends request to server subprocess
    return client.call_tool("check_refund_eligibility", {"order_id": order_id})

# 3. Server subprocess (api/mcp_server/mcp_server.py)
@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "check_refund_eligibility":
        # Queries MongoDB
        # Checks product category
        # Calculates refund amount
        # Returns result via stdio

# 4. Client receives result and returns to your code
```

## Why This Design?

### Advantages ✅
- **Isolation**: Each test run gets a fresh server instance
- **No port conflicts**: No network sockets needed
- **Automatic cleanup**: Server dies when client disconnects
- **Process-level security**: Server runs in isolated subprocess
- **Simplicity**: No need to manage server startup/shutdown

### Trade-offs ⚖️
- **Startup overhead**: Server starts each time (loads model, connects DB)
- **Not for multiple clients**: Can't share one server across processes
- **Debugging**: Server logs go to stderr, not a log file

## Common Misconceptions ❌

### ❌ WRONG: "I need to run the server first"
```bash
# DON'T DO THIS (unless debugging)
Terminal 1: python api/mcp_server/mcp_server.py
Terminal 2: python scripts/test_comprehensive.py
```

The test script will spawn its own server instance, so you'll have two servers running (wasteful and confusing).

### ✅ CORRECT: "Just run the tests"
```bash
# DO THIS
python scripts/test_comprehensive.py
# The script will automatically start the server subprocess
```

## When to Run the Server Manually

You should **only** run `python api/mcp_server/mcp_server.py` directly when:

1. **Debugging**: You want to see server logs and errors in real-time
2. **Testing server code**: You're modifying the server and want to test it
3. **Troubleshooting**: Health check fails and you want to see why

Example debugging session:
```bash
# See what's wrong with the server
python api/mcp_server/mcp_server.py

# You might see errors like:
# - "Error loading model" → model files missing
# - "MongoDB connection failed" → check MONGO_URI
# - "Import error" → missing packages
```

## Testing Workflow

### ✅ Recommended Workflow

```bash
# Step 1: Health check (spawns server subprocess automatically)
python scripts/check_mcp_server.py

# Step 2: Run tests (spawns server subprocess automatically)
python scripts/test_comprehensive.py

# Step 3: Run your app (spawns server subprocess when needed)
python api/main.py
```

### Each command starts its own server subprocess
```
check_mcp_server.py → spawns mcp_server.py → exits when check done
test_comprehensive.py → spawns mcp_server.py → exits when tests done  
api/main.py → spawns mcp_server.py → exits when app stops
```

## Global MCP Client

The client uses a **global singleton** pattern to avoid starting multiple server instances:

```python
# First call: Creates client & spawns server
result1 = check_refund_eligibility_sync("ORD000001")  # Starts server

# Subsequent calls: Reuses existing client & server
result2 = check_refund_eligibility_sync("ORD000002")  # Reuses server
result3 = query_order_sync("ORD000003")               # Reuses server

# Server stays alive until:
# - Script exits
# - close_mcp_client() is called
# - Client is garbage collected
```

## Summary

| Question | Answer |
|----------|--------|
| Do I need to start the server? | ❌ No - client starts it automatically |
| Does the server run on a port? | ❌ No - uses stdio pipes |
| Can multiple clients share one server? | ❌ No - each client spawns its own |
| When does the server stop? | ✅ When client disconnects or script exits |
| Should I run server in terminal? | ⚠️ Only for debugging |

**Key Takeaway**: The MCP server is a **subprocess managed by the client**, not an independent service. Just run your tests or app, and the server will be automatically started and stopped as needed! 🚀
