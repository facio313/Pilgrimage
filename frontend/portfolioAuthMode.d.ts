export type PortfolioEnvironment = Record<string, string | undefined>

export function resolveFrontendAuthMode(
  environment?: PortfolioEnvironment,
  resolverAvailable?: boolean,
): Readonly<{ mode: 'sso' | 'local'; ssoEnabled: boolean }>
