import html
from markdown2 import markdown
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from wikidataMCP.tools import mcp, explore_wikidata

# Build the MCP ASGI app
mcp_app = mcp.http_app("/")

app = FastAPI(title="Wikidata MCP", lifespan=mcp_app.lifespan)

# Optional CORS if you access from browsers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in prod
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount MCP transport at /mcp
app.mount("/mcp", mcp_app)

# Minimal docs page
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def docs():
    tool_names = await mcp.get_tools()
    tool_names = tool_names.keys()
    tools_html = "\n".join(
        f"<li><code>{html.escape(name)}</code></li>" for name in tool_names
    )

    prompt = await mcp.get_prompt("explore_wikidata")
    prompt = await prompt.render({"query": "[User Prompt]"})
    prompt = markdown(prompt[0].content.text.strip())


    return f"""<!doctype html>
            <html>
            <head>
            <meta charset="utf-8">
            <title>Wikidata MCP Docs</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 2rem; }}
                code {{ background: #f5f5f5; padding: 0.2rem 0.4rem; border-radius: 4px; }}
                pre {{ background: #f5f5f5; padding: 1rem; border-radius: 8px; overflow:auto; }}
                .muted {{ color:#666; font-size:0.9em }}
            </style>
            </head>
            <body>
            <h1>Wikidata MCP</h1>
            <p>MCP endpoint is mounted at <code>/mcp</code>.</p>

            <h2>Tools</h2>
            <ul>
                {tools_html}
            </ul>

            <h2>Recommended Prompt</h2>
            {prompt}

            <h2>Links</h2>
            <p><a href="https://www.wikidata.org/wiki/Wikidata:MCP" target="_blank" rel="noopener">Wikidata page</a></p>
            <p><a href="https://github.com/philippesaade-wmde/WikidataMCP" target="_blank" rel="noopener">Github Repo</a></p>

            </body>
            </html>"""

if __name__ == "__main__":
    # Run: python server_fastapi.py
    uvicorn.run(app, host="0.0.0.0", port=8000)
