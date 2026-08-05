# The distroless base is referenced twice: here, so the install stage can read the
# dpkg metadata it ships (see the status.d sync at the end of that stage), and again
# as the final image below. The same tag resolves to the same digest within one
# build, so this adds a metadata read, not a second base image.
FROM --platform=linux/amd64 gcr.io/distroless/python3-debian12:nonroot AS distroless_meta

FROM --platform=linux/amd64 python:3.13-slim-bookworm AS install

# install uv and wget; upgrade OS packages for Debian security fixes
# (libssl3, libc6, libexpat1, ...). These libraries live in /usr/lib and are
# copied into the distroless final image below, so upgrading here patches the
# shared objects that actually ship.
RUN pip install uv==0.12.0 && \
    apt-get update && \
    apt-get upgrade -y && \
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
COPY uv.lock /app/
COPY README.md /app/
WORKDIR /app
RUN uv export --frozen \
    --no-group dev --no-group linters \
    --no-emit-project \
    -o /tmp/requirements.txt \
    && uv pip install --system --no-cache -r /tmp/requirements.txt

# copy ml-engine code
COPY src/ml_engine /app/src/ml_engine

# copy and install the genai client
RUN mkdir -p /genai_client
COPY src/genai_client /genai_client
RUN uv pip install --system /genai_client

# Patch the libraries the distroless base keeps in /lib. Unlike bookworm, the base
# is NOT merged-/usr: /lib is a real directory holding glibc (libc.so.6, libm,
# libpthread, libnss_*, and the ELF interpreter that /lib64 symlinks to) plus
# liblzma, libexpat, libgcc_s, libbz2, libcom_err, libcrypt, libkeyutils,
# libncursesw and libreadline. `COPY --from=install /usr/lib /usr/lib` in the final
# stage does not reach any of them, so they stayed at the base's versions in every
# image shipped so far — the libc6 and liblzma5 CVEs scanners report against them
# are real, not stale metadata. (The libssl3 and krb5 objects do live under
# /usr/lib and were genuinely being patched.)
#
# Mirror the base's /lib layout using this stage's apt-upgraded libraries. Only
# paths the base already has are emitted, so this replaces files rather than adding
# any, and the base's layout is preserved. In this stage /lib is a symlink to
# /usr/lib, hence the /usr/lib source path.
COPY --from=distroless_meta /lib /tmp/base-lib
RUN set -eu; \
    out=/tmp/patched-lib; rm -rf "$out"; mkdir -p "$out"; \
    cd /tmp/base-lib; \
    find . -mindepth 1 \( -type f -o -type l \) -print | while IFS= read -r p; do \
      rel="${p#./}"; src="/usr/lib/${rel}"; \
      { [ -e "$src" ] || [ -L "$src" ]; } || continue; \
      mkdir -p "$out/$(dirname "$rel")"; \
      cp -a "$src" "$out/$rel"; \
      echo "  /lib patch: ${rel}"; \
    done

