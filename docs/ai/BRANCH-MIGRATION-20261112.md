# Main/dev migration — 2026-11-12

The user replaced tool/feature and retired-dev rules with two active branches: `main` is production and `dev` is development. Fetch `origin/main` before changes, validate on `dev`, and publish/deploy only reviewed main history. Local apps run only from the actual dev checkout through `scripts/dev-only.sh`; setting PORTFOLIO_BRANCH cannot bypass this checkout guard. The canonical resolver permits only main/sso and dev/local.

Pre-migration refs were saved in a verified Git bundle under `~/.local/share/cks-main-dev-migration/2026-11-12/Pilgrimage/before-migration.bundle`. Original dirty/untracked/ignored files and worktrees are preserved. Existing branches are not deleted in this change. CI on dev must not publish or deploy production artifacts.

Both cursor and recovered local codex histories had no tree difference from their merge base and are merged without application changes. The previously missing local codex object 2983063 was recovered from origin by SHA and included in the verified bundle.

Validation completed:

- 8 backend auth tests and 8 subtests passed
- 7 frontend auth tests passed
- ruff changed Python files passed
- auth integration contract and shell guard passed
- workflow YAML parsed
