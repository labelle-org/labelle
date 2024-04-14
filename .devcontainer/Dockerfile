FROM mcr.microsoft.com/devcontainers/python:1-3.12-bullseye

ARG deps="\
    libdbus-1-3 \
    libegl1 \
    libgl1 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-keysyms1 \
    libxcb-shape0 \
    libxkbcommon-x11-0 \
    "
RUN apt-get update \
    && apt-get install -y ${deps} \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/lib/apt/lists/*

ARG pip_deps="\
    pre-commit \
    ruff \
    tox \
    mypy \
    "
RUN pip install --upgrade pip \
    && pip install ${pip_deps}

# Preinstall the dependencies (extremely hacky)
COPY ../pyproject.toml /tmp/temp-project/pyproject.toml
RUN touch /tmp/temp-project/README.md \
    && cd /tmp/temp-project \
    && git init \
    && mkdir -p src/labelle \
    && echo '__version__ = "0.0.0"' > src/labelle/_version.py \
    && pip install -e . \
    && pip uninstall -y labelle \
    && rm -rf /tmp/temp-project
