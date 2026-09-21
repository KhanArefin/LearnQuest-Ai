/** API calls. OWNER: Member 1. All requests go through the shared client. */
import client from './client';

/** The student's active roadmap, or { roadmap: null } if they have none. */
export const myRoadmap = () => client.get('/api/roadmap/me');

/** Plan a new roadmap for a goal. Archives any previous active one. */
export const generateRoadmap = (goal, horizonWeeks = 8) =>
  client.post('/api/roadmap/generate', { goal, horizon_weeks: horizonWeeks });

/** Mark a quest complete and award its XP. Idempotent. */
export const completeNode = (nodeId) =>
  client.post(`/api/roadmap/nodes/${nodeId}/complete`);

/** Redraw the road ahead against updated mastery. Completed quests are kept. */
export const replanRoadmap = () => client.post('/api/roadmap/replan');
