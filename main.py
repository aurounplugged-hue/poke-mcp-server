from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse, Response
from mcp.server.sse import SseServerTransport
from mcp.server import Server
import mcp.types as types
import uvicorn

app = Server("poke-mcp-server")
sse = SseServerTransport("/message/")

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return []

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    return []

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

if __name__ == "__main__":
    uvicorn.run(starlette_app, host="0.0.0.0", port=5000)
