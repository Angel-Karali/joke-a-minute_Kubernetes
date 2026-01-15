# ============================================
# Stage 1: Builder Stage
# ============================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    libmariadb-dev \
    pkg-config && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies to /install
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============================================
# Stage 2: Runtime Stage (Minimal)
# ============================================
FROM python:3.11-slim

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Install only runtime dependencies (minimal)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libmariadb3 \
    curl && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Python packages (lib) from builder
COPY --from=builder /install/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy binaries (bin) from builder - THIS WAS MISSING!
COPY --from=builder /install/bin/* /usr/local/bin/

# Copy application code
COPY --chown=appuser:appuser app.py .
COPY --chown=appuser:appuser init_db.py .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "app:app"]