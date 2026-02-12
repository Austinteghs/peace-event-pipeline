# Multi-stage Dockerfile for GCP Cloud Run
FROM python:3.10-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements_gcp.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements_gcp.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps

# Copy scraper code
COPY . .

# Build argument for scraper folder
ARG SCRAPER_FOLDER
ENV SCRAPER_FOLDER=${SCRAPER_FOLDER}

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
echo "Starting scraper: ${SCRAPER_FOLDER}"\n\
python ${SCRAPER_FOLDER}/scraper.py\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Run the scraper
ENTRYPOINT ["/app/entrypoint.sh"]