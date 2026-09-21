import PageHeader from '../../components/layout/PageHeader';
import { EmptyState } from '../../components/ui';

export default function History() {
  return (
    <div>
      <PageHeader title="History" subtitle="Everything you have worked through, most recent first." />
      <EmptyState title="No history yet" description="Lessons and quizzes you complete will be listed here." />
    </div>
  );
}
