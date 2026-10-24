import { Link } from 'react-router-dom';
import { ArrowRight, BookOpen, UserCheck, UserX, Users } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import StatCard from '../components/StatCard';
import { EmptyState, ErrorState, LoadingState } from '../components/States';
import { useApiQuery } from '../hooks/useApiQuery';
import { dashboardService } from '../services/studentService';

const number = new Intl.NumberFormat();

export default function DashboardPage() {
  const { data: stats, error, loading, reload } = useApiQuery(() => dashboardService.stats(), []);

  return (
    <>
      <PageHeader
        title="Dashboard"
        breadcrumbs={[{ label: 'Dashboard' }]}
        description="Overview of registered students."
        actions={
          <Link to="/students" className="btn-primary">
            Manage students <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        }
      />

      {loading && !stats ? (
        <div className="card">
          <LoadingState label="Loading statistics…" />
        </div>
      ) : error ? (
        <div className="card">
          <ErrorState error={error} onRetry={reload} />
        </div>
      ) : (
        <div className="space-y-8">
          <section aria-label="Summary" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Total students" value={number.format(stats.total_students)} icon={Users} />
            <StatCard
              label="Active students"
              value={number.format(stats.active_students)}
              icon={UserCheck}
              hint={
                stats.total_students
                  ? `${Math.round((stats.active_students / stats.total_students) * 100)}% of all students`
                  : undefined
              }
            />
            <StatCard
              label="Inactive students"
              value={number.format(stats.inactive_students)}
              icon={UserX}
              tone="slate"
            />
            <StatCard
              label="Majors"
              value={number.format(stats.by_major.filter((m) => m.major !== 'Unassigned').length)}
              icon={BookOpen}
              tone="accent"
            />
          </section>

          <section aria-labelledby="by-major-heading">
            <div className="mb-3 flex items-center justify-between">
              <h2 id="by-major-heading" className="text-lg font-semibold text-ink">
                Students by major
              </h2>
              {stats.by_gender.length > 0 && (
                <p className="text-sm text-secondary">
                  {stats.by_gender.map((g) => `${g.gender}: ${number.format(g.total)}`).join(' · ')}
                </p>
              )}
            </div>

            {stats.by_major.length === 0 ? (
              <div className="card">
                <EmptyState
                  title="No students yet"
                  message="Add students or import a CSV file to see statistics here."
                  action={
                    <Link to="/students" className="btn-primary">
                      Go to students
                    </Link>
                  }
                />
              </div>
            ) : (
              <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {stats.by_major.map((m) => (
                  <li key={m.major}>
                    <Link
                      to={m.major === 'Unassigned' ? '/students' : `/students?major=${encodeURIComponent(m.major)}`}
                      className="card block p-5 transition-shadow hover:shadow-md focus-visible:outline-2 focus-visible:outline-primary"
                    >
                      <p className="truncate text-sm font-medium text-secondary" title={m.major}>
                        {m.major}
                      </p>
                      <p className="mt-1 text-2xl font-semibold text-ink tabular-nums">{number.format(m.total)}</p>
                      <p className="mt-1 text-xs text-secondary">
                        <span className="font-medium text-primary">{number.format(m.active)} active</span>
                        {' · '}
                        {number.format(m.total - m.active)} inactive
                      </p>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </>
  );
}
