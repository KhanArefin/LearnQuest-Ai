/**
 * Spaced-Repetition Review Queue API.
 * OWNER: Member 1 (AI / Scheduler backend) consumed by Member 2 (UI).
 *
 * Contract (plan.md §6.12):
 * - GET  /api/review/today             -> list of review items due today (interleaved topics)
 * - POST /api/review/{item_id}/answer  -> grade, reschedule, update mastery & misconception
 *
 * Note: If backend /api/review endpoints are pending, DEV_FALLBACK_REVIEWS serves
 * as an isolated, removable client fallback for development.
 */

import client from './client';

// ============================================================================
// ISOLATED DEV FALLBACK DATA (Removable once M1 review router lands)
// ============================================================================
const DEV_FALLBACK_REVIEWS = [
  {
    id: 'rev-01',
    topic_tag: 'dbms.sql_joins',
    topic_name: 'SQL Joins & Grouping',
    type: 'mcq',
    prompt: 'Which join type returns all rows from the left table, and matching rows from the right table, filling with NULL when no match exists?',
    options: ['INNER JOIN', 'LEFT OUTER JOIN', 'FULL OUTER JOIN', 'CROSS JOIN'],
    due_at: new Date().toISOString(),
  },
  {
    id: 'rev-02',
    topic_tag: 'dbms.relational_algebra',
    topic_name: 'Relational Algebra',
    type: 'true_false',
    prompt: 'The projection operator (π) in classical relational algebra permits duplicate rows in the final result relation.',
    options: ['True', 'False'],
    due_at: new Date().toISOString(),
  },
  {
    id: 'rev-03',
    topic_tag: 'dbms.indexing',
    topic_name: 'Indexing & Query Plans',
    type: 'short_answer',
    prompt: 'Why does placing a low-cardinality boolean column first in a composite B-Tree index often degrade range scan efficiency on subsequent columns?',
    options: null,
    due_at: new Date().toISOString(),
  },
  {
    id: 'rev-04',
    topic_tag: 'dbms.er_model',
    topic_name: 'ER Models & Keys',
    type: 'short_answer',
    prompt: 'In your own words, what distinguishes a superkey from a candidate key in relational schema design?',
    options: null,
    due_at: new Date().toISOString(),
  },
];

// ============================================================================
// API METHODS
// ============================================================================

export const getTodayReview = async () => {
  try {
    const res = await client.get('/api/review/today');
    return res?.data || res;
  } catch (err) {
    if (err?.response?.status === 404 || err?.status === 404 || err?.code === 'ERR_BAD_RESPONSE') {
      return {
        items: DEV_FALLBACK_REVIEWS,
        total_due: DEV_FALLBACK_REVIEWS.length,
      };
    }
    throw err;
  }
};

export const submitReviewAnswer = async (itemId, { answer }) => {
  try {
    const res = await client.post(`/api/review/${itemId}/answer`, { answer });
    return res?.data || res;
  } catch (err) {
    if (err?.response?.status === 404 || err?.status === 404) {
      // Contract-compatible simulated grading for development
      const isBlank = !answer || String(answer).trim().length === 0;
      const isCorrect = !isBlank && String(answer).trim().length > 3;

      return {
        item_id: itemId,
        is_correct: isCorrect,
        score_0_1: isCorrect ? 1.0 : 0.0,
        feedback: isCorrect
          ? 'Clear and conceptually accurate answer. Demonstrated solid understanding of the underlying principle.'
          : 'The answer missed key relational criteria. Review the formal definition and re-check how nulls and candidate keys interact.',
        misconception: isCorrect
          ? null
          : 'Equating superkeys directly with candidate keys without verifying minimal irreducibility.',
        next_due_at: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString(),
      };
    }
    throw err;
  }
};
