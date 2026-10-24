import { useEffect, useState } from 'react';
import { Download, Loader2, Plus, Upload } from 'lucide-react';
import ConfirmDialog from '../components/ConfirmDialog';
import ImportModal from '../components/ImportModal';
import PageHeader from '../components/PageHeader';
import Pagination from '../components/Pagination';
import StudentFilters from '../components/StudentFilters';
import StudentFormModal from '../components/StudentFormModal';
import StudentTable from '../components/StudentTable';
import { EmptyState, ErrorState, LoadingState } from '../components/States';
import { useApiQuery } from '../hooks/useApiQuery';
import { useStudentQuery } from '../hooks/useStudentQuery';
import { useToast } from '../hooks/useToast';
import { useStudentStatusToggle } from '../hooks/useStudentStatusToggle';
import { studentService } from '../services/studentService';

export default function StudentsPage() {
  const toast = useToast();
  const { query, filters, hasFilters, update, clearFilters } = useStudentQuery();

  const students = useApiQuery(() => studentService.list(query), [query]);
  const options = useApiQuery(() => studentService.filterOptions(), []);

  const [formState, setFormState] = useState({ open: false, student: null });
  const [importOpen, setImportOpen] = useState(false);
  const [exporting, setExporting] = useState(false);

  const refresh = () => {
    students.reload();
    options.reload();
  };
  const statusToggle = useStudentStatusToggle(refresh);

  const handleExport = async () => {
    setExporting(true);
    try {
      const filename = await studentService.exportCsv(filters);
      toast.success(`Saved ${filename}.`, 'Export ready');
    } catch (err) {
      toast.error(err.message, 'Export failed');
    } finally {
      setExporting(false);
    }
  };

  const data = students.data;
  // If the current page no longer exists (e.g. after deactivations), go back to the last page.
  useEffect(() => {
    if (data && data.pages > 0 && query.page > data.pages) update({ page: data.pages }, { resetPage: false });
  }, [data, query.page, update]);

  let body;
  if (students.loading && !data) body = <LoadingState label="Loading students…" />;
  else if (students.error) body = <ErrorState error={students.error} onRetry={students.reload} />;
  else if (!data.items.length)
    body = hasFilters ? (
      <EmptyState
        title="No matching students"
        message="No students match the current search and filters."
        action={
          <button type="button" className="btn-secondary" onClick={clearFilters}>
            Clear filters
          </button>
        }
      />
    ) : (
      <EmptyState
        title="No students registered yet"
        message="Add your first student or import an existing attendance sheet as CSV."
        action={
          <button type="button" className="btn-primary" onClick={() => setFormState({ open: true, student: null })}>
            <Plus className="h-4 w-4" aria-hidden="true" /> Add student
          </button>
        }
      />
    );
  else
    body = (
      <div className={students.loading ? 'opacity-60 transition-opacity' : ''} aria-busy={students.loading}>
        <StudentTable
          students={data.items}
          sortBy={query.sort_by}
          sortOrder={query.sort_order}
          onSort={(sort_by, sort_order) => update({ sort_by, sort_order }, { resetPage: false })}
          onEdit={(student) => setFormState({ open: true, student })}
          onToggleStatus={statusToggle.request}
        />
        <Pagination
          page={data.page}
          pages={data.pages}
          total={data.total}
          pageSize={data.page_size}
          onPageChange={(page) => update({ page }, { resetPage: false })}
          onPageSizeChange={(page_size) => update({ page_size })}
        />
      </div>
    );

  return (
    <>
      <PageHeader
        title="Students"
        breadcrumbs={[{ label: 'Students' }]}
        description="Register, search and maintain student records."
        actions={
          <>
            <button type="button" className="btn-secondary" onClick={() => setImportOpen(true)}>
              <Upload className="h-4 w-4" aria-hidden="true" /> Import CSV
            </button>
            <button type="button" className="btn-secondary" onClick={handleExport} disabled={exporting}>
              {exporting ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Download className="h-4 w-4" aria-hidden="true" />
              )}
              Export CSV
            </button>
            <button type="button" className="btn-primary" onClick={() => setFormState({ open: true, student: null })}>
              <Plus className="h-4 w-4" aria-hidden="true" /> Add Student
            </button>
          </>
        }
      />

      <div className="card overflow-hidden">
        <StudentFilters
          query={query}
          options={options.data}
          hasFilters={hasFilters}
          onChange={update}
          onClear={clearFilters}
        />
        {body}
      </div>

      <StudentFormModal
        open={formState.open}
        student={formState.student}
        filterOptions={options.data}
        onClose={() => setFormState({ open: false, student: null })}
        onSaved={() => {
          setFormState({ open: false, student: null });
          refresh();
        }}
      />

      <ImportModal open={importOpen} onClose={() => setImportOpen(false)} onImported={refresh} />

      <ConfirmDialog {...statusToggle.dialogProps} />
    </>
  );
}
