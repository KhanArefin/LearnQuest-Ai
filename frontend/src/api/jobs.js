/**
 * Background generation jobs. OWNER: Member 1.
 *
 * Anything too slow for a request returns a job id instead of a result.
 * Course generation is the one that matters: measured at 24.5s for three
 * lessons, against this client's 30s timeout.
 *
 * You usually want `useGenerationJob` in `hooks/` rather than these directly —
 * it does the polling and the cleanup for you.
 */
import client from './client';

/** {id, kind, status, progress, result, error, created_at, finished_at} */
export const getJob = (jobId) => client.get(`/api/jobs/${jobId}`);

/** This user's recent generations, newest first. */
export const myJobs = (limit = 20) => client.get('/api/jobs', { params: { limit } });

/**
 * {used, limit, remaining} — how many generations are left today.
 *
 * Ask before showing a generate button, so the student finds out up front
 * rather than after waiting for a 429.
 */
export const myQuota = () => client.get('/api/jobs/quota');
