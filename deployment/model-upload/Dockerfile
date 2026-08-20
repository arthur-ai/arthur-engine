# Model Upload - Multi-stage build with three named runtime targets
#
# Build args:
#   BACKEND: s3 (ECS) | gcs (GCP) | fs (K8s PVC / EFS / any mounted volume)  [default: s3]
#
# Build commands:
#   docker build --build-arg BACKEND=s3  --target runtime-s3  -t <image> .
#   docker build --build-arg BACKEND=gcs --target runtime-gcs -t <image> .
#   docker build --build-arg BACKEND=fs  --target runtime-fs  -t <image> .
#
# Runtime is Python 3.12 (per requires-python) on Debian bookworm. The distroless
# runtimes (s3, fs) copy the apt-upgraded Python 3.12 runtime + patched system
# libraries from the builder stage over the distroless base (whose own python3 is
# the unused, vulnerable 3.11, which is removed). Images are linux/amd64 only.

ARG BACKEND=s3

# The distroless base is referenced here so the builder stage can read the dpkg
# metadata it ships (see the status.d sync at the end of that stage), in addition to
# the runtime-s3/runtime-fs stages below. The same tag resolves to the same digest
# within one build, so this adds a metadata read, not a second base image.
FROM gcr.io/distroless/python3-debian12:nonroot AS distroless_meta

# =============================================================================
# Stage 1: Download models (shared across all backends)
# =============================================================================
FROM python:3.12-slim-bookworm AS downloader
ARG BACKEND
# Stamped into metadata.component.version of the AI-BOM (passed as a build-arg in CI).
ARG AIBOM_VERSION=unknown

WORKDIR /app
RUN pip install --no-cache-dir uv==0.12.0
COPY pyproject.toml uv.lock* ./

RUN uv export --frozen --no-emit-project --no-hashes -o /tmp/requirements.txt \
    && uv pip install --system --no-cache -r /tmp/requirements.txt

COPY download_models.py generate_aibom.py models-manifest.json ./

RUN python download_models.py --output-dir /models --workers 4

# Generate the CycloneDX AI-BOM for the bundled models into /models so it ships to the
# storage backend (S3/GCS/FS) alongside the weights via upload_models.py. Hashes are
# computed locally from the freshly downloaded files; license/task come from HuggingFace.
RUN python generate_aibom.py \
      --models-dir /models \
      --manifest models-manifest.json \
      --engine-version "$AIBOM_VERSION" \
      --output /models/aibom.cdx.json

# =============================================================================
# Stage 2: Install backend-specific runtime deps + apply Debian security fixes
#   - s3:  boto3
#   - gcs: google-cloud-storage
#   - fs:  nothing (stdlib only)
#
# `apt-get upgrade` patches base-image OS CVEs (libssl3, libc6, ...). The upgraded
# shared objects in /usr/lib and the Python 3.12 runtime in /usr/local are copied
# into the distroless runtime images below, so the binaries that actually ship
# contain the fixes (the distroless base's dpkg metadata, which scanners read,
# stays stale — see security/vex/openvex.json).
# =============================================================================
FROM python:3.12-slim-bookworm AS builder
ARG BACKEND

RUN apt-get update && apt-get upgrade -y && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN pip install --no-cache-dir uv==0.12.0
COPY pyproject.toml uv.lock* ./

RUN if [ "$BACKEND" != "fs" ]; then \
      uv export --frozen --no-emit-project --no-hashes --extra "$BACKEND" \
        -o /tmp/requirements.txt \
      && pip install --target=/app/site-packages --no-cache \
           -r /tmp/requirements.txt; \
    fi

# Patch the libraries the distroless base keeps in /lib. Unlike bookworm, the base
# is NOT merged-/usr: /lib is a real directory holding glibc (libc.so.6, libm,
# libpthread, libnss_*, and the ELF interpreter that /lib64 symlinks to) plus
# liblzma, libexpat, libgcc_s, libbz2, libcom_err, libcrypt, libkeyutils,
# libncursesw and libreadline. `COPY --from=builder /usr/lib /usr/lib` in the
# distroless runtimes does not reach any of them, so they stayed at the base's
# versions in every image shipped so far — the libc6 and liblzma5 CVEs scanners
# report against them are real, not stale metadata. (The libssl3 and krb5 objects do
# live under /usr/lib and were genuinely being patched.)
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
# actually installed. With the /lib mirror above and `COPY /usr/lib` in the
# distroless runtimes, the base's shared objects are replaced by the apt-upgraded
# ones from bookworm-security, but the base's /var/lib/dpkg/status.d keeps
# advertising the versions it was built with. Scanners resolve OS-package CVEs from
# that metadata (Wiz reports these as `detectionMethod: PACKAGE`), so they flag
# already-fixed CVEs against libssl3/libkrb5* indefinitely and block downstream
# image-policy gates — the situation security/vex/openvex.json documents.
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

# =============================================================================
# Runtime: ECS / S3  (distroless)
# =============================================================================
FROM gcr.io/distroless/python3-debian12:nonroot AS runtime-s3

