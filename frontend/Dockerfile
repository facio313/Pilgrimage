FROM node:22-slim AS build

WORKDIR /app
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
    PORTFOLIO_AUTH_MODE=${PORTFOLIO_AUTH_MODE}
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .
COPY scripts/portfolio-auth-mode.sh /scripts/portfolio-auth-mode.sh
ARG VITE_SSO_ENABLED
ENV VITE_SSO_ENABLED=$VITE_SSO_ENABLED
RUN npm run build

FROM nginx:stable-alpine
ARG PORTFOLIO_BRANCH
ARG PORTFOLIO_AUTH_MODE
ENV PORTFOLIO_BRANCH=${PORTFOLIO_BRANCH} \
    PORTFOLIO_AUTH_MODE=${PORTFOLIO_AUTH_MODE}
LABEL org.opencontainers.image.ref.name="${PORTFOLIO_BRANCH}" \
      io.bonifacio.portfolio.auth-mode="${PORTFOLIO_AUTH_MODE}"
RUN normalized_branch="${PORTFOLIO_BRANCH#refs/heads/}" \
    && printf '%s\n%s\n' "$normalized_branch" "$PORTFOLIO_AUTH_MODE" \
         > /etc/portfolio-auth-build \
    && chmod 0444 /etc/portfolio-auth-build
COPY scripts/portfolio-auth-mode.sh /usr/local/bin/portfolio-auth-mode.sh
COPY scripts/portfolio-auth-entrypoint.sh /usr/local/bin/portfolio-auth-entrypoint.sh
RUN chmod 0555 /usr/local/bin/portfolio-auth-mode.sh \
    /usr/local/bin/portfolio-auth-entrypoint.sh
COPY --from=build /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
ENTRYPOINT ["/usr/local/bin/portfolio-auth-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
