import { Link } from 'react-router-dom';
import PageHeader from '../components/PageHeader';
import { EmptyState } from '../components/States';

export default function NotFoundPage() {
  return (
    <>
      <PageHeader title="Page not found" breadcrumbs={[{ label: 'Not found' }]} />
      <div className="card">
        <EmptyState
          title="This page does not exist"
          message="The link may be outdated."
          action={
            <Link to="/" className="btn-primary">
              Go to dashboard
            </Link>
          }
        />
      </div>
    </>
  );
}
