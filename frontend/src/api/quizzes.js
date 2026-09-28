/** API calls. OWNER: Member 2 (attempts) + Member 1 (generation). All requests go through the shared client. */
import client from './client';

// --- taking quizzes (M2) ---
export const getQuiz = (quizId) => client.get(`/api/quizzes/${quizId}`);
export const getQuizByLesson = (lessonId) => client.get(`/api/quizzes/lesson/${lessonId}`);
export const startAttempt = (quizId) => client.post(`/api/quizzes/${quizId}/attempts`);
export const submitAttempt = (attemptId, answers) =>
  client.post(`/api/quizzes/attempts/${attemptId}/submit`, { answers });
export const getAttempt = (attemptId) => client.get(`/api/quizzes/attempts/${attemptId}`);

// --- AI generation (M1) ---
export const generateQuiz = (bodyOrLessonId) =>
  client.post(
    '/api/quizzes/generate',
    typeof bodyOrLessonId === 'string' ? { lesson_id: bodyOrLessonId } : bodyOrLessonId
  );
export const generateAdaptiveQuiz = (body = {}) => client.post('/api/quizzes/generate/adaptive', body);

// --- free-response grading (M1 endpoint) ---
export const gradeOpenAnswer = (attemptId, payload) =>
  client.post(`/api/quizzes/attempts/${attemptId}/grade-open`, payload);

