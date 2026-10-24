import { createElement, useState } from 'react';
import { useToast } from './useToast';
import { studentService } from '../services/studentService';
import { formToPayload, studentToForm } from '../types/student';

/**
 * Confirm-then-run flow for deactivating (soft delete) or reactivating a student.
 * Returns `request(student)` to start the flow and props for <ConfirmDialog>.
 */
export function useStudentStatusToggle(onDone) {
  const toast = useToast();
  const [target, setTarget] = useState(null);
  const [busy, setBusy] = useState(false);

  const deactivating = target?.status === 'Active';

  const confirm = async () => {
    if (!target || busy) return;
    setBusy(true);
    try {
      const saved = deactivating
        ? await studentService.deactivate(target.id)
        : await studentService.update(target.id, {
            ...formToPayload(studentToForm(target)),
            status: 'Active',
            expected_updated_at: target.updated_at,
          });
      toast.success(
        `${saved.full_name_latin} (${saved.student_id}) is now ${saved.status.toLowerCase()}.`,
        deactivating ? 'Student deactivated' : 'Student reactivated',
      );
      setTarget(null);
      onDone?.(saved);
    } catch (err) {
      toast.error(err.message, deactivating ? 'Could not deactivate' : 'Could not reactivate');
    } finally {
      setBusy(false);
    }
  };

  const name = target ? `${target.full_name_latin} (${target.student_id})` : '';

  return {
    request: setTarget,
    dialogProps: {
      open: Boolean(target),
      busy,
      tone: deactivating ? 'danger' : 'primary',
      title: deactivating ? 'Deactivate student?' : 'Reactivate student?',
      confirmLabel: deactivating ? 'Deactivate' : 'Reactivate',
      message: deactivating
        ? createElement(
            'p',
            null,
            createElement('strong', { className: 'text-ink' }, name),
            ' will be marked as Inactive. The record is kept (not deleted) and can be reactivated at any time.',
          )
        : createElement(
            'p',
            null,
            createElement('strong', { className: 'text-ink' }, name),
            ' will be marked as Active again.',
          ),
      onConfirm: confirm,
      onCancel: () => !busy && setTarget(null),
    },
  };
}
