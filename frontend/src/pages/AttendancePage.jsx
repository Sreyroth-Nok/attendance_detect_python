import { useEffect, useId, useState } from 'react';
import {
  AlertTriangle, Camera, CheckCircle2, ChevronLeft, ChevronRight, Loader2, ScanLine, Search, UserPlus, XCircle,
} from 'lucide-react';
import PageHeader from '../components/PageHeader';
import StatCard from '../components/StatCard';
import { EmptyState, ErrorState, LoadingState } from '../components/States';
import { useApiQuery } from '../hooks/useApiQuery';
import { useToast } from '../hooks/useToast';
import { attendanceService } from '../services/studentService';

const shortDate = (iso) => {
  const [, m, d] = iso.split('-');
  return `${d}/${m}`;
};

function Mark({ mark }) {
  if (mark === '✓')
    return (
      <span className="inline-flex h-6 min-w-6 items-center justify-center rounded bg-green-50 px-1 text-sm font-bold text-green-600">
        ✓<span className="sr-only"> (present)</span>
      </span>
    );
  if (mark === '✗')
    return (
      <span className="inline-flex h-6 min-w-6 items-center justify-center rounded bg-red-50 px-1 text-sm font-bold text-red-600">
        ✗<span className="sr-only"> (not present)</span>
      </span>
    );
  if (mark === '?')
    return (
      <span className="inline-flex h-6 min-w-6 items-center justify-center rounded bg-accent-soft px-1 text-xs font-bold text-yellow-800">
        ?<span className="sr-only"> (unreadable, check the paper)</span>
      </span>
    );
  return <span className="text-slate-300" aria-label="blank">—</span>;
}

