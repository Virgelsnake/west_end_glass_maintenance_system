import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import AppLayout from "./components/AppLayout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Tickets from "./pages/Tickets";
import TicketDetail from "./pages/TicketDetail";
import Users from "./pages/Users";
import Machines from "./pages/Machines";
import AuditLog from "./pages/AuditLog";
import Admins from "./pages/Admins";
import Dailys from "./pages/Dailys";
import Files from "./pages/Files";
import SettingsPage from "./pages/SettingsPage";
import TechLogin from "./pages/tech/TechLogin";
import TechTicketList from "./pages/tech/TechTicketList";
import TechTicketDetail from "./pages/tech/TechTicketDetail";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster position="top-right" richColors closeButton />
        <Routes>
          {/* Public */}
          <Route path="/login" element={<Login />} />
          <Route path="/tech/login" element={<TechLogin />} />

          {/* Admin portal — uses AppLayout (sidebar) */}
          <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/tickets" element={<Tickets />} />
            <Route path="/tickets/:id" element={<TicketDetail />} />
            <Route path="/users" element={<Users />} />
            <Route path="/machines" element={<Machines />} />
            <Route path="/dailys" element={<Dailys />} />
            <Route path="/files" element={<Files />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/audit" element={<AuditLog />} />
            <Route
              path="/admin/admins"
              element={
                <ProtectedRoute requiredRole="super_admin">
                  <Admins />
                </ProtectedRoute>
              }
            />
          </Route>

          {/* Technician portal */}
          <Route
            path="/tech/tickets"
            element={<ProtectedRoute techPortal><TechTicketList /></ProtectedRoute>}
          />
          <Route
            path="/tech/tickets/:id"
            element={<ProtectedRoute techPortal><TechTicketDetail /></ProtectedRoute>}
          />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

