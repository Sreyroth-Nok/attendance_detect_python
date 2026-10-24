import { useEffect, useId, useState } from 'react';
import { CheckCircle2, Download, FileUp, Loader2, XCircle } from 'lucide-react';
import Modal from './Modal';
import { useToast } from '../hooks/useToast';
import { studentService } from '../services/studentService';

const STATUS_STYLES = {
  completed: 'border-teal-200 bg-primary-soft text-primary',
  partial: 'border-yellow-200 bg-accent-soft text-yellow-800',
  rejected: 'border-red-200 bg-red-50 text-red-700',
};

function ImportReportView({ report }) {
  return (
    <div className="space-y-4">
      <div role="status" className={`rounded-lg border p-3 text-sm ${STATUS_STYLES[report.status]}`}>
        {report.message}
      </div>

      <dl className="grid grid-cols-3 gap-3 text-center">
        {[
          ['Rows in file', report.total_rows],
          ['Saved', report.imported],
          ['Failed', report.failed],
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg border border-line p-3">
            <dt className="text-xs text-secondary">{label}</dt>
            <dd className="text-xl font-semibold text-ink tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>

      {report.errors.length > 0 && (
        <section>
          <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-ink">
            <XCircle className="h-4 w-4 text-red-600" aria-hidden="true" /> Rows not saved
          </h3>
          <div className="max-h-56 overflow-auto rounded-lg border border-line">
            <table className="min-w-full text-sm">
              <thead className="sticky top-0 bg-slate-50 text-left text-xs text-secondary uppercase">
                <tr>
                  <th scope="col" className="px-3 py-2">Line</th>
                  <th scope="col" className="px-3 py-2">Student ID</th>
                  <th scope="col" className="px-3 py-2">Problem</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {report.errors.map((e) => (
                  <tr key={e.row}>
                    <td className="px-3 py-2 align-top tabular-nums">{e.row}</td>
                    <td className="px-3 py-2 align-top font-mono text-xs">{e.student_id || '—'}</td>
                    <td className="px-3 py-2 text-red-700">
                      <ul className="list-disc pl-4">
                        {e.errors.map((msg) => (
                          <li key={msg}>{msg}</li>
                        ))}
                      </ul>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {report.saved.length > 0 && (
        <section>
          <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-ink">
            <CheckCircle2 className="h-4 w-4 text-primary" aria-hidden="true" /> Rows saved
          </h3>
          <p className="max-h-28 overflow-auto rounded-lg border border-line p-3 font-mono text-xs text-secondary">
            {report.saved.map((s) => `${s.student_id} (line ${s.row})`).join(', ')}
          </p>
        </section>
      )}
    </div>
  );
}

export default function ImportModal({ open, onClose, onImported }) {
  const toast = useToast();
  const fileId = useId();
  const [file, setFile] = useState(null);
  const [skipInvalid, setSkipInvalid] = useState(false);
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (open) {
      setFile(null);
      setSkipInvalid(false);
      setReport(null);
      setError('');
    }
  }, [open]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!file || busy) return;
    setBusy(true);
    setError('');
    setReport(null);
    try {
      const result = await studentService.importCsv(file, { skipInvalid });
      setReport(result);
      if (result.imported > 0) {
        onImported?.();
        toast.success(result.message, 'Import finished');
      } else {
        toast.error(result.message, 'Nothing imported');
      }
    } catch (err) {
      setError(err.message);
      toast.error(err.message, 'Import failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={busy ? undefined : onClose}
      size="lg"
      title="Import students from CSV"
      description="Every row is validated before anything is saved."
      footer={
        <>
          <button type="button" className="btn-secondary" onClick={onClose} disabled={busy}>
            {report ? 'Close' : 'Cancel'}
          </button>
          <button type="submit" form="import-form" className="btn-primary" disabled={!file || busy}>
            {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <FileUp className="h-4 w-4" aria-hidden="true" />}
            Import
          </button>
        </>
      }
    >
      <form id="import-form" onSubmit={handleSubmit} className="space-y-4">
        <div className="flex flex-col gap-2 rounded-lg border border-line bg-slate-50 p-3 text-sm text-secondary sm:flex-row sm:items-center sm:justify-between">
          <span>
            Use UTF-8 CSV with columns: <code className="text-xs">student_id, full_name_khmer, full_name_latin, gender, program, major, academic_year, semester, status</code>
          </span>
          <a href="/student_import_template.csv" download className="btn-secondary shrink-0">
            <Download className="h-4 w-4" aria-hidden="true" /> Template
          </a>
        </div>

        <div>
          <label htmlFor={fileId} className="field-label">
            CSV file
          </label>
          <input
            id={fileId}
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => {
              setFile(e.target.files?.[0] || null);
              setReport(null);
            }}
            disabled={busy}
            className="block w-full text-sm text-secondary file:mr-3 file:rounded-lg file:border-0 file:bg-primary file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-primary-hover"
          />
          <p className="mt-1 text-xs text-secondary">Maximum 2 MB / 5,000 rows.</p>
        </div>

        <fieldset className="space-y-2">
          <legend className="field-label">If some rows are invalid</legend>
          <label className="flex items-start gap-2 text-sm">
            <input
              type="radio"
              name="mode"
              checked={!skipInvalid}
              onChange={() => setSkipInvalid(false)}
              className="mt-0.5 accent-primary"
            />
            <span>
              <span className="font-medium text-ink">Reject the whole file</span>
              <span className="block text-secondary">Nothing is saved until every row is valid. (Recommended)</span>
            </span>
          </label>
          <label className="flex items-start gap-2 text-sm">
            <input
              type="radio"
              name="mode"
              checked={skipInvalid}
              onChange={() => setSkipInvalid(true)}
              className="mt-0.5 accent-primary"
            />
            <span>
              <span className="font-medium text-ink">Import valid rows only</span>
              <span className="block text-secondary">Invalid rows are skipped and listed in the report.</span>
            </span>
          </label>
        </fieldset>

        {error && (
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}
      </form>

      {report && (
        <div className="mt-6 border-t border-line pt-5">
          <ImportReportView report={report} />
        </div>
      )}
    </Modal>
  );
}
