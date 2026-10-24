import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Pencil, RotateCcw, UserX } from 'lucide-react';
import ConfirmDialog from '../components/ConfirmDialog';
import PageHeader from '../components/PageHeader';
import StatusBadge from '../components/StatusBadge';
import StudentFormModal from '../components/StudentFormModal';
import { ErrorState, LoadingState } from '../components/States';
import { useApiQuery } from '../hooks/useApiQuery';
import { useStudentStatusToggle } from '../hooks/useStudentStatusToggle';
import { studentService } from '../services/studentService';
import { formatDateTime, semesterLabel } from '../types/student';

function DetailItem({ label, children, lang }) {
  return (
    <div className="border-b border-line py-3 sm:grid sm:grid-cols-3 sm:gap-4">
      <dt className="text-sm font-medium text-secondary">{label}</dt>
      <dd lang={lang} className="mt-1 text-sm text-ink sm:col-span-2 sm:mt-0">
        {children ?? '—'}
      </dd>
    </div>
  );
}

export default function StudentDetailPage() {
  const { id } = useParams();
  const { data: student, error, loading, reload, setData } = useApiQuery(() => studentService.get(id), [id]);
  const [editing, setEditing] = useState(false);
  const statusToggle = useStudentStatusToggle(setData);

  const title = student ? student.full_name_latin : 'Student details';

  return (
    <>
      <PageHeader
        title={title}
        breadcrumbs={[{ label: 'Students', to: '/students' }, { label: student?.student_id || 'Details' }]}
        actions={
          student && (
            <>
              <Link to="/students" className="btn-secondary">
                <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back
              </Link>
              <button
                type="button"
                className={student.status === 'Active' ? 'btn-secondary text-red-600' : 'btn-secondary'}
                onClick={() => statusToggle.request(student)}
              >
                {student.status === 'Active' ? (
                  <>
                    <UserX className="h-4 w-4" aria-hidden="true" /> Deactivate
                  </>
                ) : (
                  <>
                    <RotateCcw className="h-4 w-4" aria-hidden="true" /> Reactivate
                  </>
                )}
              </button>
              <button type="button" className="btn-primary" onClick={() => setEditing(true)}>
                <Pencil className="h-4 w-4" aria-hidden="true" /> Edit
              </button>
            </>
          )
        }
      />

      {loading && !student ? (
        <div className="card">
          <LoadingState label="Loading student…" />
        </div>
      ) : error ? (
        <div className="card">
          <ErrorState error={error} onRetry={error.status === 404 ? undefined : reload} />
          {error.status === 404 && (
            <div className="pb-10 text-center">
              <Link to="/students" className="btn-secondary">
                Back to students
              </Link>
            </div>
          )}
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          <section className="card p-6 lg:col-span-2" aria-labelledby="profile-heading">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 id="profile-heading" className="text-base font-semibold text-ink">
                Student information
              </h2>
              <StatusBadge status={student.status} />
            </div>
            <dl className="mt-2">
              <DetailItem label="Student ID">
                <span className="font-medium tabular-nums">{student.student_id}</span>
              </DetailItem>
              <DetailItem label="Full name (Khmer)" lang="km">
                {student.full_name_khmer}
              </DetailItem>
              <DetailItem label="Full name (Latin)">{student.full_name_latin}</DetailItem>
              <DetailItem label="Gender">{student.gender}</DetailItem>
              <DetailItem label="Program">{student.program}</DetailItem>
              <DetailItem label="Major">{student.major}</DetailItem>
              <DetailItem label="Academic year">{student.academic_year}</DetailItem>
              <DetailItem label="Semester">{student.semester ? semesterLabel(student.semester) : null}</DetailItem>
              <DetailItem label="Status">{student.status}</DetailItem>
            </dl>
          </section>

          <section className="card h-fit p-6" aria-labelledby="record-heading">
            <h2 id="record-heading" className="text-base font-semibold text-ink">
              Record
            </h2>
            <dl className="mt-2">
              <div className="border-b border-line py-3">
                <dt className="text-sm font-medium text-secondary">Registered</dt>
                <dd className="mt-1 text-sm text-ink">
                  <time dateTime={student.created_at}>{formatDateTime(student.created_at)}</time>
                </dd>
              </div>
              <div className="border-b border-line py-3">
                <dt className="text-sm font-medium text-secondary">Last updated</dt>
                <dd className="mt-1 text-sm text-ink">
                  <time dateTime={student.updated_at}>{formatDateTime(student.updated_at)}</time>
                </dd>
              </div>
              <div className="py-3">
                <dt className="text-sm font-medium text-secondary">Internal ID</dt>
                <dd className="mt-1 font-mono text-sm text-ink">{student.id}</dd>
              </div>
            </dl>
          </section>
        </div>
      )}

      <StudentFormModal
        open={editing}
        student={student}
        onClose={() => setEditing(false)}
        onSaved={(saved) => {
          setEditing(false);
          setData(saved);
        }}
      />
      <ConfirmDialog {...statusToggle.dialogProps} />
    </>
  );
}
