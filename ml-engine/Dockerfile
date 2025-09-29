FROM --platform=linux/amd64 python:3.13-slim-bookworm AS install

# install poetry and wget
RUN pip install poetry==2.1.3 && \
    apt-get update && \
    apt-get install -y wget curl gnupg apt-transport-https && \
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
    && rm -rf /var/lib/apt/lists/*

# install Microsoft ODBC Drivers 17 and 18
RUN echo "deb [arch=amd64 signed-by=/usr/share/keyrings/msprod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
      > /etc/apt/sources.list.d/msprod.list && \
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/msprod.gpg && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql18 msodbcsql17 mssql-tools18 && \
    rm -rf /var/lib/apt/lists/*

# configure ODBC drivers
RUN set -eux; \
    DRV18="$(basename /opt/microsoft/msodbcsql18/lib64/libmsodbcsql-*.so* | head -n1)"; \
    DRV17="$(basename /opt/microsoft/msodbcsql17/lib64/libmsodbcsql-*.so* | head -n1)"; \
    printf '%s\n' \
      "[ODBC Driver 18 for SQL Server]" \
      "Description=Microsoft ODBC Driver 18 for SQL Server" \
      "Driver=/opt/microsoft/msodbcsql18/lib64/${DRV18}" \
      "UsageCount=1" \
      "" \
      "[ODBC Driver 17 for SQL Server]" \
      "Description=Microsoft ODBC Driver 17 for SQL Server" \
      "Driver=/opt/microsoft/msodbcsql17/lib64/${DRV17}" \
      "UsageCount=1" \
      > /etc/odbcinst.ini

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

# install dependencies
COPY pyproject.toml /app/
COPY poetry.lock /app/
COPY README.md /app/
WORKDIR /app
RUN poetry config virtualenvs.create false && poetry install --no-root

# copy ml-engine code
COPY src/ml_engine /app/src/ml_engine

# copy and install the genai client
RUN mkdir -p /genai_client
COPY src/genai_client /genai_client
RUN poetry run pip install /genai_client

# Final Stage(s): Create ml-engine image
FROM --platform=linux/amd64 gcr.io/distroless/python3-debian12:nonroot AS ml-engine-distroless-base

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
COPY --from=install /opt/oracle/ /opt/oracle/
COPY --from=install /opt/microsoft/msodbcsql18 /opt/microsoft/msodbcsql18
COPY --from=install /opt/microsoft/msodbcsql17 /opt/microsoft/msodbcsql17
COPY --from=install /etc/odbcinst.ini /etc/odbcinst.ini
COPY --from=install --chown=nonroot:nonroot /app/ /home/nonroot/app/
COPY --from=install --chown=nonroot:nonroot /root/.cache/pypoetry/ /home/nonroot/.cache/pypoetry/
COPY --from=install --chown=nonroot:nonroot /root/.config/pypoetry/ /home/nonroot/.config/pypoetry/

ENV PATH="/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"
ENV PYTHONPATH="$PYTHONPATH:/home/nonroot/app/src"
ENV POETRY_VIRTUALENVS_PATH="/home/nonroot/.cache/pypoetry/virtualenvs"
ENV POETRY_CACHE_DIR="/home/nonroot/.cache/pypoetry"
ENV LD_LIBRARY_PATH="/opt/microsoft/msodbcsql18/lib64:/opt/microsoft/msodbcsql17/lib64:/opt/oracle/instantclient:${LD_LIBRARY_PATH}"
ENV ODBCSYSINI="/etc"

# Set working directory (this is where the entrypoint will be run)
WORKDIR /home/nonroot/app

# start the ml-engine
ENTRYPOINT ["poetry", "run", "python", "src/ml_engine/job_agent.py"]
