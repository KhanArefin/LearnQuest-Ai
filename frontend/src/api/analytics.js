/** API calls. OWNER: Member 4. All requests go through the shared client. */
import client from './client';

// ⚠️ These three are STUBS in `backend/app/routers/analytics.py` — they return
// zeros and empty lists, and will keep doing so until M4 implements them
// (Slot 12). They are not broken; they were never built. Do not spend an
// afternoon wondering why a chart is empty.
export const mySummary = () => client.get('/api/analytics/me/summary');
export const myActivity = (days = 56) =>
  client.get('/api/analytics/me/activity', { params: { days } });
export const adminOverview = () => client.get('/api/analytics/admin/overview');

/**
 * Mastery per topic, weakest first.
 *
 * Re-pointed 2026-09-28 from `/api/analytics/mastery/me` to M1's `/api/mastery/me`.
 * The analytics one is a stub that returns `{items: []}`, so anything built on
 * it looked like a student with no history rather than a missing endpoint.
 *
 * For the misconception map use `myMisconceptions` from `api/mastery.js`.
 */
export { myMastery, myMisconceptions } from './mastery';
