import PageHeader from '../../components/layout/PageHeader';
import { EmptyState } from '../../components/ui';

export default function AdminUsers() {
  return (
    <div>
      <PageHeader title="Users" subtitle="Manage accounts and roles." />
      <EmptyState title="No users to show" description="Registered users will be listed here." />
    </div>
  );
}
