import { describe, expect, it } from 'vitest'
import { resolveFrontendAuthMode } from '../portfolioAuthMode.js'

describe('portfolio auth mode', () => {
  it.each(['main', 'dev', 'refs/heads/main', 'refs/heads/dev'])(
    'enables SSO for %s',
    (branch) => {
      expect(resolveFrontendAuthMode({
        PORTFOLIO_BRANCH: branch,
        PORTFOLIO_AUTH_MODE: 'sso',
        VITE_SSO_ENABLED: 'true',
      }).ssoEnabled).toBe(true)
    },
  )

  it('keeps a feature branch on local auth', () => {
    expect(resolveFrontendAuthMode({
      PORTFOLIO_BRANCH: 'codex/auth-contract',
      PORTFOLIO_AUTH_MODE: 'local',
      VITE_SSO_ENABLED: 'false',
    })).toEqual({ mode: 'local', ssoEnabled: false })
  })

  it('rejects canonical and legacy mismatches', () => {
    expect(() => resolveFrontendAuthMode({
      PORTFOLIO_BRANCH: 'main',
      PORTFOLIO_AUTH_MODE: 'local',
    })).toThrow()
    expect(() => resolveFrontendAuthMode({
      PORTFOLIO_BRANCH: 'main',
      PORTFOLIO_AUTH_MODE: 'sso',
      VITE_SSO_ENABLED: 'false',
    })).toThrow(/VITE_SSO_ENABLED/)
  })

  it('requires both canonical values in a packaged build', () => {
    expect(() => resolveFrontendAuthMode({}, false)).toThrow(/PORTFOLIO_BRANCH/)
    expect(() => resolveFrontendAuthMode({
      PORTFOLIO_BRANCH: 'main',
    }, false)).toThrow(/PORTFOLIO_AUTH_MODE/)
  })
})
