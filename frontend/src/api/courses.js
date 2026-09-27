/** API calls. OWNER: Member 2. All requests go through the shared client. */
import client from './client';

export const listCourses = (params) => client.get('/api/courses', { params });
export const getCourse = (slug) => client.get(`/api/courses/${slug}`);
export const enroll = (courseId) => client.post(`/api/courses/${courseId}/enroll`);
export const myEnrollments = () => client.get('/api/me/enrollments');
export const myProgress = () => client.get('/api/me/progress');
export const myHistory = (params) => client.get('/api/me/history', { params });

/**
 * Generate a private course for this student from a goal. (M1)
 *
 * ⚠️ Returns **202 with a job id, not a course**:
 *   {job_id, status: "queued", poll: "/api/jobs/<id>"}
 *
 * Generation is an outline call plus one per lesson — measured at 24.5s for
 * three lessons, well past this client's 30s timeout. Poll `GET /api/jobs/{id}`
 * until `status` is "succeeded", then `result` carries
 * {course_id, slug, title, lessons, topics} and the student is already
 * enrolled, so route straight to `/courses/{slug}`.
 *
 * `useGenerationJob` in hooks/ does the polling for you.
 *
 * Throws 429 when the daily generation allowance is spent.
 */
export const generateCourse = (goal, nLessons = 4) =>
  client.post('/api/courses/generate', { goal, n_lessons: nLessons });
