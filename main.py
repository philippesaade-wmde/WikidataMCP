from markdown2 import markdown
import uvicorn
from starlette.templating import Jinja2Templates
from wikidataMCP.tools import mcp

templates = Jinja2Templates(directory="templates")

# Homepage
@mcp.custom_route("/", methods=["GET"])
async def docs(request):
    tool_names = await mcp.get_tools()
    tool_names = tool_names.keys()

    prompt = await mcp.get_prompt("explore_wikidata")
    prompt = await prompt.render({"query": "[User Prompt]"})
    prompt = markdown(prompt[0].content.text)

    return templates.TemplateResponse(
        "docs.html",
        {
            "request": request,
            "tools": tool_names,
            "prompt": prompt,
        },
    )

# Build the MCP ASGI app
app = mcp.http_app()

if __name__ == "__main__":
    # Run: python server_fastapi.py
    uvicorn.run(app, host="0.0.0.0", port=8000)
