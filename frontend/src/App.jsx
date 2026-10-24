import { BrowserRouter, Route, Routes } from 'react-router-dom';
import ToastProvider from './components/ToastProvider';
import AppLayout from './layouts/AppLayout';
import AttendancePage from './pages/AttendancePage';
import DashboardPage from './pages/DashboardPage';
import NotFoundPage from './pages/NotFoundPage';
import SettingsPage from './pages/SettingsPage';
import StudentDetailPage from './pages/StudentDetailPage';
import StudentsPage from './pages/StudentsPage';

export default function App() {
  return (
    <ToastProvider>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="students" element={<StudentsPage />} />
            <Route path="students/:id" element={<StudentDetailPage />} />
            <Route path="attendance" element={<AttendancePage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  );
}