# Rewrite the distroless base's dpkg metadata to the package versions this stage
# actually installed. With the /lib mirror above and `COPY /usr/lib` in the final
# stage, the base's shared objects are replaced by the apt-upgraded ones from
# bookworm-security, but the base's /var/lib/dpkg/status.d keeps advertising the
# versions it was built with. Scanners resolve OS-package CVEs from that metadata
# (Wiz reports these as `detectionMethod: PACKAGE`), so they flag already-fixed
# CVEs against libssl3/libkrb5* indefinitely and block downstream image-policy
# gates — the situation security/vex/openvex.json documents.
#
# Only packages that this stage has installed AND that ship a shared object under
# /lib|/usr/lib/<triplet>/ are synced: those, and only those, are the files the two
# copies overwrite, so the synced version is what genuinely ships. (Both prefixes
# are matched because bookworm packages are split between them.) Packages the base
# ships but this stage lacks keep their original version — their files survive
# untouched.
#
# The md5sums sidecars are refreshed from this stage's dpkg database, resolved via
# `dpkg-query --control-path` rather than by composing the path: dpkg stores those
# files arch-qualified (libc6:amd64.md5sums) for Multi-Arch: same packages, which
# every package selected above is, so a hand-built /var/lib/dpkg/info/<pkg>.md5sums
# never exists. The refreshed lists match every shipped shared object byte-for-byte;
# their /usr/share/doc entries (changelog, NEWS) stay stale because these images
# never copy /usr/share. That residue is inert — no scanner resolves CVEs from
# checksums — but the shared objects, which the Version above now claims, do match.
COPY --from=distroless_meta /var/lib/dpkg/status.d /tmp/base-status.d
RUN set -eu; \
    out=/tmp/dpkg-status.d; \
    rm -rf "$out"; cp -a /tmp/base-status.d "$out"; \
    for f in "$out"/*; do \
      pkg="${f##*/}"; \
      case "$pkg" in *.md5sums) continue ;; esac; \
      dpkg-query -L "$pkg" 2>/dev/null | grep -qE '^(/usr)?/lib/[^/]*-linux-gnu/.*\.so' || continue; \
      ver="$(dpkg-query -W -f='${Version}' "$pkg" 2>/dev/null)" || continue; \
      [ -n "$ver" ] || continue; \
      sed -i "s/^Version: .*/Version: ${ver}/" "$f"; \
      if src="$(dpkg-query --control-path "$pkg" md5sums 2>/dev/null)" && [ -f "$src" ]; then \
        cp "$src" "${f}.md5sums"; \
      fi; \
      echo "  dpkg-status sync: ${pkg} -> ${ver}"; \
    done

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
# The base keeps real glibc/liblzma/libexpat/... files in /lib (it is not
# merged-/usr), which the /usr/lib copy above does not reach. See install stage.
COPY --from=install /tmp/patched-lib /lib
COPY --from=install /usr/local/lib/ /usr/local/lib/
COPY --from=install /usr/local/bin/ /usr/local/bin/
COPY --from=install /etc/ld.so.cache /etc/ld.so.cache
# dpkg metadata corrected to match the shared objects copied above (see install stage).
# Must precede the python3.11 cleanup below, which deletes three of these stanzas.
COPY --from=install /tmp/dpkg-status.d /var/lib/dpkg/status.d
COPY --from=install /opt/oracle/ /opt/oracle/
COPY --from=install /opt/microsoft/msodbcsql18 /opt/microsoft/msodbcsql18
COPY --from=install /opt/microsoft/msodbcsql17 /opt/microsoft/msodbcsql17
COPY --from=install /etc/odbcinst.ini /etc/odbcinst.ini
COPY --from=install --chown=nonroot:nonroot /app/ /home/nonroot/app/

# Remove the unused Python 3.11 runtime inherited from the distroless base.
# The app runs on Python 3.13 (from /usr/local); the distroless base ships a
# separate, never-executed Python 3.11 that image scanners keep flagging
# (e.g. CVE-2025-8194, CVE-2025-13836). Delete the files and their dpkg
# metadata so neither the runtime nor the SBOM advertise it. distroless has no
# `rm`, so copy it from the build stage and delete it again in the same layer.
USER root
COPY --from=install /usr/bin/rm /usr/bin/rm
RUN /usr/bin/rm -rf \
      /usr/lib/python3.11 \
      /usr/bin/python3.11 \
      /usr/lib/*-linux-gnu/libpython3.11.so* \
      /var/lib/dpkg/status.d/python3.11-minimal \
      /var/lib/dpkg/status.d/libpython3.11-minimal \
      /var/lib/dpkg/status.d/libpython3.11-stdlib \
    && /usr/bin/rm /usr/bin/rm
USER nonroot

ENV PATH="/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"
ENV PYTHONPATH="$PYTHONPATH:/home/nonroot/app/src"
ENV LD_LIBRARY_PATH="/opt/microsoft/msodbcsql18/lib64:/opt/microsoft/msodbcsql17/lib64:/opt/oracle/instantclient:${LD_LIBRARY_PATH}"
ENV ODBCSYSINI="/etc"

# Set working directory (this is where the entrypoint will be run)
WORKDIR /home/nonroot/app

# start the ml-engine
ENTRYPOINT ["python", "src/ml_engine/job_agent.py"]
