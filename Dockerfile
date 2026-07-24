FROM python:3.14-slim

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl gnupg2 \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

WORKDIR /app

# Install Python dependencies and Playwright browsers
# (these layers are cached and rarely change)
RUN uv pip install --system requests playwright tzdata \
    && python -m playwright install --with-deps chromium

# Create output directory
RUN mkdir -p /app/output

# Set default output directory
ENV OUTPUT_DIR=/app/output/

# Copy the script last — changes to prices.py won't invalidate the
# cached dependency layers above.
COPY prices.py .

# Run the script on container start
CMD ["python", "prices.py"]
