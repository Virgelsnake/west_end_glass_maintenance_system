import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children, requiredRole, techPortal = false }) {
  const { isAuthenticated, role, isTechAuthenticated } = useAuth();

  if (techPortal) {
    return isTechAuthenticated ? children : <Navigate to="/tech/login" replace />;
  }

  if (!isAuthenticated) return <Navigate to="/login" replace />;

  if (requiredRole) {
    const hierarchy = { super_admin: 3, dispatcher: 2, viewer: 1 };
    const userLevel = hierarchy[role] || 0;
    const required = hierarchy[requiredRole] || 0;
    if (userLevel < required) return <Navigate to="/dashboard" replace />;
  }

  return children;
}
