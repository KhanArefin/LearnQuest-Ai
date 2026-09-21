import PageHeader from '../../components/layout/PageHeader';
import { EmptyState } from '../../components/ui';

export default function QuizResult() {
  return (
    <div>
      <PageHeader title="Quiz result" subtitle="Your score and a question-by-question review." />
      <EmptyState title="No result to show" description="Complete a quiz to see your result here." />
    </div>
  );
}
