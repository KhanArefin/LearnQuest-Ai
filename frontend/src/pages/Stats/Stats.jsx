import PageHeader from '../../components/layout/PageHeader';
import { EmptyState } from '../../components/ui';

export default function Stats() {
  return (
    <div>
      <PageHeader title="Stats" subtitle="Your activity, accuracy and topic mastery over time." />
      <EmptyState title="No activity yet" description="Complete a lesson or a quiz and your progress will appear here." />
    </div>
  );
}