# Bring the apt-upgraded Python 3.12 runtime and patched system libraries from the
# builder over the distroless base (whose own python3 is the unused, vulnerable 3.11).
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY --from=builder /usr/local/lib/ /usr/local/lib/
COPY --from=builder /usr/lib /usr/lib
# The base keeps real glibc/liblzma/libexpat/... files in /lib (it is not
# merged-/usr), which the /usr/lib copy above does not reach. See builder stage.
COPY --from=builder /tmp/patched-lib /lib
COPY --from=builder /etc/ld.so.cache /etc/ld.so.cache
# dpkg metadata corrected to match the shared objects copied above (see builder stage).
# Must precede the python3.11 cleanup below, which deletes three of these stanzas.
COPY --from=builder /tmp/dpkg-status.d /var/lib/dpkg/status.d

# Remove the unused Python 3.11 runtime inherited from the distroless base so it
# neither ships nor trips scanners (CVE-2025-8194, CVE-2025-13836). The job runs on
# Python 3.12 from /usr/local. distroless has no shell, so use exec-form rm with
# explicit amd64 paths (these images are linux/amd64 only); rm deletes itself last.
USER root
COPY --from=builder /usr/bin/rm /usr/bin/rm
RUN ["/usr/bin/rm", "-rf", \
     "/usr/lib/python3.11", \
     "/usr/bin/python3.11", \
     "/usr/lib/x86_64-linux-gnu/libpython3.11.so.1.0", \
     "/var/lib/dpkg/status.d/python3.11-minimal", \
     "/var/lib/dpkg/status.d/libpython3.11-minimal", \
     "/var/lib/dpkg/status.d/libpython3.11-stdlib", \
     "/usr/bin/rm"]
USER nonroot

WORKDIR /app
COPY --from=builder /app/site-packages /app/site-packages
COPY --from=downloader /models /models
COPY --chown=nonroot:nonroot upload_models.py /app/

ENV BACKEND=s3 \
    PATH="/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin" \
    PYTHONPATH=/app/site-packages \
    MODELS_DIR=/models \
    LOG_LEVEL=INFO

ENTRYPOINT ["python", "/app/upload_models.py"]

# =============================================================================
# Runtime: Filesystem / FS  (distroless — no extra deps, stdlib only)
# Covers any mounted volume: K8s PVC, AWS EFS, OpenShift, etc.
# Set TARGET_DIR to the mount path at runtime (default: /models-output)
# =============================================================================
FROM gcr.io/distroless/python3-debian12:nonroot AS runtime-fs

# Bring the apt-upgraded Python 3.12 runtime and patched system libraries from the
# builder over the distroless base (whose own python3 is the unused, vulnerable 3.11).
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY --from=builder /usr/local/lib/ /usr/local/lib/
COPY --from=builder /usr/lib /usr/lib
# The base keeps real glibc/liblzma/libexpat/... files in /lib (it is not
# merged-/usr), which the /usr/lib copy above does not reach. See builder stage.
COPY --from=builder /tmp/patched-lib /lib
COPY --from=builder /etc/ld.so.cache /etc/ld.so.cache
# dpkg metadata corrected to match the shared objects copied above (see builder stage).
# Must precede the python3.11 cleanup below, which deletes three of these stanzas.
COPY --from=builder /tmp/dpkg-status.d /var/lib/dpkg/status.d

# Remove the unused Python 3.11 runtime inherited from the distroless base (see s3 stage).
USER root
COPY --from=builder /usr/bin/rm /usr/bin/rm
RUN ["/usr/bin/rm", "-rf", \
     "/usr/lib/python3.11", \
     "/usr/bin/python3.11", \
     "/usr/lib/x86_64-linux-gnu/libpython3.11.so.1.0", \
     "/var/lib/dpkg/status.d/python3.11-minimal", \
     "/var/lib/dpkg/status.d/libpython3.11-minimal", \
     "/var/lib/dpkg/status.d/libpython3.11-stdlib", \
     "/usr/bin/rm"]
USER nonroot

WORKDIR /app
COPY --from=downloader /models /models
COPY --chown=nonroot:nonroot upload_models.py /app/

ENV BACKEND=fs \
    PATH="/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin" \
    MODELS_DIR=/models \
    TARGET_DIR=/models-output \
    LOG_LEVEL=INFO

ENTRYPOINT ["python", "/app/upload_models.py"]

# =============================================================================
# Runtime: GCP / GCS  (slim — google-auth requires libffi)
# apt-get upgrade patches base OS CVEs here directly (the slim image's dpkg
# metadata is updated too, so scanners see the fixed versions).
# =============================================================================
FROM python:3.12-slim-bookworm AS runtime-gcs

RUN apt-get update && apt-get upgrade -y && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN useradd --uid 65532 --no-create-home nonroot

WORKDIR /app
COPY --from=builder /app/site-packages /app/site-packages
COPY --from=downloader /models /models
COPY upload_models.py /app/

ENV BACKEND=gcs \
    PYTHONPATH=/app/site-packages \
    MODELS_DIR=/models \
    LOG_LEVEL=INFO

USER nonroot
ENTRYPOINT ["python", "/app/upload_models.py"]
