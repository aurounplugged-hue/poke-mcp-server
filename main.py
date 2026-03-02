from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse, Response
from mcp.server.sse import SseServerTransport
from mcp.server import Server
import mcp.types as types
import anthropic
import uvicorn
import os
app = Server("poke-mcp-server")
sse = SseServerTransport("/message/")
@app.list_tools()
async def list_tools() -> list[types.Tool]:
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
if name == "ask_claude":
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
message = client.messages.create(
model="claude-sonnet-4-20250514",
max_tokens=1024,
messages=[{"role": "user", "content": arguments["prompt"]}]
)
return [types.TextContent(type="text", text=message.content[0].text)]
async def handle_sse(request):
async with sse.connect_sse(
request.scope,
request.receive,
request._send
) as streams:
await app.run(
streams[0],
streams[1],
app.create_initialization_options()
)
return Response()
async def handle_message(request):
await sse.handle_post_message(
request.scope,
request.receive,
request._send
)
return Response()
async def handle_info(request):
return JSONResponse({
"name": "poke-mcp-server",
"version": "1.0.0",
"protocol_version": "2025-06-18"
})
starlette_app = Starlette(
routes=[
Route("/", handle_info),
Route("/sse", handle_sse),
Route("/message", handle_message, methods=["POST"]),
]
)
if name == "main":
uvicorn.run(starlette_app, host="0.0.0.0", port=5000)
