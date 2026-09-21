import PageHeader from '../../components/layout/PageHeader';
import { EmptyState } from '../../components/ui';

export default function Leaderboard() {
  return (
    <div>
      <PageHeader title="Leaderboard" subtitle="How you compare with other learners this week." />
      <EmptyState title="Leaderboard is empty" description="Rankings appear once learners start earning XP." />
    </div>
  );
}
