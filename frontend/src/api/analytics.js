/** API calls. OWNER: Member 4. All requests go through the shared client. */
import client from './client';

export const mySummary = () => client.get('/api/analytics/me/summary');
export const myActivity = (days = 56) =>
  client.get('/api/analytics/me/activity', { params: { days } });
export const myReviewQueue = () => client.get('/api/analytics/me/review');
export const adminOverview = () => client.get('/api/analytics/admin/overview');

/**
 * Mastery per topic, weakest first.
 * Re-exports M1's /api/mastery/me and /api/mastery/me/misconceptions.
 */
export { myMastery, myMisconceptions } from './mastery';
