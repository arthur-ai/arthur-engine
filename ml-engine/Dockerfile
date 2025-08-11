FROM python:3.13-slim AS install

# install poetry and wget
RUN pip install poetry==2.1.3 && \
    apt-get update && \
    apt-get install -y wget && \
    rm -rf /var/lib/apt/lists/*

# install dependencies
COPY pyproject.toml /app/
COPY poetry.lock /app/
COPY README.md /app/
WORKDIR /app
RUN poetry install --no-root

# copy ml-engine code
COPY src/ml_engine /app/src/ml_engine

# copy and install the genai client
RUN mkdir -p /genai_client
COPY src/genai_client /genai_client
RUN poetry run pip install /genai_client

# Final Stage(s): Create genai-engine image
FROM gcr.io/distroless/python3 AS ml-engine-distroless-base

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
COPY --from=install /root/.cache/pypoetry/virtualenvs/ /root/.cache/pypoetry/virtualenvs/
COPY --from=install /app/ /app/

ENV PATH="/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"
ENV PYTHONPATH="$PYTHONPATH:/app/src"

# Set working directory (this is where the entrypoint will be run)
WORKDIR /app

# start the ml-engine
# TODO: start using WSGI server instead of direct python run
ENTRYPOINT ["poetry", "run", "python", "src/ml_engine/job_agent.py"]
