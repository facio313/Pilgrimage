import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { BonifacioReturnLink, PortfolioShell } from './PortfolioShell';

describe('PortfolioShell', () => {
  it('does not add a global navigation banner', () => {
    render(
      <PortfolioShell>
        <main>현재 화면</main>
      </PortfolioShell>,
    );

    expect(screen.getByText('현재 화면')).toBeTruthy();
    expect(screen.queryByRole('banner')).toBeNull();
    expect(screen.queryByRole('link', { name: 'Bonifacio로 돌아가기' })).toBeNull();
  });

  it('provides a same-tab Bonifacio return link for map surfaces', () => {
    render(<BonifacioReturnLink />);

    const link = screen.getByRole('link', { name: 'Bonifacio로 돌아가기' });
    expect(link.getAttribute('href')).toBe('https://bonifacio.work/');
    expect(link.hasAttribute('target')).toBe(false);
  });
});
