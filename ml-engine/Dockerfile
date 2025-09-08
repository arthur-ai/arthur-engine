FROM python:3.13-slim-bookworm AS install

# install poetry and wget
RUN pip install poetry==2.1.3 && \
    apt-get update && \
    apt-get install -y wget && \
    rm -rf /var/lib/apt/lists/*

# install system dependencies for database drivers
RUN apt-get update && apt-get install -y \
    libpq-dev \
    postgresql-client \
    unixodbc \
    unixodbc-dev \
    libmariadb-dev \
    libmariadb-dev-compat \
    build-essential \
    python3-dev \
    libaio-dev \
    wget \
    unzip \
    git \
    && rm -rf /var/lib/apt/lists/*

# install Oracle Instant Client
RUN mkdir -p /opt/oracle && \
    wget -O /tmp/oracle-basic.zip https://download.oracle.com/otn_software/linux/instantclient/2112000/instantclient-basic-linux.x64-21.12.0.0.0dbru.zip && \
    wget -O /tmp/oracle-sdk.zip https://download.oracle.com/otn_software/linux/instantclient/2112000/instantclient-sdk-linux.x64-21.12.0.0.0dbru.zip && \
    unzip -q /tmp/oracle-basic.zip -d /opt/oracle && \
    unzip -q /tmp/oracle-sdk.zip -d /opt/oracle && \
    ln -sf /opt/oracle/instantclient_21_12 /opt/oracle/instantclient && \
    rm -f /tmp/oracle-basic.zip /tmp/oracle-sdk.zip

# Set Oracle environment variables
ENV ORACLE_HOME=/opt/oracle/instantclient
ENV LD_LIBRARY_PATH=/opt/oracle/instantclient:$LD_LIBRARY_PATH
ENV PATH=/opt/oracle/instantclient:$PATH

# Create a non-root user with home directory
RUN groupadd -r mluser && useradd -r -g mluser -m mluser

# Set working directory
WORKDIR /app

# install dependencies
COPY pyproject.toml /app/
COPY poetry.lock /app/
COPY README.md /app/

# Set ownership of app directory to mluser
RUN chown -R mluser:mluser /app

# Create poetry cache directory and set permissions
RUN mkdir -p /home/mluser/.cache/pypoetry/virtualenvs && \
    chown -R mluser:mluser /home/mluser/.cache

# Configure poetry to use the correct virtual environment directory
RUN mkdir -p /home/mluser/.config/pypoetry && \
    echo '[virtualenvs]\npath = "/home/mluser/.cache/pypoetry/virtualenvs"\nin-project = false' > /home/mluser/.config/pypoetry/config.toml && \
    chown -R mluser:mluser /home/mluser/.config

# Set environment variables for poetry
ENV POETRY_VENV_PATH="/home/mluser/.cache/pypoetry/virtualenvs"
ENV POETRY_CACHE_DIR="/home/mluser/.cache/pypoetry"

# Switch to non-root user for poetry install
USER mluser
ENV HOME="/home/mluser"
RUN poetry install --no-root

# Switch back to root to copy files and set permissions
USER root

# copy ml-engine code
COPY src/ml_engine /app/src/ml_engine

# copy and install the genai client
RUN mkdir -p /genai_client
COPY src/genai_client /genai_client

# Set ownership of all copied files to mluser
RUN chown -R mluser:mluser /app /genai_client

# Switch back to non-root user for pip install
USER mluser
RUN poetry run pip install /genai_client

# Final Stage(s): Create genai-engine image
FROM gcr.io/distroless/python3-debian12 AS ml-engine-distroless-base

# Create non-root user in the final stage
USER 1000:1000

COPY --from=install /bin/sh /bin/sh
COPY --from=install /bin/bash /bin/bash
COPY --from=install /bin/env /bin/env
COPY --from=install /usr/bin/sh /usr/bin/sh
COPY --from=install /usr/bin/bash /usr/bin/bash
COPY --from=install /usr/bin/env /usr/bin/env
COPY --from=install /usr/bin/printenv /usr/bin/printenv
COPY --from=install /usr/bin/wget /usr/bin/wget
COPY --from=install /usr/lib /usr/lib
COPY --from=install /usr/local/lib/ /usr/local/lib/
COPY --from=install /usr/local/bin/ /usr/local/bin/
COPY --from=install /etc/ld.so.cache /etc/ld.so.cache
COPY --from=install /home/mluser/.cache/pypoetry/virtualenvs/ /home/mluser/.cache/pypoetry/virtualenvs/
COPY --from=install /home/mluser/.config/pypoetry/ /home/mluser/.config/pypoetry/
COPY --from=install /app/ /app/
COPY --from=install /opt/oracle/ /opt/oracle/

ENV PATH="/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"
ENV PYTHONPATH="$PYTHONPATH:/app/src"
ENV HOME="/home/mluser"
ENV POETRY_VENV_PATH="/home/mluser/.cache/pypoetry/virtualenvs"
ENV POETRY_CACHE_DIR="/home/mluser/.cache/pypoetry"

# Set working directory (this is where the entrypoint will be run)
WORKDIR /app

# start the ml-engine
# TODO: start using WSGI server instead of direct python run
ENTRYPOINT ["poetry", "run", "python", "src/ml_engine/job_agent.py"]
