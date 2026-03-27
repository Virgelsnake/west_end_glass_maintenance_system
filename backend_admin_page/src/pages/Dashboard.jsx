import { useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import client from "../api/client";
import {
  Ticket, AlertCircle, CheckCircle2, Clock, TrendingUp,
  Activity, User, ArrowRight,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";

const AUDIT_ICONS = {
  ticket_created: { icon: Ticket, color: "text-blue-600", bg: "bg-blue-50" },
  ticket_updated: { icon: TrendingUp, color: "text-amber-600", bg: "bg-amber-50" },
  ticket_closed: { icon: CheckCircle2, color: "text-emerald-600", bg: "bg-emerald-50" },
  ticket_reopened: { icon: AlertCircle, color: "text-orange-600", bg: "bg-orange-50" },
  step_completed: { icon: CheckCircle2, color: "text-emerald-600", bg: "bg-emerald-50" },
  note_added: { icon: Activity, color: "text-blue-600", bg: "bg-blue-50" },
  photo_attached: { icon: Activity, color: "text-purple-600", bg: "bg-purple-50" },
  user_added: { icon: User, color: "text-blue-600", bg: "bg-blue-50" },
  user_deactivated: { icon: User, color: "text-red-600", bg: "bg-red-50" },
};

const PRIORITY_COLORS = {
  high: "bg-red-100 text-red-700",
  mid: "bg-amber-100 text-amber-700",
  low: "bg-slate-100 text-slate-600",
};

const STATUS_STYLES = {
  open: "bg-red-100 text-red-700",
  in_progress: "bg-amber-100 text-amber-700",
  closed: "bg-emerald-100 text-emerald-700",
};

function kpiLabel(p) {
  if (p >= 8) return "high";
  if (p >= 4) return "mid";
  return "low";
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [activeTickets, setActiveTickets] = useState([]);

  const load = useCallback(async () => {
    try {
      const [statsRes, openRes, ipRes] = await Promise.all([
        client.get("/dashboard/stats"),
        client.get("/tickets?status=open"),
        client.get("/tickets?status=in_progress"),
      ]);
      setStats(statsRes.data);
      const combined = [...ipRes.data, ...openRes.data]
        .sort((a, b) => b.priority - a.priority)
        .slice(0, 10);
      setActiveTickets(combined);
    } catch {
      // silently ignore polling errors
    }
  }, []);

  useAutoRefresh(load, 30000);

  const by = stats?.by_status ?? { open: 0, in_progress: 0, closed: 0 };
  const overdue = stats?.overdue_count ?? 0;
  const workload = stats?.tech_workload ?? [];
  const activity = stats?.recent_activity ?? [];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-sm text-slate-500">Live view — refreshes every 30 seconds</p>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard label="Open" value={by.open} icon={Ticket} color="border-red-400" iconColor="text-red-500" to="/tickets?status=open" />
        <KpiCard label="In Progress" value={by.in_progress} icon={Clock} color="border-amber-400" iconColor="text-amber-500" to="/tickets?status=in_progress" />
        <KpiCard label="Closed" value={by.closed} icon={CheckCircle2} color="border-emerald-400" iconColor="text-emerald-500" to="/tickets?status=closed" />
        <KpiCard label="Overdue" value={overdue} icon={AlertCircle} color="border-red-700" iconColor="text-red-700" to="/tickets" />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Active tickets — takes 2 cols */}
        <div className="lg:col-span-2 rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
            <h2 className="font-semibold text-slate-800">Active Tickets</h2>
            <Link to="/tickets" className="flex items-center gap-1 text-xs text-amber-600 hover:underline">
              View all <ArrowRight size={12} />
            </Link>
          </div>
          <div className="overflow-x-auto">
            {activeTickets.length === 0 ? (
              <p className="px-5 py-8 text-center text-sm text-slate-400">No active tickets right now.</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-xs font-medium text-slate-500">
                    <th className="px-5 py-3 text-left">Priority</th>
                    <th className="px-3 py-3 text-left">Machine</th>
                    <th className="px-3 py-3 text-left">Title</th>
                    <th className="px-3 py-3 text-left">Assigned</th>
                    <th className="px-3 py-3 text-left">Status</th>
                    <th className="px-3 py-3 text-left">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {activeTickets.map((t) => (
                    <tr key={t._id} className="border-b border-slate-50 hover:bg-slate-50">
                      <td className="px-5 py-3">
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-bold ${PRIORITY_COLORS[kpiLabel(t.priority)]}`}>
                          P{t.priority}
                        </span>
                      </td>
                      <td className="px-3 py-3">
                        <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-700">{t.machine_id}</code>
                      </td>
                      <td className="px-3 py-3 max-w-[200px]">
                        <Link to={`/tickets/${t._id}`} className="font-medium text-amber-600 hover:underline truncate block">
                          {t.title}
                        </Link>
                      </td>
                      <td className="px-3 py-3 text-slate-600">{t.assigned_to || "—"}</td>
                      <td className="px-3 py-3">
                        <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STATUS_STYLES[t.status]}`}>
                          {t.status?.replace("_", " ")}
                        </span>
                      </td>
                      <td className="px-3 py-3 text-slate-400 text-xs">
                        {t.created_at ? formatDistanceToNow(new Date(t.created_at), { addSuffix: true }) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Right column: workload + activity */}
        <div className="space-y-6">
          {/* Technician workload */}
          <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-100 px-5 py-4">
              <h2 className="font-semibold text-slate-800">Technician Workload</h2>
            </div>
            <div className="divide-y divide-slate-50">
              {workload.length === 0 ? (
                <p className="px-5 py-6 text-center text-sm text-slate-400">No active technicians.</p>
              ) : (
                workload.map((tech) => (
                  <div key={tech.phone} className="flex items-center justify-between px-5 py-3">
                    <div className="flex items-center gap-2.5">
                      <div className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">
                        {tech.name.charAt(0).toUpperCase()}
                      </div>
                      <span className="text-sm font-medium text-slate-700">{tech.name}</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-xs">
                      <span className="rounded-full bg-red-100 px-2 py-0.5 font-medium text-red-700">{tech.open} open</span>
                      <span className="rounded-full bg-amber-100 px-2 py-0.5 font-medium text-amber-700">{tech.in_progress} active</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Recent activity */}
          <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-100 px-5 py-4">
              <h2 className="font-semibold text-slate-800">Recent Activity</h2>
            </div>
            <ul className="divide-y divide-slate-50">
              {activity.slice(0, 6).map((a) => {
                const meta = AUDIT_ICONS[a.event] || { icon: Activity, color: "text-slate-500", bg: "bg-slate-50" };
                const Icon = meta.icon;
                return (
                  <li key={a._id} className="flex items-start gap-3 px-5 py-3">
                    <span className={`mt-0.5 flex-shrink-0 rounded-full p-1.5 ${meta.bg}`}>
                      <Icon size={13} className={meta.color} />
                    </span>
                    <div className="min-w-0">
                      <p className="text-xs font-medium text-slate-700 capitalize">{a.event?.replace(/_/g, " ")}</p>
                      <p className="text-xs text-slate-400">
                        {a.actor || "system"} — {a.timestamp ? formatDistanceToNow(new Date(a.timestamp), { addSuffix: true }) : "just now"}
                      </p>
                    </div>
                  </li>
                );
              })}
              {activity.length === 0 && (
                <li className="px-5 py-6 text-center text-sm text-slate-400">No activity yet.</li>
              )}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

function KpiCard({ label, value, icon: Icon, color, iconColor, to }) {
  return (
    <Link
      to={to}
      className={`flex items-center justify-between rounded-xl border-l-4 bg-white p-5 shadow-sm hover:shadow-md transition-shadow ${color}`}
    >
      <div>
        <p className="text-xs font-medium text-slate-500">{label}</p>
        <p className="mt-1 text-3xl font-bold text-slate-900">
          {value ?? <span className="inline-block h-8 w-10 animate-pulse rounded bg-slate-100" />}
        </p>
      </div>
      <div className={`rounded-full bg-slate-50 p-3 ${iconColor}`}>
        <Icon size={22} />
      </div>
    </Link>
  );
}


