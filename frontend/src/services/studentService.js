import { downloadFile, request } from './api';

/** All calls to the Student Management API live here. */
export const studentService = {
  list: (params) => request('/api/students', { params }),
  get: (id) => request(`/api/students/${id}`),
  create: (payload) => request('/api/students', { method: 'POST', json: payload }),
  update: (id, payload) => request(`/api/students/${id}`, { method: 'PUT', json: payload }),
  deactivate: (id) => request(`/api/students/${id}`, { method: 'DELETE' }),
  filterOptions: () => request('/api/students/filters'),

  importCsv: (file, { skipInvalid = false } = {}) => {
    const formData = new FormData();
    formData.append('file', file);
    return request('/api/students/import', {
      method: 'POST',
      formData,
      params: { skip_invalid: skipInvalid },
    });
  },

  exportCsv: (filters) => downloadFile('/api/students/export', filters, 'students.csv'),
};

export const dashboardService = {
  stats: () => request('/api/dashboard/stats'),
};

export const attendanceService = {
  scan: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return request('/api/attendance/scan', { method: 'POST', formData });
  },
  records: (params) => request('/api/attendance/records', { params }),
};

export const systemService = {
  health: () => request('/api/health'),
};
