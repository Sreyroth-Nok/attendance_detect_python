/**
 * Student domain constants, JSDoc types and client-side validation.
 * The rules mirror backend/app/schemas/student.py; the backend remains the authority.
 */

/**
 * @typedef {Object} Student
 * @property {number} id
 * @property {string} student_id
 * @property {string|null} full_name_khmer
 * @property {string} full_name_latin
 * @property {'Male'|'Female'|'Other'} gender
 * @property {string|null} program
 * @property {string|null} major
 * @property {number|null} academic_year
 * @property {1|2|null} semester
 * @property {'Active'|'Inactive'} status
 * @property {string} created_at
 * @property {string} updated_at
 */

export const GENDERS = ['Male', 'Female', 'Other'];
export const STATUSES = ['Active', 'Inactive'];
export const SEMESTERS = [
  { value: 1, label: 'Semester 1' },
  { value: 2, label: 'Semester 2' },
];
export const ACADEMIC_YEAR_MAX = 10;

export const STUDENT_ID_PATTERN = /^[A-Z0-9][A-Z0-9_\-/.]{0,19}$/;

export const EMPTY_STUDENT_FORM = {
  student_id: '',
  full_name_khmer: '',
  full_name_latin: '',
  gender: '',
  program: '',
  major: '',
  academic_year: '',
  semester: '',
  status: 'Active',
};

export const TABLE_COLUMNS = [
  { key: 'student_id', label: 'Student ID' },
  { key: 'full_name_khmer', label: 'Full Name (Khmer)' },
  { key: 'full_name_latin', label: 'Full Name (Latin)' },
  { key: 'gender', label: 'Gender' },
  { key: 'program', label: 'Program' },
  { key: 'major', label: 'Major' },
  { key: 'academic_year', label: 'Year' },
  { key: 'semester', label: 'Semester' },
  { key: 'status', label: 'Status' },
];

const collapse = (value) => String(value ?? '').replace(/\s+/g, ' ').trim();

/** Convert an API student into form values (strings for inputs). */
export function studentToForm(student) {
  return {
    student_id: student.student_id ?? '',
    full_name_khmer: student.full_name_khmer ?? '',
    full_name_latin: student.full_name_latin ?? '',
    gender: student.gender ?? '',
    program: student.program ?? '',
    major: student.major ?? '',
    academic_year: student.academic_year == null ? '' : String(student.academic_year),
    semester: student.semester == null ? '' : String(student.semester),
    status: student.status ?? 'Active',
  };
}

/** Normalize form values into the JSON payload the API expects. */
export function formToPayload(values) {
  const optional = (v) => collapse(v) || null;
  return {
    student_id: collapse(values.student_id).toUpperCase(),
    full_name_khmer: optional(values.full_name_khmer),
    full_name_latin: collapse(values.full_name_latin),
    gender: values.gender,
    program: optional(values.program),
    major: optional(values.major),
    academic_year: values.academic_year === '' ? null : Number(values.academic_year),
    semester: values.semester === '' ? null : Number(values.semester),
    status: values.status || 'Active',
  };
}

/** @returns {Record<string, string>} field -> error message (empty object when valid) */
export function validateStudentForm(values) {
  const errors = {};
  const id = collapse(values.student_id).toUpperCase();
  if (!id) errors.student_id = 'Student ID is required.';
  else if (id.length > 20) errors.student_id = 'Student ID must be at most 20 characters.';
  else if (!STUDENT_ID_PATTERN.test(id))
    errors.student_id = "Use letters, digits, '-', '_', '/' or '.' only.";

  const latin = collapse(values.full_name_latin);
  if (!latin) errors.full_name_latin = 'Full name in Latin is required.';
  else if (latin.length > 150) errors.full_name_latin = 'Must be at most 150 characters.';

  if (collapse(values.full_name_khmer).length > 150)
    errors.full_name_khmer = 'Must be at most 150 characters.';

  if (!GENDERS.includes(values.gender)) errors.gender = 'Select a gender.';

  if (collapse(values.program).length > 100) errors.program = 'Must be at most 100 characters.';
  if (collapse(values.major).length > 150) errors.major = 'Must be at most 150 characters.';

  if (values.academic_year !== '') {
    const year = Number(values.academic_year);
    if (!Number.isInteger(year) || year < 1 || year > ACADEMIC_YEAR_MAX)
      errors.academic_year = `Enter a whole number from 1 to ${ACADEMIC_YEAR_MAX}.`;
  }

  if (values.semester !== '' && !['1', '2'].includes(String(values.semester)))
    errors.semester = 'Select Semester 1 or Semester 2.';

  if (!STATUSES.includes(values.status)) errors.status = 'Select a status.';

  return errors;
}

export function semesterLabel(semester) {
  return semester ? `Semester ${semester}` : '—';
}

export function formatDateTime(iso) {
  if (!iso) return '—';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(iso),
  );
}
