FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir mcp asyncpg httpx pydantic
ENV PYTHONPATH=/app/src \
    MCP_TRANSPORT=http \
    MCP_PORT=8090 \
    PGHOST=app-db PGUSER=postgres PGDATABASE=gluvex_documents \
    MEMPALACE_URL=http://mempalace-gluvex:8080
EXPOSE 8090
CMD ["python", "-m", "gluvex_catalog_mcp.server"]
