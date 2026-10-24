import { Link, useNavigate } from 'react-router-dom';
import { ArrowDown, ArrowUp, ArrowUpDown, Eye, Pencil, RotateCcw, UserX } from 'lucide-react';
import StatusBadge from './StatusBadge';
import { TABLE_COLUMNS, semesterLabel } from '../types/student';

function SortHeader({ column, sortBy, sortOrder, onSort }) {
  const active = sortBy === column.key;
  const Icon = !active ? ArrowUpDown : sortOrder === 'asc' ? ArrowUp : ArrowDown;
  const nextOrder = active && sortOrder === 'asc' ? 'desc' : 'asc';
  return (
    <th
      scope="col"
      aria-sort={active ? (sortOrder === 'asc' ? 'ascending' : 'descending') : 'none'}
      className="px-2 py-3 text-left text-xs font-semibold tracking-wide whitespace-nowrap text-secondary uppercase first:pl-4"
    >
      <button
        type="button"
        onClick={() => onSort(column.key, nextOrder)}
        className={`inline-flex items-center gap-1 rounded hover:text-ink focus-visible:outline-2 focus-visible:outline-primary ${
          active ? 'text-ink' : ''
        }`}
      >
        {column.label}
        <Icon className={`h-3.5 w-3.5 ${active ? 'text-primary' : 'text-slate-400'}`} aria-hidden="true" />
        <span className="sr-only">, sort {nextOrder === 'asc' ? 'ascending' : 'descending'}</span>
      </button>
    </th>
  );
}

function RowActions({ student, onEdit, onToggleStatus }) {
  const active = student.status === 'Active';
  const name = student.full_name_latin;
  return (
    <div className="flex items-center justify-end gap-1">
      <Link to={`/students/${student.id}`} className="icon-btn" aria-label={`View ${name}`} title="View details">
        <Eye className="h-4 w-4" />
      </Link>
      <button
        type="button"
        className="icon-btn"
        onClick={() => onEdit(student)}
        aria-label={`Edit ${name}`}
        title="Edit"
      >
        <Pencil className="h-4 w-4" />
      </button>
      <button
        type="button"
        className={`icon-btn ${active ? 'hover:bg-red-50 hover:text-red-600' : 'hover:bg-primary-soft hover:text-primary'}`}
        onClick={() => onToggleStatus(student)}
        aria-label={active ? `Deactivate ${name}` : `Reactivate ${name}`}
        title={active ? 'Deactivate' : 'Reactivate'}
      >
        {active ? <UserX className="h-4 w-4" /> : <RotateCcw className="h-4 w-4" />}
      </button>
    </div>
  );
}

const dash = (v) => (v === null || v === undefined || v === '' ? '—' : v);

export default function StudentTable({ students, sortBy, sortOrder, onSort, onEdit, onToggleStatus }) {
  const navigate = useNavigate();
  const open = (student) => navigate(`/students/${student.id}`);

  return (
    <>
      {/* Desktop / tablet: full table */}
      <div className="hidden overflow-x-auto md:block">
        <table className="min-w-full divide-y divide-line text-sm">
          <thead className="bg-slate-50">
            <tr>
              {TABLE_COLUMNS.map((column) => (
                <SortHeader
                  key={column.key}
                  column={column}
                  sortBy={sortBy}
                  sortOrder={sortOrder}
                  onSort={onSort}
                />
              ))}
              <th
                scope="col"
                className="sticky right-0 bg-slate-50 py-3 pr-4 pl-2 text-right text-xs font-semibold tracking-wide text-secondary"
              >
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line bg-white">
            {students.map((s) => (
              <tr
                key={s.id}
                onClick={(e) => {
                  if (!e.target.closest('a,button')) open(s);
                }}
                className="group cursor-pointer transition-colors hover:bg-primary-soft"
              >
                <td className="py-3 pr-2 pl-4 font-medium whitespace-nowrap text-ink tabular-nums">
                  <Link to={`/students/${s.id}`} className="hover:text-primary hover:underline">
                    {s.student_id}
                  </Link>
                </td>
                <td lang="km" className="min-w-[7rem] px-2 py-2">
                  {dash(s.full_name_khmer)}
                </td>
                <td className="min-w-[8rem] px-2 py-3 font-medium">{s.full_name_latin}</td>
                <td className="px-2 py-3 whitespace-nowrap text-secondary">{s.gender}</td>
                <td className="px-2 py-3 whitespace-nowrap text-secondary">{dash(s.program)}</td>
                <td className="min-w-[7rem] px-2 py-3 text-secondary">{dash(s.major)}</td>
                <td className="px-2 py-3 text-center whitespace-nowrap text-secondary">{dash(s.academic_year)}</td>
                <td className="px-2 py-3 whitespace-nowrap text-secondary">{semesterLabel(s.semester)}</td>
                <td className="px-2 py-3 whitespace-nowrap">
                  <StatusBadge status={s.status} />
                </td>
                <td className="sticky right-0 bg-white py-2 pr-3 pl-2 shadow-[-8px_0_8px_-8px_rgb(15_23_42/0.15)] group-hover:bg-primary-soft">
                  <RowActions student={s} onEdit={onEdit} onToggleStatus={onToggleStatus} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile: stacked cards */}
      <ul className="divide-y divide-line md:hidden">
        {students.map((s) => (
          <li key={s.id} className="flex items-start gap-3 px-4 py-4">
            <Link to={`/students/${s.id}`} className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-medium text-secondary tabular-nums">{s.student_id}</span>
                <StatusBadge status={s.status} />
              </div>
              <p className="mt-1 truncate font-medium text-ink">{s.full_name_latin}</p>
              {s.full_name_khmer && (
                <p lang="km" className="truncate text-sm text-secondary">
                  {s.full_name_khmer}
                </p>
              )}
              <p className="mt-1 text-xs text-secondary">
                {[s.gender, s.major, s.academic_year && `Year ${s.academic_year}`, s.semester && semesterLabel(s.semester)]
                  .filter(Boolean)
                  .join(' · ')}
              </p>
            </Link>
            <RowActions student={s} onEdit={onEdit} onToggleStatus={onToggleStatus} />
          </li>
        ))}
      </ul>
    </>
  );
}
