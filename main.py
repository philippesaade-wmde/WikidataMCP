from wikidataMCP.tools import mcp
import uvicorn

app = mcp.http_app()

if __name__ == "__main__":
    # mcp.run(transport="http", host="0.0.0.0", path='/mcp')
    uvicorn.run(app, host="0.0.0.0", port=8000)
