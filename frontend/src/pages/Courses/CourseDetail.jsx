/**
 * CourseDetail - OWNER: Member 2. See plan.md §7.2.
 *
 * Course detail page displaying course metadata, ordered lesson list,
 * enrollment status check, and active enrollment action.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { enroll, getCourse, myEnrollments } from '../../api/courses';
import { useAuth } from '../../context/AuthContext';
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Spinner,
} from '../../components/ui';

function getDifficultyTone(difficulty) {
  switch (difficulty?.toLowerCase()) {
    case 'beginner':
      return 'success';
    case 'intermediate':
      return 'warning';
    case 'advanced':
      return 'danger';
    default:
      return 'default';
  }
}

export default function CourseDetail() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();

  const [course, setCourse] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Enrollment state
  const [isEnrolled, setIsEnrolled] = useState(false);
  const [enrolling, setEnrolling] = useState(false);
  const [enrollError, setEnrollError] = useState(null);
  const [enrollSuccess, setEnrollSuccess] = useState(false);

  // Fetch course details & current enrollment status strictly for the active user
  const loadData = useCallback(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);
    setEnrollError(null);

    const enrollmentPromise =
      isAuthenticated && user
        ? myEnrollments()
        : Promise.resolve({ items: [] });

    Promise.allSettled([getCourse(slug), enrollmentPromise])
      .then(([courseRes, enrollmentsRes]) => {
        if (!isMounted) return;

        if (courseRes.status === 'fulfilled') {
          const courseData = courseRes.value;
          setCourse(courseData);

          // Check if user is enrolled
          if (isAuthenticated && user && enrollmentsRes.status === 'fulfilled') {
            const enrollmentsData = enrollmentsRes.value;
            const items = Array.isArray(enrollmentsData)
              ? enrollmentsData
              : enrollmentsData?.items || [];
            const enrolled = items.some(
              (e) => e.course_id === courseData.id || e.course?.id === courseData.id
            );
            setIsEnrolled(enrolled);
          } else {
            setIsEnrolled(false);
          }
        } else {
          const detail =
            courseRes.reason?.detail || `Course '${slug}' could not be found.`;
          setError(detail);
        }
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [slug, isAuthenticated, user?.id]);

  useEffect(() => {
    const cancel = loadData();
    return cancel;
  }, [loadData]);

  const handleEnroll = async () => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }

    if (!course?.id || isEnrolled || enrolling) return;

    setEnrolling(true);
    setEnrollError(null);

    try {
      await enroll(course.id);
      setIsEnrolled(true);
      setEnrollSuccess(true);
    } catch (err) {
      console.error('Enrollment failed:', err);
      setEnrollError(
        err?.detail || 'Failed to complete enrollment. Please try again.'
      );
    } finally {
      setEnrolling(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[350px] items-center justify-center">
        <Spinner size="lg" label="Loading course details..." />
      </div>
    );
  }

  if (error || !course) {
    return (
      <div className="py-6">
        <Link
          to="/courses"
          className="mb-6 inline-flex items-center text-sm font-medium text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
        >
          ← Back to Courses
        </Link>
        <EmptyState
          title="Course Not Found"
          description={error || "We couldn't locate the course you requested."}
          action={
            <div className="flex gap-3">
              <Button variant="secondary" size="sm" onClick={() => navigate('/courses')}>
                Browse Courses
              </Button>
              <Button variant="primary" size="sm" onClick={loadData}>
                Try Again
              </Button>
            </div>
          }
        />
      </div>
    );
  }

  const lessons = [...(course.lessons || [])].sort(
    (a, b) => (a.order_index ?? 0) - (b.order_index ?? 0)
  );

  const firstLessonId = lessons[0]?.id;

  return (
    <div className="space-y-8 pb-12">
      {/* Breadcrumb / Back Link */}
      <div>
        <Link
          to="/courses"
          className="inline-flex items-center text-sm font-medium text-slate-500 transition-colors hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
        >
          ← Back to Courses
        </Link>
      </div>

      {/* Course Hero Banner */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900/60 sm:p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="default">{course.subject || 'General'}</Badge>
              <Badge tone={getDifficultyTone(course.difficulty)}>
                {course.difficulty || 'beginner'}
              </Badge>
              {isEnrolled && <Badge tone="success">Enrolled</Badge>}
            </div>

            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-50 sm:text-3xl">
              {course.title}
            </h1>

            <p className="text-base text-slate-600 dark:text-slate-300 sm:text-lg">
              {course.description || 'No description provided for this course.'}
            </p>

            {/* Metadata Badges */}
            <div className="flex flex-wrap items-center gap-4 text-xs font-medium text-slate-500 dark:text-slate-400">
              <div className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-slate-400 dark:bg-slate-500" />
                <span>{course.estimated_hours ? `${course.estimated_hours} Hours` : 'Self-paced'}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-slate-400 dark:bg-slate-500" />
                <span>{lessons.length} {lessons.length === 1 ? 'Lesson' : 'Lessons'}</span>
              </div>
              {course.source && (
                <div className="flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-slate-400 dark:bg-slate-500" />
                  <span className="capitalize">{course.source} Course</span>
                </div>
              )}
            </div>
          </div>

          {/* Action / Enrollment Box */}
          <div className="flex w-full flex-col gap-3 rounded-xl border border-slate-100 bg-slate-50/80 p-5 dark:border-slate-800 dark:bg-slate-800/40 lg:w-72 lg:shrink-0">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              {isEnrolled ? 'Enrollment Status' : 'Start Learning'}
            </h3>

            {isEnrolled ? (
              <div className="space-y-3">
                <div className="rounded-lg bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300">
                  ✓ You are enrolled in this course
                </div>
                {firstLessonId ? (
                  <Link to={`/lessons/${firstLessonId}`} className="block w-full">
                    <Button variant="primary" className="w-full">
                      Start Lesson 1 →
                    </Button>
                  </Link>
                ) : (
                  <Button variant="secondary" disabled className="w-full">
                    No lessons yet
                  </Button>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                <Button
                  variant="primary"
                  loading={enrolling}
                  onClick={handleEnroll}
                  className="w-full"
                >
                  Enroll in Course
                </Button>
                <p className="text-center text-xs text-slate-500 dark:text-slate-400">
                  Free access • Self-paced learning
                </p>
              </div>
            )}

            {enrollSuccess && (
              <div className="animate-fade-in rounded-lg bg-emerald-50 p-2.5 text-xs text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
                🎉 Successfully enrolled! You can now access all lessons below.
              </div>
            )}

            {enrollError && (
              <div className="animate-fade-in rounded-lg bg-rose-50 p-2.5 text-xs text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
                {enrollError}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Lesson Curriculum / Outline */}
      <div className="space-y-4">
        <div className="flex items-end justify-between">
          <div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">
              Course Syllabus
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Complete each lesson and practice with the AI avatar tutor.
            </p>
          </div>
          <span className="text-sm font-medium text-slate-500">
            {lessons.length} {lessons.length === 1 ? 'lesson' : 'lessons'}
          </span>
        </div>

        {lessons.length === 0 ? (
          <EmptyState
            title="No lessons published yet"
            description="The instructor has not added any lessons to this course yet. Check back soon!"
          />
        ) : (
          <div className="space-y-3">
            {lessons.map((lesson, idx) => {
              const lessonNumber = lesson.order_index ?? idx + 1;
              const topicTags = Array.isArray(lesson.topic_tags) ? lesson.topic_tags : [];

              return (
                <Card
                  key={lesson.id}
                  className="flex flex-col gap-4 transition-all hover:border-slate-300 dark:hover:border-slate-700 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="flex items-start gap-3.5">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary-50 font-semibold text-primary-700 dark:bg-primary-950 dark:text-primary-300 text-sm">
                      {lessonNumber}
                    </span>
                    <div className="space-y-1">
                      <h3 className="font-semibold text-slate-900 dark:text-slate-100">
                        {lesson.title}
                      </h3>
                      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                        <span>
                          {lesson.estimated_minutes
                            ? `~${lesson.estimated_minutes} min`
                            : '10 min'}
                        </span>
                        {topicTags.length > 0 && (
                          <>
                            <span>•</span>
                            <div className="flex flex-wrap gap-1">
                              {topicTags.map((tag) => (
                                <Badge key={tag} tone="default" className="text-[10px] py-0 px-1.5">
                                  {tag}
                                </Badge>
                              ))}
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex shrink-0 items-center justify-end">
                    <Link to={`/lessons/${lesson.id}`}>
                      <Button variant="secondary" size="sm">
                        View Lesson →
                      </Button>
                    </Link>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
