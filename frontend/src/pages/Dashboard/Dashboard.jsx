import PageHeader from '../../components/layout/PageHeader';
import { EmptyState } from '../../components/ui';

export default function Dashboard() {
  return (
    <div>
      <PageHeader title="Dashboard" subtitle="Your progress, current streak and what to do next." />
      <EmptyState title="Nothing to show yet" description="Start a course or generate a roadmap and your dashboard will fill in." />
    </div>
  );
}
