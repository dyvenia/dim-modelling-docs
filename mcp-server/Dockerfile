# Remote (HTTP) deployment of the docs MCP server.
# Build from the REPO ROOT so the docs in ../src are included:
#   docker build -f mcp-server/Dockerfile -t dim-docs-mcp .
#   docker run -p 8000:8000 dim-docs-mcp
# The server is then reachable at http://localhost:8000/mcp
FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir "fastmcp>=2.0.0"

# Server code and the documentation it serves.
COPY mcp-server/ ./mcp-server/
COPY src/ ./src/

# Run as an HTTP service; DOCS_SRC points at the copied docs.
ENV MCP_TRANSPORT=http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    DOCS_SRC=/app/src

EXPOSE 8000

CMD ["python", "mcp-server/server.py"]
