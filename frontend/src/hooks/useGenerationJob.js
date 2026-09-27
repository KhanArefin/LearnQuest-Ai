/**
 * Poll a background generation job. OWNER: Member 1.
 *
 * Course generation returns a job id rather than a course, because it takes
 * around 25s for three lessons against this client's 30s timeout. This hook is
 * the whole client side of that: start it, watch `progress`, read `result`.
 *
 *   const job = useGenerationJob();
 *
 *   await job.start(() => generateCourse(goal));
 *
 *   job.status    'idle' | 'running' | 'succeeded' | 'failed'
 *   job.progress  0-100
 *   job.result    the payload, once succeeded
 *   job.error     a sentence written for the student, once failed
 *
 * Three things here are easy to get wrong and annoying to debug:
 *
 *   - polling keeps running after the component unmounts, so a student who
 *     navigates away leaves a timer hitting the API forever;
 *   - a second generation started while the first is in flight leaves two
 *     pollers writing to the same state, and whichever finishes last wins;
 *   - a failed poll aborts the whole thing, when one dropped request during a
 *     25s job is nothing to worry about.
 *
 * All three are handled below.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

import { getJob } from '../api/jobs';

const POLL_MS = 2000;

/** Long enough for a six-lesson course, short enough to not hang forever. */
const MAX_POLL_MS = 5 * 60 * 1000;

/** One dropped poll mid-job is normal; several in a row is not. */
const MAX_CONSECUTIVE_POLL_FAILURES = 4;

export default function useGenerationJob() {
  const [status, setStatus] = useState('idle');
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [jobId, setJobId] = useState(null);

  const timerRef = useRef(null);
  const mountedRef = useRef(true);
  // Bumped on every start, so a poller from a previous run can tell it is stale
  // and stop writing state.
  const runRef = useRef(0);

  const clearTimer = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = null;
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      clearTimer();
    };
  }, [clearTimer]);

  const poll = useCallback(
    (id, run, startedAt, failures = 0) => {
      timerRef.current = setTimeout(async () => {
        if (!mountedRef.current || run !== runRef.current) return;

        if (Date.now() - startedAt > MAX_POLL_MS) {
          setStatus('failed');
          setError('This is taking longer than expected. Check back shortly.');
          return;
        }

        try {
          const job = await getJob(id);
          if (!mountedRef.current || run !== runRef.current) return;

          setProgress(job.progress ?? 0);

          if (job.status === 'succeeded') {
            setResult(job.result ?? null);
            setProgress(100);
            setStatus('succeeded');
            return;
          }
          if (job.status === 'failed') {
            // The backend writes this for a student to read, so show it as-is.
            setError(job.error || 'Generation failed. Try again.');
            setStatus('failed');
            return;
          }
          poll(id, run, startedAt, 0);
        } catch {
          if (!mountedRef.current || run !== runRef.current) return;
          if (failures + 1 >= MAX_CONSECUTIVE_POLL_FAILURES) {
            setStatus('failed');
            setError('Lost contact while generating. Try again.');
            return;
          }
          poll(id, run, startedAt, failures + 1);
        }
      }, POLL_MS);
    },
    [],
  );

  /**
   * Kick off a job. `request` is any call returning {job_id} — normally
   * `() => generateCourse(goal)`.
   *
   * Resolves with the job id, or null if it could not be started.
   */
  const start = useCallback(
    async (request) => {
      clearTimer();
      const run = (runRef.current += 1);

      setStatus('running');
      setProgress(0);
      setResult(null);
      setError(null);
      setJobId(null);

      try {
        const response = await request();
        if (!mountedRef.current || run !== runRef.current) return null;

        const id = response?.job_id;
        if (!id) {
          setStatus('failed');
          setError('Could not start generating. Try again.');
          return null;
        }

        setJobId(id);
        poll(id, run, Date.now());
        return id;
      } catch (err) {
        if (!mountedRef.current || run !== runRef.current) return null;
        // 429 carries the real "you have used today's generations" message.
        setStatus('failed');
        setError(err?.detail || 'Could not start generating. Try again.');
        return null;
      }
    },
    [clearTimer, poll],
  );

  /** Stop watching. Does not cancel the work, which finishes server-side. */
  const reset = useCallback(() => {
    clearTimer();
    runRef.current += 1;
    setStatus('idle');
    setProgress(0);
    setResult(null);
    setError(null);
    setJobId(null);
  }, [clearTimer]);

  return {
    start,
    reset,
    jobId,
    status,
    progress,
    result,
    error,
    isRunning: status === 'running',
  };
}
