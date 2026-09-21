import PageHeader from '../../components/layout/PageHeader';
import { EmptyState } from '../../components/ui';

export default function AdminOverview() {
  return (
    <div>
      <PageHeader title="Admin overview" subtitle="Platform activity at a glance." />
      <EmptyState title="No data yet" description="Usage statistics will appear here." />
    </div>
  );
}