function ScanResultView({ result }) {
  const { attendance, columns, rows, sheet } = result;
  return (
    <section aria-labelledby="result-heading" className="space-y-6">
      <div role="status" className="flex items-start gap-2 rounded-xl border border-teal-200 bg-primary-soft p-4 text-sm text-primary">
        <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
        <div>
          <h2 id="result-heading" className="font-semibold">Saved to the database</h2>
          <p className="mt-0.5">{result.message}</p>
          <p className="mt-1 text-xs text-secondary">
            {[sheet.major, sheet.program && `Program ${sheet.program}`, sheet.academic_year && `Year ${sheet.academic_year}`,
              sheet.semester && `Semester ${sheet.semester}`, sheet.week && `Week ${sheet.week}`, sheet.room && `Room ${sheet.room}`]
              .filter(Boolean)
              .join(' · ')}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Students on sheet" value={result.students_on_sheet} icon={ScanLine} />
        <StatCard label="New students registered" value={result.students_registered.length} icon={UserPlus} tone="accent" />
        <StatCard label="Present ✓" value={attendance.present} icon={CheckCircle2} />
        <StatCard label="Not present ✗" value={attendance.not_present} icon={XCircle} tone="slate" />
      </div>

      {result.warnings.length > 0 && (
        <div role="alert" className="rounded-xl border border-yellow-200 bg-accent-soft p-4 text-sm text-yellow-900">
          <p className="flex items-center gap-2 font-semibold">
            <AlertTriangle className="h-4 w-4" aria-hidden="true" /> Check these on the paper sheet
          </p>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {result.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-line text-sm">
            <thead className="bg-slate-50 text-xs text-secondary">
              <tr>
                <th scope="col" className="px-3 py-3 text-left font-semibold">No</th>
                <th scope="col" className="px-3 py-3 text-left font-semibold">Student ID</th>
                <th scope="col" className="px-3 py-3 text-left font-semibold">Khmer name</th>
                <th scope="col" className="px-3 py-3 text-left font-semibold">Name in Latin</th>
                {columns.map((c) => (
                  <th key={`${c.subject_code}-${c.date}-${c.session}`} scope="col" className="px-2 py-3 text-center font-semibold whitespace-nowrap">
                    {c.subject_code}
                    <span className="block font-normal">
                      {shortDate(c.date)} · S{c.session}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {rows.map((r) => (
                <tr key={r.student_id}>
                  <td className="px-3 py-2 text-secondary tabular-nums">{r.row}</td>
                  <td className="px-3 py-2 font-medium tabular-nums">
                    {r.student_id}
                    {result.students_registered.includes(r.student_id) && (
                      <span className="ml-2 rounded bg-accent-soft px-1.5 py-0.5 text-[10px] font-semibold text-yellow-800">NEW</span>
                    )}
                  </td>
                  <td lang="km" className="px-3 py-2 whitespace-nowrap">{r.full_name_khmer || <span className="text-slate-300">—</span>}</td>
                  <td className="px-3 py-2 whitespace-nowrap">{r.full_name_latin}</td>
                  {r.marks.map((m, i) => (
                    <td key={i} className="px-2 py-2 text-center">
                      <Mark mark={m} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

const NO_WEEK = 'none';
const NO_CLASS = 'No major';

const weekday = (iso) => new Date(`${iso}T00:00:00`).toLocaleDateString('en-GB', { weekday: 'short' });
const longDate = (iso) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });

// Spans for consecutive header cells with the same key, e.g. one date over its sessions.
function spans(items, keyOf) {
  const out = [];
  for (const item of items) {
    const key = keyOf(item);
    if (out.length && out[out.length - 1].key === key) out[out.length - 1].span += 1;
    else out.push({ key, item, span: 1 });
  }
  return out;
}

function CellMark({ present }) {
  if (present === undefined) return <span className="text-slate-300" aria-label="no mark">·</span>;
  return present ? (
    <span className="inline-flex h-7 w-7 items-center justify-center rounded-md bg-green-50 text-sm font-bold text-green-600" title="Present">
      ✓<span className="sr-only">present</span>
    </span>
  ) : (
    <span className="inline-flex h-7 w-7 items-center justify-center rounded-md bg-red-100 text-sm font-bold text-red-600 ring-1 ring-red-200" title="Not present">
      ✗<span className="sr-only">not present</span>
    </span>
  );
}

function RatePill({ present, total }) {
  if (!total) return <span className="text-slate-300">—</span>;
  const rate = Math.round((present / total) * 100);
  const tone = rate === 100 ? 'bg-green-50 text-green-700' : rate >= 75 ? 'bg-accent-soft text-yellow-800' : 'bg-red-50 text-red-700';
  return <span className={`inline-block min-w-12 rounded-full px-2 py-0.5 text-xs font-semibold tabular-nums ${tone}`}>{rate}%</span>;
}

function SummaryItem({ label, value, hint, tone = 'text-ink' }) {
  return (
    <div className="min-w-0 px-5 py-3">
      <p className="text-xs font-medium text-secondary">{label}</p>
      <p className={`mt-0.5 text-xl font-semibold tabular-nums ${tone}`}>{value}</p>
      {hint && <div className="mt-1.5">{hint}</div>}
    </div>
  );
}

// Student columns stay visible while scrolling sideways (from md up; too wide for phones).
const STICKY = [
  'md:sticky md:left-0 w-12 min-w-12',
  'md:sticky md:left-12 w-24 min-w-24',
  'md:sticky md:left-36 w-40 min-w-40',
  'md:sticky md:left-76 w-48 min-w-48 md:shadow-[4px_0_6px_-4px_rgb(15_23_42/0.15)]',
];

function RecordsTable({ refreshKey }) {
  const records = useApiQuery(() => attendanceService.records({ limit: 5000 }), [refreshKey]);
  const [klass, setKlass] = useState('');
  const [week, setWeek] = useState('');
  const [search, setSearch] = useState('');
  const [onlyAbsent, setOnlyAbsent] = useState(false);

  const all = records.data || [];
  // One sheet per class (major + year + program): each class gets its own tab, weeks and table.
  const classOf = (r) =>
    r.major ? [r.major, r.academic_year && `Year ${r.academic_year}`, r.program].filter(Boolean).join(' · ') : NO_CLASS;
  const classes = [...new Set(all.map(classOf))].sort((a, b) => (a === NO_CLASS) - (b === NO_CLASS) || a.localeCompare(b));
  const shownClass = classes.includes(klass) ? klass : classes[0];
  const studentCount = (m) => new Set(all.filter((r) => classOf(r) === m).map((r) => r.student_id)).size;
  const inClass = all.filter((r) => classOf(r) === shownClass);

  const weekOf = (r) => (r.week == null ? NO_WEEK : String(r.week));
  const weeks = [...new Set(inClass.map(weekOf))].sort((a, b) => (a === NO_WEEK) - (b === NO_WEEK) || b - a);
  const shownWeek = weeks.includes(week) ? week : weeks[0];
  const weekIndex = weeks.indexOf(shownWeek);
  const rows = inClass.filter((r) => weekOf(r) === shownWeek);

  // Pivot like the paper sheet: one row per student, one column per date + subject + session.
  const colKey = (r) => `${r.date}|${r.subject_code}|${r.session}`;
  const columns = [...new Map(rows.map((r) => [colKey(r), r])).values()].sort(
    (a, b) => a.date.localeCompare(b.date) || a.subject_code.localeCompare(b.subject_code) || a.session - b.session,
  );
  const marks = new Map(rows.map((r) => [`${r.student_id}|${colKey(r)}`, r.is_present]));
  const markOf = (st, c) => marks.get(`${st.student_id}|${colKey(c)}`);
  const students = [...new Map(rows.map((r) => [r.student_id, r])).values()]
    .sort((a, b) => a.full_name_latin.localeCompare(b.full_name_latin))
    .map((st, i) => {
      const own = columns.map((c) => markOf(st, c)).filter((m) => m !== undefined);
      return { ...st, no: i + 1, present: own.filter(Boolean).length, total: own.length };
    });
  const subjects = [...new Map(columns.map((c) => [c.subject_code, c.subject_name])).entries()];
  const dateGroups = spans(columns, (c) => c.date);
  const subjectGroups = spans(columns, (c) => `${c.date}|${c.subject_code}`);

  const present = rows.filter((r) => r.is_present).length;
  const rate = rows.length ? (present / rows.length) * 100 : 0;
  const withAbsence = students.filter((st) => st.present < st.total);
  const term = search.trim().toLowerCase();
  const visible = students.filter(
    (st) =>
      (!onlyAbsent || st.present < st.total) &&
      (!term || [st.student_id, st.full_name_latin, st.full_name_khmer].some((v) => v?.toLowerCase().includes(term))),
  );

  const th = 'border-b border-r border-line bg-slate-50 px-2 py-2 text-xs font-semibold text-secondary';
  const td = 'border-b border-r border-line px-2 py-1.5 bg-white group-even:bg-slate-50 group-hover:bg-primary-soft';

  return (
    <section aria-labelledby="records-heading" className="card overflow-hidden">
      <div className="flex flex-col gap-3 p-5 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 id="records-heading" className="text-base font-semibold text-ink">
            Saved attendance records
          </h2>
          {columns.length > 0 && (
            <p className="mt-0.5 text-sm text-secondary">
              {shownClass} · {shownWeek === NO_WEEK ? 'No week' : `Week ${shownWeek}`} · {longDate(columns[0].date)}
              {columns.at(-1).date !== columns[0].date && ` – ${longDate(columns.at(-1).date)}`}
            </p>
          )}
        </div>
        {weeks.length > 0 && (
          <div className="flex items-center gap-1">
            <button
              type="button"
              className="icon-btn disabled:opacity-40"
              aria-label="Previous week"
              disabled={weekIndex >= weeks.length - 1}
              onClick={() => setWeek(weeks[weekIndex + 1])}
            >
              <ChevronLeft className="h-4 w-4" aria-hidden="true" />
            </button>
            <label htmlFor="rec-week" className="sr-only">Week</label>
            <select id="rec-week" value={shownWeek} onChange={(e) => setWeek(e.target.value)} className="field-input w-auto">
              {weeks.map((w) => (
                <option key={w} value={w}>{w === NO_WEEK ? 'No week' : `Week ${w}`}</option>
              ))}
            </select>
            <button
              type="button"
              className="icon-btn disabled:opacity-40"
              aria-label="Next week"
              disabled={weekIndex <= 0}
              onClick={() => setWeek(weeks[weekIndex - 1])}
            >
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        )}
      </div>

      {classes.length > 0 && (
        <div role="tablist" aria-label="Class" className="flex gap-1 overflow-x-auto px-5">
          {classes.map((m) => {
            const active = m === shownClass;
            return (
              <button
                key={m}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => {
                  setKlass(m);
                  setWeek('');
                }}
                className={`-mb-px flex shrink-0 items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium whitespace-nowrap transition-colors ${
                  active ? 'border-primary text-primary' : 'border-transparent text-secondary hover:text-ink'
                }`}
              >
                {m}
                <span className={`rounded-full px-1.5 text-xs tabular-nums ${active ? 'bg-primary-soft' : 'bg-slate-100'}`}>
                  {studentCount(m)}
                </span>
              </button>
            );
          })}
        </div>
      )}

      {records.loading && !records.data ? (
        <LoadingState label="Loading records…" />
      ) : records.error ? (
        <ErrorState error={records.error} onRetry={records.reload} />
      ) : !all.length ? (
        <EmptyState title="No attendance saved yet" message="Scan a sheet above to save its marks." />
      ) : (
        <>
          <div className="grid grid-cols-2 border-y border-line lg:grid-cols-4 lg:divide-x lg:divide-line">
            <SummaryItem
              label="Attendance rate"
              value={`${Math.round(rate)}%`}
              tone="text-primary"
              hint={
                <div className="h-1.5 w-full max-w-40 overflow-hidden rounded-full bg-slate-100">
                  <div className="h-full rounded-full bg-primary" style={{ width: `${rate}%` }} />
                </div>
              }
            />
            <SummaryItem label="Present ✓" value={present} tone="text-green-600" />
            <SummaryItem label="Not present ✗" value={rows.length - present} tone="text-red-600" />
            <SummaryItem label="Students with ✗" value={`${withAbsence.length} / ${students.length}`} />
          </div>

          <div className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative">
                <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
                <label htmlFor="rec-search" className="sr-only">Search students</label>
                <input
                  id="rec-search"
                  type="search"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search name or ID"
                  className="field-input w-64 pl-9"
                />
              </div>
              <button
                type="button"
                aria-pressed={onlyAbsent}
                onClick={() => setOnlyAbsent((v) => !v)}
                className={`btn border px-3 py-1.5 ${onlyAbsent ? 'border-red-200 bg-red-50 text-red-700' : 'border-line bg-white text-secondary hover:bg-slate-50'}`}
              >
                <XCircle className="h-4 w-4" aria-hidden="true" /> Only students with ✗ ({withAbsence.length})
              </button>
            </div>
            <p className="flex items-center gap-4 text-xs text-secondary">
              <span className="inline-flex items-center gap-1.5"><CellMark present /> Present</span>
              <span className="inline-flex items-center gap-1.5"><CellMark present={false} /> Not present</span>
            </p>
          </div>

          <div className="max-h-[42rem] overflow-auto border-t border-line">
            <table className="min-w-full border-separate border-spacing-0 text-sm">
              <thead className="sticky top-0 z-20">
                <tr>
                  {['Nº', 'ID', 'Full Name', 'Name in Latin'].map((h, i) => (
                    <th key={h} scope="col" rowSpan={3} className={`${th} ${STICKY[i]} z-10 text-left align-bottom`}>{h}</th>
                  ))}
                  <th scope="row" className={`${th} text-right font-medium`}>Date</th>
                  {dateGroups.map((g) => (
                    <th key={g.key} scope="colgroup" colSpan={g.span} className={`${th} text-center whitespace-nowrap text-ink`}>
                      <span className="block text-[10px] font-medium tracking-wide text-secondary uppercase">{weekday(g.key)}</span>
                      {shortDate(g.key)}/{g.key.slice(2, 4)}
                    </th>
                  ))}
                  <th scope="col" rowSpan={3} className={`${th} text-center align-bottom`}>Present</th>
                  <th scope="col" rowSpan={3} className={`${th} text-center align-bottom`}>Rate</th>
                </tr>
                <tr>
                  <th scope="row" className={`${th} text-right font-medium`}>Subject</th>
                  {subjectGroups.map((g) => (
                    <th
                      key={g.key}
                      scope="colgroup"
                      colSpan={g.span}
                      title={g.item.subject_name}
                      className={`${th} text-center whitespace-nowrap text-primary`}
                    >
                      {g.item.subject_code}
                    </th>
                  ))}
                </tr>
                <tr>
                  <th scope="row" className={`${th} text-right font-medium`}>Session</th>
                  {columns.map((c) => (
                    <th key={colKey(c)} scope="col" className={`${th} w-11 text-center`}>{c.session}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visible.map((st) => (
                  <tr key={st.student_id} className="group">
                    <td className={`${td} ${STICKY[0]} text-center text-secondary tabular-nums`}>{st.no}</td>
                    <td className={`${td} ${STICKY[1]} font-medium tabular-nums`}>{st.student_id}</td>
                    <td lang="km" className={`${td} ${STICKY[2]} py-0.5 whitespace-nowrap`}>
                      {st.full_name_khmer || <span className="text-slate-300">—</span>}
                    </td>
                    <td className={`${td} ${STICKY[3]} font-medium whitespace-nowrap text-ink uppercase`}>{st.full_name_latin}</td>
                    <td className={`${td} text-center`}>
                      <span
                        className={`inline-block w-6 rounded text-xs font-semibold ${st.gender === 'Female' ? 'bg-pink-50 text-pink-700' : 'bg-sky-50 text-sky-700'}`}
                      >
                        {st.gender?.[0]}
                      </span>
                    </td>
                    {columns.map((c) => (
                      <td key={colKey(c)} className={`${td} px-1 text-center`}>
                        <CellMark present={markOf(st, c)} />
                      </td>
                    ))}
                    <td className={`${td} text-center text-secondary tabular-nums`}>{st.present}/{st.total}</td>
                    <td className={`${td} text-center`}><RatePill present={st.present} total={st.total} /></td>
                  </tr>
                ))}
                {!visible.length && (
                  <tr>
                    <td colSpan={columns.length + 7} className="px-4 py-10 text-center text-sm text-secondary">
                      No students match.
                    </td>
                  </tr>
                )}
              </tbody>
              <tfoot className="sticky bottom-0 z-20">
                <tr>
                  <td colSpan={5} className={`${th} text-right`}>Present per session</td>
                  {columns.map((c) => {
                    const col = students.map((st) => markOf(st, c)).filter((m) => m !== undefined);
                    return (
                      <td key={colKey(c)} className={`${th} text-center text-ink tabular-nums`}>
                        {col.filter(Boolean).length}
                        <span className="font-normal text-secondary">/{col.length}</span>
                      </td>
                    );
                  })}
                  <td className={`${th} text-center text-ink tabular-nums`}>{present}/{rows.length}</td>
                  <td className={`${th} text-center`}><RatePill present={present} total={rows.length} /></td>
                </tr>
              </tfoot>
            </table>
          </div>

          <div className="flex flex-col gap-2 border-t border-line px-5 py-3 text-xs text-secondary sm:flex-row sm:items-center sm:justify-between">
            <ul className="flex flex-wrap gap-x-4 gap-y-1">
              {subjects.map(([code, name]) => (
                <li key={code}>
                  <span className="font-semibold text-primary">{code}</span> = {name}
                </li>
              ))}
            </ul>
            <span className="shrink-0">
              Showing {visible.length} of {students.length} student(s) · {columns.length} session(s)
            </span>
          </div>
        </>
      )}
    </section>
  );
}

export default function AttendancePage() {
  const toast = useToast();
  const inputId = useId();
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (!file) return undefined;
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const scan = async (event) => {
    event.preventDefault();
    if (!file || busy) return;
    setBusy(true);
    setError('');
    setResult(null);
    try {
      const res = await attendanceService.scan(file);
      setResult(res);
      setRefreshKey((k) => k + 1);
      toast.success(res.message, 'Attendance saved');
    } catch (err) {
      setError(err.message);
      toast.error(err.message, 'Scan failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Attendance"
        breadcrumbs={[{ label: 'Attendance' }]}
        description="Upload a photo of a paper attendance sheet. Each student is listed with ✓ if checked (present) or ✗ if not (a P or an empty cell)."
      />

      <div className="space-y-8">
        <form onSubmit={scan} className="card grid gap-6 p-6 md:grid-cols-[1fr_16rem]">
          <div>
            <label htmlFor={inputId} className="field-label">
              Attendance sheet photo
            </label>
            <input
              id={inputId}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              disabled={busy}
              onChange={(e) => {
                setFile(e.target.files?.[0] || null);
                setResult(null);
                setError('');
              }}
              className="block w-full text-sm text-secondary file:mr-3 file:rounded-lg file:border-0 file:bg-primary file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-primary-hover"
            />
            <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-secondary">
              <li>Take the photo straight on, with the whole sheet visible and in focus.</li>
              <li>Students not yet in the system are registered from the sheet header (major, program, year, semester).</li>
              <li>Khmer names are read by OCR and may contain small spelling slips; fix them on the Students page.</li>
              <li>Cells that cannot be read are skipped and listed so you can check them.</li>
            </ul>
            <button type="submit" className="btn-primary mt-5" disabled={!file || busy}>
              {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <ScanLine className="h-4 w-4" aria-hidden="true" />}
              {busy ? 'Reading sheet… (up to a minute)' : 'Scan & save'}
            </button>
            {error && (
              <div role="alert" className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {error}
              </div>
            )}
          </div>
          <div className="flex aspect-[3/4] items-center justify-center overflow-hidden rounded-lg border border-dashed border-line bg-slate-50">
            {preview && file ? (
              <img src={preview} alt="Selected attendance sheet" className="h-full w-full object-contain" />
            ) : (
              <span className="flex flex-col items-center gap-2 text-xs text-secondary">
                <Camera className="h-8 w-8 text-slate-400" aria-hidden="true" /> Photo preview
              </span>
            )}
          </div>
        </form>

        {result && <ScanResultView result={result} />}

        <RecordsTable refreshKey={refreshKey} />
      </div>
    </>
  );
}
