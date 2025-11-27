# Selenium MCP Server Dockerfile
FROM python:3.14-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files and install package
COPY pyproject.toml .
COPY requirements.txt .
COPY src/ src/

# Install the package (this makes selenium_mcp importable)
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check - verify server is responding (FastMCP serves at /mcp)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:8000/ > /dev/null || exit 1

# Expose MCP HTTP port
EXPOSE 8000

# Use exec form so Python receives signals directly as PID 1
CMD ["python", "-m", "selenium_mcp"]
