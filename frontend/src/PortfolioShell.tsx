import type { ReactNode } from 'react';

interface PortfolioShellProps {
  children: ReactNode;
}

export function PortfolioShell({ children }: PortfolioShellProps) {
  return (
    <div className="pilgrimage-app-shell">
      <header className="portfolio-return-header">
        <a className="bonifacio-return-link" href="https://bonifacio.work/">
          ← Bonifacio
        </a>
      </header>
      <div className="pilgrimage-app-content">{children}</div>
    </div>
  );
}
