/**
 * Topic mastery and misconceptions. OWNER: Member 1.
 *
 * ⚠️ Use THESE, not the `myMastery` in `analytics.js`. That one calls
 * `/api/analytics/mastery/me`, which is still a stub returning `{items: []}` —
 * it will look like the student simply has no data.
 */
import client from './client';

/**
 * Every false belief recorded for this student, with its decay status.
 *
 * {items: [{topic_tag, misconception, status, mastery_score, correct_streak,
 *           captured_at, cleared_at}], total, counts}
 *
 * `status` is 'active' (named, no correct answers since), 'fading' (at least
 * one correct answer since) or 'cleared' (overcome). The text is kept after
 * clearing on purpose: the map should show what a student has beaten, not only
 * what they still get wrong.
 */
export const myMisconceptions = (includeCleared = true) =>
  client.get('/api/mastery/me/misconceptions', {
    params: { include_cleared: includeCleared },
  });

/**
 * Mastery score per topic, weakest first.
 *
 * {items: [{topic_tag, mastery_score, attempts, correct, has_misconception,
 *           last_practiced_at}], total}
 */
export const myMastery = () => client.get('/api/mastery/me');
