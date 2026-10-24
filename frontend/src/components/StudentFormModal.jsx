import { useEffect, useId, useRef, useState } from 'react';
import { AlertCircle, Loader2 } from 'lucide-react';
import Modal from './Modal';
import { useToast } from '../hooks/useToast';
import { studentService } from '../services/studentService';
import {
  ACADEMIC_YEAR_MAX,
  EMPTY_STUDENT_FORM,
  GENDERS,
  SEMESTERS,
  STATUSES,
  formToPayload,
  studentToForm,
  validateStudentForm,
} from '../types/student';

function Field({ id, label, required, error, hint, children }) {
  return (
    <div>
      <label htmlFor={id} className="field-label">
        {label}
        {required && (
          <span className="ml-0.5 text-red-600" aria-hidden="true">
            *
          </span>
        )}
      </label>
      {children}
      {error ? (
        <p id={`${id}-error`} className="field-error">
          {error}
        </p>
      ) : (
        hint && (
          <p id={`${id}-hint`} className="mt-1 text-xs text-secondary">
            {hint}
          </p>
        )
      )}
    </div>
  );
}

/**
 * Add / edit student dialog. Pass `student` to edit; omit it to create.
 * `filterOptions` provides suggestions for program and major.
 */
export default function StudentFormModal({ open, student, filterOptions, onClose, onSaved }) {
  const isEdit = Boolean(student);
  const toast = useToast();
  const formId = useId();
  const formRef = useRef(null);
  const [values, setValues] = useState(EMPTY_STUDENT_FORM);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setValues(student ? studentToForm(student) : EMPTY_STUDENT_FORM);
      setErrors({});
      setFormError('');
      setSubmitting(false);
    }
  }, [open, student]);

  const fid = (name) => `${formId}-${name}`;

  const setField = (name) => (event) => {
    const { value } = event.target;
    setValues((v) => ({ ...v, [name]: value }));
    if (errors[name]) setErrors((e) => ({ ...e, [name]: undefined }));
  };

  const inputProps = (name) => ({
    id: fid(name),
    name,
    value: values[name],
    onChange: setField(name),
    'aria-invalid': errors[name] ? 'true' : 'false',
    'aria-describedby': errors[name] ? `${fid(name)}-error` : `${fid(name)}-hint`,
    className: 'field-input',
    disabled: submitting,
  });

  const focusFirstError = () => {
    setTimeout(() => formRef.current?.querySelector('[aria-invalid="true"]')?.focus(), 0);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (submitting) return; // guards against double submission

    const clientErrors = validateStudentForm(values);
    if (Object.keys(clientErrors).length) {
      setErrors(clientErrors);
      setFormError('Please correct the highlighted fields.');
      focusFirstError();
      return;
    }

    setSubmitting(true);
    setFormError('');
    try {
      const payload = formToPayload(values);
      const saved = isEdit
        ? await studentService.update(student.id, {
            ...payload,
            expected_updated_at: student.updated_at,
          })
        : await studentService.create(payload);
      toast.success(
        isEdit
          ? `${saved.full_name_latin} (${saved.student_id}) was updated.`
          : `${saved.full_name_latin} (${saved.student_id}) was registered.`,
        isEdit ? 'Student updated' : 'Student added',
      );
      onSaved?.(saved);
    } catch (err) {
      const fieldErrors = err.fieldErrors || {};
      setErrors(fieldErrors);
      setFormError(err.message);
      toast.error(err.message, isEdit ? 'Update failed' : 'Could not add student');
      if (Object.keys(fieldErrors).length) focusFirstError();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={submitting ? undefined : onClose}
      size="lg"
      title={isEdit ? 'Edit student' : 'Add student'}
      description={
        isEdit
          ? `Update the record for ${student.student_id}.`
          : 'Register a new student. Fields marked * are required.'
      }
      footer={
        <>
          <button type="button" className="btn-secondary" onClick={onClose} disabled={submitting}>
            Cancel
          </button>
          <button type="submit" form={formId} className="btn-primary" disabled={submitting}>
            {submitting && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
            {isEdit ? 'Save changes' : 'Add student'}
          </button>
        </>
      }
    >
      <form id={formId} ref={formRef} onSubmit={handleSubmit} noValidate>
        {formError && (
          <div
            role="alert"
            className="mb-4 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{formError}</span>
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field
            id={fid('student_id')}
            label="Student ID"
            required
            error={errors.student_id}
            hint="Up to 20 characters. Leading zeros are kept."
          >
            <input
              {...inputProps('student_id')}
              maxLength={20}
              autoComplete="off"
              autoFocus
              placeholder="e.g. E20240001"
            />
          </Field>

          <Field id={fid('gender')} label="Gender" required error={errors.gender}>
            <select {...inputProps('gender')}>
              <option value="">Select gender</option>
              {GENDERS.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </Field>

          <Field id={fid('full_name_khmer')} label="Full Name (Khmer)" error={errors.full_name_khmer}>
            <input {...inputProps('full_name_khmer')} lang="km" maxLength={150} placeholder="ឈ្មោះពេញ" />
          </Field>

          <Field id={fid('full_name_latin')} label="Full Name (Latin)" required error={errors.full_name_latin}>
            <input {...inputProps('full_name_latin')} maxLength={150} placeholder="e.g. Sok Sophea" />
          </Field>

          <Field id={fid('program')} label="Program" error={errors.program}>
            <input
              {...inputProps('program')}
              list={fid('program-options')}
              maxLength={100}
              placeholder="e.g. Bachelor"
            />
            <datalist id={fid('program-options')}>
              {filterOptions?.programs?.map((p) => <option key={p} value={p} />)}
            </datalist>
          </Field>

          <Field id={fid('major')} label="Major" error={errors.major}>
            <input
              {...inputProps('major')}
              list={fid('major-options')}
              maxLength={150}
              placeholder="e.g. Computer Science"
            />
            <datalist id={fid('major-options')}>
              {filterOptions?.majors?.map((m) => <option key={m} value={m} />)}
            </datalist>
          </Field>

          <Field
            id={fid('academic_year')}
            label="Academic Year"
            error={errors.academic_year}
            hint={`Year of study, 1–${ACADEMIC_YEAR_MAX}.`}
          >
            <input
              {...inputProps('academic_year')}
              type="number"
              inputMode="numeric"
              min={1}
              max={ACADEMIC_YEAR_MAX}
              step={1}
              placeholder="e.g. 2"
            />
          </Field>

          <Field id={fid('semester')} label="Semester" error={errors.semester}>
            <select {...inputProps('semester')}>
              <option value="">Not set</option>
              {SEMESTERS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </Field>

          <Field id={fid('status')} label="Status" required error={errors.status}>
            <select {...inputProps('status')}>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </Field>
        </div>
      </form>
    </Modal>
  );
}
