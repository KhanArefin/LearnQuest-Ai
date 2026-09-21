import PageHeader from '../../components/layout/PageHeader';
import { EmptyState } from '../../components/ui';

export default function AdminCourses() {
  return (
    <div>
      <PageHeader title="Courses" subtitle="Create, edit and publish courses." />
      <EmptyState title="No courses yet" description="Courses you create will be listed here." />
    </div>
  );
}
