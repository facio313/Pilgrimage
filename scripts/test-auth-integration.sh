#!/bin/sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

python3 - "$repository_root" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
backend_dockerfile = (root / "backend" / "Dockerfile").read_text(encoding="utf-8")
dockerfile = (root / "frontend" / "Dockerfile").read_text(encoding="utf-8")
entrypoint = (root / "scripts" / "portfolio-auth-entrypoint.sh").read_text(encoding="utf-8")
urls = (root / "backend" / "config" / "urls.py").read_text(encoding="utf-8")
package = json.loads((root / "frontend" / "package.json").read_text(encoding="utf-8"))
workflow = (root / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
dockerignore = (root / ".dockerignore").read_text(encoding="utf-8")
nginx = (root / "frontend" / "nginx.conf").read_text(encoding="utf-8")


def require(condition, message):
    if not condition:
        raise SystemExit(f"FAIL: {message}")


for command in ("dev", "preview"):
    value = package["scripts"][command]
    require("PORTFOLIO_AUTH_MODE=local" in value, f"{command} is not local-only")
    require("../scripts/portfolio-auth-mode.sh exec --" in value, f"{command} bypasses the resolver")

require("branches: [main, dev]" in workflow, "main/dev workflow trigger is missing")
require(workflow.count("push: ${{ github.ref_name == 'main' }}") == 2, "dev image build could push")
require("if: github.ref_name == 'main'" in workflow, "production mutation is not main-only")
require("pilgrimageBackend:\n    image:" in compose, "backend service image contract changed")
require("context: ./backend" in compose, "local backend build context is missing")
require("dockerfile: frontend/Dockerfile" in compose, "frontend does not use the guarded root context")
require("file: ./frontend/Dockerfile" in workflow, "CI frontend Dockerfile is not explicit")
require("**" in dockerignore and "!frontend/**" in dockerignore, "root frontend context is not allowlisted")
require("!scripts/portfolio-auth-mode.sh" in dockerignore, "root context omits the canonical resolver")
require(compose.count("PORTFOLIO_BRANCH: ${PORTFOLIO_BRANCH:?") >= 3, "branch is not injected into builds/runtime")
require("org.opencontainers.image.ref.name" in dockerfile, "frontend branch audit label is missing")
require("io.bonifacio.portfolio.auth-mode" in dockerfile, "frontend auth-mode audit label is missing")
for name, content in (("backend", backend_dockerfile), ("frontend", dockerfile)):
    require(
        '${PORTFOLIO_BRANCH#refs/heads/}' in content,
        f"{name} Docker build does not normalize refs/heads branches",
    )
    require(
        "/etc/portfolio-auth-build" in content and "chmod 0444" in content,
        f"{name} image lacks an immutable auth build contract",
    )
require(
    'ENTRYPOINT ["/usr/local/bin/portfolio-auth-entrypoint.sh"]' in dockerfile,
    "frontend does not verify auth mode at container startup",
)
require("portfolio-auth-mode.sh contract" in entrypoint, "frontend entrypoint bypasses the resolver")
require("if not settings.PILGRIMAGE_SSO_ENABLED" in urls, "SSO mode still registers Django admin")
require(
    "proxy_set_header Remote-Groups $http_remote_groups;" in nginx,
    "protected proxy does not forward central role groups",
)
require(
    "proxy_set_header X-Portfolio-Edge-Secret $http_x_portfolio_edge_secret;" in nginx,
    "protected proxy does not forward the per-app edge credential",
)

print("pilgrimage auth integration contract: ok")
PY
