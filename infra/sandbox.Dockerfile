FROM python:3.11-slim

# Instala utilitÃ¡rios bÃ¡sicos e compiladores
RUN apt-get update && apt-get install -y \
    default-jdk \
    maven \
    nodejs \
    npm \
    build-essential \
    git \
    curl \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Instala Rust (Cargo)
ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/usr/local/cargo \
    PATH=/usr/local/cargo/bin:$PATH
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Instala Go (Golang 1.21)
RUN wget https://go.dev/dl/go1.21.6.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.21.6.linux-amd64.tar.gz && \
    rm go1.21.6.linux-amd64.tar.gz
ENV PATH=$PATH:/usr/local/go/bin

# Atualiza pip e instala pytest
RUN pip install --upgrade pip setuptools wheel pytest

WORKDIR /app
