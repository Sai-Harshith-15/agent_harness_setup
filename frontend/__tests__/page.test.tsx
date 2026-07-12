import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import Home from '../app/page';

// Mock fetch for the async Server Component
global.fetch = vi.fn((url) => {
  if (typeof url === 'string' && url.includes('/health')) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ status: 'ok', obsidian_backend: true }),
    });
  }
  if (typeof url === 'string' && url.includes('/dashboard/state')) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ locks: [], recent_activity: [] }),
    });
  }
  return Promise.reject(new Error('not found'));
}) as any;

describe('Mission Control Home', () => {
  it('renders without crashing and shows health status', async () => {
    // Since it's a Server Component doing async fetch, we need to await the component
    const PageComponent = await Home();
    render(PageComponent);
    
    expect(screen.getByText('Agentic OS — Mission Control')).toBeDefined();
    expect(screen.getAllByText(/ok/i)[0]).toBeDefined();
    expect(screen.getByText(/Obsidian backend: reachable/i)).toBeDefined();
  });
});
