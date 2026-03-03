from mcp.server import Server
from mcp.server.sse import SseServerTransport
import mcp.types as types
import anthropic
import uvicorn
import os

app = Server(
    name="poke-mcp-server",
    version="1.0.0"
)

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    print("list_tools called")
    return [
        types.Tool(
            name="ask_claude",
            description="Ask Claude a question or request",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Your question or request"}
                },
                "required": ["prompt"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    print(f"call_tool called: {name}")
    try:
        if name == "ask_claude":
            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            message = client.messages.create(
                model="claude-3-5-sonnet-latest",
                max_tokens=1024,
                messages=[{"role": "user", "content": arguments["prompt"]}]
            )
            return [types.TextContent(type="text", text=message.content[0].text)]
    except Exception as e:
        print(f"Error in call_tool: {e}")
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]

starlette_app = app.create_starlette_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(starlette_app, host="0.0.0.0", port=port)
