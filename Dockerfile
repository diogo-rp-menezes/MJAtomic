# Stage 1: Build Frontend
FROM node:20-alpine as builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 2: Runtime
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install Poetry and configure to install into system (no virtualenv)
RUN pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false

# Copy dependency files
COPY poetry.lock pyproject.toml ./

# Resolve/refresh lock file and install dependencies using poetry
RUN poetry lock --no-interaction --no-ansi \
    && poetry install --no-root --no-interaction --no-ansi

# Copy application code
COPY . .

# Copy frontend artifacts from builder
COPY --from=builder /app/frontend/dist /app/static

# Expose API port
EXPOSE 8001
