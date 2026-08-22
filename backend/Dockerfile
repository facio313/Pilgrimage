FROM python:3.13-slim

ARG PORTFOLIO_BRANCH
ARG PORTFOLIO_AUTH_MODE
RUN case "$PORTFOLIO_BRANCH" in ""|*[!A-Za-z0-9._/-]*) exit 1 ;; esac \
    && normalized_branch="${PORTFOLIO_BRANCH#refs/heads/}" \
    && case "$normalized_branch" in ""|*[!A-Za-z0-9._/-]*) exit 1 ;; esac \
    && case "$normalized_branch:$PORTFOLIO_AUTH_MODE" in \
         main:sso|dev:sso) ;; \
         main:*|dev:*) exit 1 ;; \
         *:local) ;; \
         *) exit 1 ;; \
       esac \
    && printf '%s\n%s\n' "$normalized_branch" "$PORTFOLIO_AUTH_MODE" \
         > /etc/portfolio-auth-build \
    && chmod 0444 /etc/portfolio-auth-build
ENV PORTFOLIO_BRANCH=${PORTFOLIO_BRANCH} \
    PORTFOLIO_AUTH_MODE=${PORTFOLIO_AUTH_MODE} \
    PORTFOLIO_BUILD_AUTH_MODE=${PORTFOLIO_AUTH_MODE}

RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin libgdal-dev libgeos-dev libproj-dev \
    && rm -rf /var/lib/apt/lists/*

ENV GDAL_LIBRARY_PATH=/usr/lib/aarch64-linux-gnu/libgdal.so
ENV GEOS_LIBRARY_PATH=/usr/lib/aarch64-linux-gnu/libgeos_c.so

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && \
    uv export --frozen --no-dev --no-hashes -o requirements.txt && \
    pip install --no-cache-dir -r requirements.txt && \
    rm requirements.txt

RUN useradd --uid 10001 --gid 0 --no-create-home --home-dir /app \
        --shell /usr/sbin/nologin pilgrimage && \
    mkdir -p /app/staticfiles && \
    chown -R 10001:0 /app

COPY --chown=10001:0 . .

USER 10001:0

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
