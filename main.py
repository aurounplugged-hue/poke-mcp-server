from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse
from starlette.requests import Request
from mcp.server.sse import SseServerTransport
from mcp.server import Server
import mcp.types as types
import anthropic
import httpx
import uvicorn
import os

app = Server(
    name="poke-mcp-server",
    version="1.0.0"
)
sse = SseServerTransport("/messages")

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    print("list_tools called")
    return [
        types.Tool(
            name="ask_claude",
            description="Ask Claude (Anthropic) a question",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Your question or request"}
                },
                "required": ["prompt"]
            }
        ),
        types.Tool(
            name="ask_chatgpt",
            description="Ask ChatGPT (OpenAI) a question",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Your question or request"}
                },
                "required": ["prompt"]
            }
        ),
        types.Tool(
            name="ask_gemini",
            description="Ask Gemini (Google) a question",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Your question or request"}
                },
                "required": ["prompt"]
            }
        ),
        types.Tool(
            name="ask_deepseek",
            description="Ask DeepSeek a question",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Your question or request"}
                },
                "required": ["prompt"]
            }
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    print(f"call_tool called: {name}")
    prompt = arguments.get("prompt", "")
    if not prompt:
        return [types.TextContent(type="text", text="Error: No prompt provided.")]

    try:
        if name == "ask_claude":
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                return [types.TextContent(type="text", text="Error: ANTHROPIC_API_KEY is not set.")]
            client = anthropic.Anthropic(api_key=api_key)
            message = client.messages.create(
                model="claude-3-5-sonnet-latest",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            text = ""
            if hasattr(message, "content") and message.content:
                first = message.content[0]
                text = getattr(first, "text", "") or "No response."
            return [types.TextContent(type="text", text=text or "No response.")]

        elif name == "ask_chatgpt":
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                return [types.TextContent(type="text", text="Error: OPENAI_API_KEY is not set.")]
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}]}
                )
                if response.status_code != 200:
                    return [types.TextContent(type="text", text=f"OpenAI error {response.status_code}: {response.text}")]
                result = response.json()
                choices = result.get("choices", [])
                text = choices[0].get("message", {}).get("content", "No response.") if choices else "No response."
                return [types.TextContent(type="text", text=text)]

        elif name == "ask_gemini":
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                return [types.TextContent(type="text", text="Error: GEMINI_API_KEY is not set.")]
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
                    json={"contents": [{"parts": [{"text": prompt}]}]}
                )
                if response.status_code != 200:
                    return [types.TextContent(type="text", text=f"Gemini error {response.status_code}: {response.text}")]
                result = response.json()
                candidates = result.get("candidates", [])
                text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "No response.") if candidates else "No response."
                return [types.TextContent(type="text", text=text)]

        elif name == "ask_deepseek":
            api_key = os.environ.get("DEEPSEEK_API_KEY")
            if not api_key:
                return [types.TextContent(type="text", text="Error: DEEPSEEK_API_KEY is not set.")]
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://api.deepseek.com/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}]}
                )
                if response.status_code != 200:
                    return [types.TextContent(type="text", text=f"DeepSeek error {response.status_code}: {response.text}")]
                result = response.json()
                choices = result.get("choices", [])
                text = choices[0].get("message", {}).get("content", "No response.") if choices else "No response."
                return [types.TextContent(type="text", text=text)]

        else:
            return [types.TextContent(type="text", text=f"Error: Unknown tool {name}")]

    except httpx.TimeoutException:
        return [types.TextContent(type="text", text=f"Error: Request to {name} timed out.")]
    except Exception as e:
        print(f"Error in call_tool [{name}]: {e}")
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]

async def handle_sse(request: Request):
    print("SSE connection initiated")
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

async def handle_info(request: Request):
    return JSONResponse({
        "name": "poke-mcp-server",
        "version": "1.0.0",
        "protocol_version": "2024-11-05"
    })

async def messages_asgi(scope, receive, send):
    print("Message received")
    await sse.handle_post_message(scope, receive, send)

starlette_app = Starlette(
    routes=[
        Route("/", handle_info),
        Route("/sse", endpoint=handle_sse, methods=["GET"]),
    ]
)

async def root_app(scope, receive, send):
    if scope["type"] == "http" and scope["path"] == "/messages":
        await messages_asgi(scope, receive, send)
    else:
        await starlette_app(scope, receive, send)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(root_app, host="0.0.0.0", port=port)
