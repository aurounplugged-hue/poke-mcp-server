from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse, Response
from mcp.server.sse import SseServerTransport
from mcp.server import Server
import mcp.types as types
import anthropic
import uvicorn
import os

app = Server(
    name="poke-mcp-server",
    version="1.0.0"
)
sse = SseServerTransport("/message/")

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

async def handle_sse(request):
    print("SSE connection initiated")
    async with sse.connect_sse(
        request.scope,
        request.receive,
        request.send
    ) as streams:
        await app.run(
            streams[0],
            streams[1],
            app.create_initialization_options()
        )

async def handle_message(request):
    print("Message received")
    await sse.handle_post_message(
        request.scope,
        request.receive,
        request.send
    )

async def handle_info(request):
    return JSONResponse({
        "name": "poke-mcp-server",
        "version": "1.0.0",
        "protocol_version": "2024-11-05"
    })

starlette_app = Starlette(
    routes=[
        Route("/", handle_info),
        Route("/sse", handle_sse),
        Route("/message", handle_message, methods=["POST"]),
    ]
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(starlette_app, host="0.0.0.0", port=port)
