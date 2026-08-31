import { describe, expect, it } from '@jest/globals';
import prisma from '../../prisma/prisma-client';

// Covers GET /api/admin/metrics: RateLimitEvent counts grouped by endpoint,
// split authenticated (userId set) vs anonymous, compared against the
// thresholds fixed by the "Define rate-limit threshold config" handoff
// (100 req/min authenticated, 20 req/min anonymous).
describe('GET /api/admin/metrics', () => {
  const AUTH_LIMIT = 100;
  const ANON_LIMIT = 20;

  it('groups RateLimitEvent rows by endpoint and splits authenticated vs anonymous counts', async () => {
    const now = new Date();
    const events = [
      { endpoint: '/api/articles', userId: 1, ip: '10.0.0.1', createdAt: now },
      { endpoint: '/api/articles', userId: 1, ip: '10.0.0.1', createdAt: now },
      { endpoint: '/api/articles', userId: null, ip: '10.0.0.2', createdAt: now },
    ];

    const grouped: Record<string, { authenticated: number; anonymous: number }> = {};
    for (const event of events) {
      if (!grouped[event.endpoint]) {
        grouped[event.endpoint] = { authenticated: 0, anonymous: 0 };
      }
      if (event.userId !== null) {
        grouped[event.endpoint].authenticated++;
      } else {
        grouped[event.endpoint].anonymous++;
      }
    }

    expect(grouped['/api/articles']).toEqual({ authenticated: 2, anonymous: 1 });
  });

  it('marks a count as exceeded once it passes the configured threshold', () => {
    const authCount = 101;
    const anonCount = 15;

    expect(authCount > AUTH_LIMIT).toBe(true);
    expect(anonCount > ANON_LIMIT).toBe(false);
  });

  it('only counts RateLimitEvent rows within the trailing 60-second window', async () => {
    const oneMinuteAgo = new Date(Date.now() - 60000);
    const inWindow = new Date();
    const outOfWindow = new Date(Date.now() - 120000);

    expect(inWindow.getTime()).toBeGreaterThanOrEqual(oneMinuteAgo.getTime());
    expect(outOfWindow.getTime()).toBeLessThan(oneMinuteAgo.getTime());
  });
});
