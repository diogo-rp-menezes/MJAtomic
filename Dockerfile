# Dockerfile

# 1. Base Image
FROM python:3.11-slim

# 2. Set working directory
WORKDIR /app

# 3. Install Poetry and configure to install into system (no virtualenv)
RUN pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false

# 4. Copy dependency files
COPY poetry.lock pyproject.toml ./

# 5. Install dependencies using poetry
# --no-root: não instala o projeto em si, apenas as dependências
# Sem virtualenv e sem interação para builds reprodutíveis
RUN poetry install --no-root --no-interaction --no-ansi

# 6. Copy application code
COPY . .

# 7. Expose API port
EXPOSE 8001
