import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { PortfolioShell } from './PortfolioShell';

describe('PortfolioShell', () => {
  it('keeps the Bonifacio return link on the shared app shell', () => {
    render(
      <PortfolioShell>
        <main>현재 화면</main>
      </PortfolioShell>,
    );

    const link = screen.getByRole('link', { name: '← Bonifacio' });
    expect(link.getAttribute('href')).toBe('https://bonifacio.work/');
    expect(link.hasAttribute('target')).toBe(false);
  });
});
