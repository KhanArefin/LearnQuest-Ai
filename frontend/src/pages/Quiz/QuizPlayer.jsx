import PageHeader from '../../components/layout/PageHeader';
import { EmptyState } from '../../components/ui';

export default function QuizPlayer() {
  return (
    <div>
      <PageHeader title="Quiz" subtitle="Answer each question, then review your result." />
      <EmptyState title="Quiz not available" description="This quiz has no questions yet." />
    </div>
  );
}
