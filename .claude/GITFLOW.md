# Pilgrimage — Claude Gitflow Guide

> Claude (Anthropic) 에이전트 전용 브랜치 운영 규칙.

---

## 브랜치 구조

```
main                       ← 배포 기준 (직접 커밋 금지)
└── dev                    ← 통합 브랜치 (PR 경유 병합)
    ├── anthropic/main     ← Claude 상주 브랜치 ✅ (현재)
    │   └── anthropic/<feature>
    ├── cursor/main        ← Cursor 에이전트 (수정 금지)
    └── codex/main         ← Codex 에이전트 (수정 금지)
```

---

## Claude 작업 규칙

| 항목 | 규칙 |
|------|------|
| 상주 브랜치 | `anthropic/main` |
| 기능 브랜치 생성 | `git checkout -b anthropic/<feature-name>` |
| 네이밍 예시 | `anthropic/gps-cert`, `anthropic/spot-detail-ui` |
| 병합 방향 | `anthropic/<feature>` → `anthropic/main` → `dev` → `main` |
| `main` / `dev` 직접 커밋 | **금지** |
| `cursor/*` / `codex/*` 브랜치 | **수정 금지** (읽기만 허용) |

---

## 체크아웃 확인

작업 시작 전 반드시 현재 브랜치 확인:

```bash
git branch --show-current
# 출력이 anthropic/main 또는 anthropic/<feature> 이어야 함
```

---

## PR 흐름

1. `anthropic/<feature>` 브랜치에서 작업
2. `anthropic/main`으로 PR (또는 직접 병합)
3. `anthropic/main` → `dev` PR (사용자 확인 후)
4. `dev` → `main` PR (최종 배포 시)
