import type { ReactNode } from 'react';

interface PortfolioShellProps {
  children: ReactNode;
}

export function PortfolioShell({ children }: PortfolioShellProps) {
  return (
    <div className="pilgrimage-app-shell">
      <div className="pilgrimage-app-content">{children}</div>
    </div>
  );
}

export function BonifacioReturnLink() {
  return (
    <a
      className="bonifacio-return-link"
      href="https://bonifacio.work/"
      aria-label="Bonifacio로 돌아가기"
    >
      <span aria-hidden="true">←</span>
      <span>Bonifacio</span>
    </a>
  );
}
