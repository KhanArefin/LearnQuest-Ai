import PageHeader from '../../components/layout/PageHeader';
import { EmptyState } from '../../components/ui';

export default function Achievements() {
  return (
    <div>
      <PageHeader title="Achievements" subtitle="Badges you have earned and what is still to unlock." />
      <EmptyState title="Nothing here yet" description="Earn your first badge by completing a lesson or a quiz." />
    </div>
  );
}
