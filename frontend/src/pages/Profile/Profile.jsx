import PageHeader from '../../components/layout/PageHeader';
import { EmptyState } from '../../components/ui';

export default function Profile() {
  return (
    <div>
      <PageHeader title="Profile" subtitle="Your account details and learning preferences." />
      <EmptyState title="Profile not available" description="Account settings will appear here." />
    </div>
  );
}
