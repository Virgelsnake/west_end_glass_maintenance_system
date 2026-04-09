import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  LayoutDashboard, Ticket, Users, Cpu, ScrollText,
  LogOut, ShieldCheck, X, Wrench, CalendarClock,
} from "lucide-react";

const ROLE_COLORS = {
  super_admin: "bg-amber-100 text-amber-800",
  dispatcher: "bg-blue-100 text-blue-800",
  viewer: "bg-slate-200 text-slate-600",
};

const ROLE_LABELS = {
  super_admin: "Super Admin",
  dispatcher: "Dispatcher",
  viewer: "Viewer",
};

const NAV = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/tickets", icon: Ticket, label: "Tickets" },
  { to: "/users", icon: Users, label: "Technicians" },
  { to: "/machines", icon: Cpu, label: "Machines" },
  { to: "/dailys", icon: CalendarClock, label: "Daily Checks" },
  { to: "/audit", icon: ScrollText, label: "Audit Log" },
];

export default function Sidebar({ onClose }) {
  const { username, fullName, role, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  const displayName = fullName || username;
  const initials = displayName
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <nav className="flex h-full w-60 flex-col bg-slate-900 text-slate-100">
      {/* Brand */}
      <div className="flex items-center justify-between px-5 py-5">
        <div>
          <div className="flex items-center gap-2">
            <Wrench size={18} className="text-amber-400" />
            <span className="text-sm font-bold tracking-wide text-white">West End Glass</span>
          </div>
          <span className="text-xs text-slate-400">Maintenance System</span>
        </div>
        <button
          onClick={onClose}
          className="rounded-md p-1 text-slate-400 hover:bg-slate-700 md:hidden"
        >
          <X size={16} />
        </button>
      </div>

      <div className="mx-4 mb-4 border-t border-slate-700" />

      {/* Nav links */}
      <ul className="flex-1 space-y-0.5 px-3">
        {NAV.map(({ to, icon: Icon, label }) => (
          <li key={to}>
            <NavLink
              to={to}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-blue-600 text-white"
                    : "text-slate-300 hover:bg-slate-800 hover:text-white"
                }`
              }
            >
              <Icon size={17} />
              {label}
            </NavLink>
          </li>
        ))}
        {role === "super_admin" && (
          <li>
            <NavLink
              to="/admin/admins"
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-blue-600 text-white"
                    : "text-slate-300 hover:bg-slate-800 hover:text-white"
                }`
              }
            >
              <ShieldCheck size={17} />
              Admin Accounts
            </NavLink>
          </li>
        )}
      </ul>

      {/* User footer */}
      <div className="mx-4 mb-4 border-t border-slate-700" />
      <div className="px-4 pb-5">
        <div className="flex items-center gap-3 rounded-lg bg-slate-800 px-3 py-3">
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">
            {initials}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-white">{displayName}</p>
            <span className={`inline-block rounded-full px-1.5 py-0.5 text-xs font-medium ${ROLE_COLORS[role] || ROLE_COLORS.viewer}`}>
              {ROLE_LABELS[role] || role}
            </span>
          </div>
          <button
            onClick={handleLogout}
            className="rounded-md p-1 text-slate-400 hover:text-red-400"
            title="Sign out"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </nav>
  );
}
