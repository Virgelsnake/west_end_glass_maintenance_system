import { useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";
import client from "../../api/client";
import { toast } from "sonner";
import {
  Wrench, LogOut, AlertCircle, Loader2, ChevronRight, Clock,
} from "lucide-react";
import { format, isPast } from "date-fns";

const STATUS_STYLES = {
  open: "bg-red-100 text-red-700",
  in_progress: "bg-amber-100 text-amber-700",
  closed: "bg-emerald-100 text-emerald-700",
};
const CATEGORY_STYLES = {
  repair: "bg-orange-100 text-orange-700",
  installation: "bg-blue-100 text-blue-700",
  maintenance: "bg-slate-100 text-slate-600",
  emergency: "bg-red-100 text-red-800",
  inspection: "bg-purple-100 text-purple-700",
};

export default function TechTicketList() {
  const { techUser, logoutTech } = useAuth();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const res = await client.get("/tech/my-tickets");
      setTickets(res.data);
    } catch {
      toast.error("Failed to load tickets");
    } finally {
      setLoading(false);
    }
  }, []);

  useAutoRefresh(load, 30000);

  const openTickets = tickets.filter((t) => t.status === "open");
  const inProgressTickets = tickets.filter((t) => t.status === "in_progress");

  return (
    <div className="min-h-svh bg-slate-50">
      {/* Top bar */}
      <header className="sticky top-0 z-10 flex items-center justify-between bg-slate-900 px-4 py-3 shadow-md">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500">
            <Wrench size={16} className="text-white" />
          </div>
          <div>
            <p className="text-xs font-bold text-white leading-none">West End Glass</p>
            <p className="text-[10px] text-slate-400">{techUser?.name}</p>
          </div>
        </div>
        <button
          onClick={logoutTech}
          className="flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800"
        >
          <LogOut size={13} /> Sign Out
        </button>
      </header>

      <main className="max-w-lg mx-auto p-4 space-y-5">
        {loading ? (
          <div className="space-y-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-24 rounded-2xl bg-slate-200 animate-pulse" />
            ))}
          </div>
        ) : (
          <>
            {/* In Progress */}
            {inProgressTickets.length > 0 && (
              <section>
                <h2 className="mb-2 text-xs font-bold uppercase tracking-wider text-amber-700">In Progress ({inProgressTickets.length})</h2>
                <div className="space-y-3">
                  {inProgressTickets.map((t) => <TicketCard key={t._id} ticket={t} />)}
                </div>
              </section>
            )}

            {/* Open */}
            {openTickets.length > 0 && (
              <section>
                <h2 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500">Open ({openTickets.length})</h2>
                <div className="space-y-3">
                  {openTickets.map((t) => <TicketCard key={t._id} ticket={t} />)}
                </div>
              </section>
            )}

            {tickets.length === 0 && (
              <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center">
                <p className="text-slate-400 text-sm">No open tickets assigned to you.</p>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}

function TicketCard({ ticket }) {
  const completedSteps = (ticket.steps || []).filter((s) => s.completed).length;
  const totalSteps = (ticket.steps || []).length;
  const progressPct = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;
  const isOverdue =
    ticket.due_date && ticket.status !== "closed" && isPast(new Date(ticket.due_date));

  return (
    <Link
      to={`/tech/tickets/${ticket._id}`}
      className="block rounded-2xl border border-slate-200 bg-white shadow-sm p-4 hover:shadow-md transition-shadow active:scale-[0.99]"
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">{ticket.machine_id}</code>
            {ticket.category && (
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${CATEGORY_STYLES[ticket.category] || "bg-slate-100 text-slate-600"}`}>
                {ticket.category}
              </span>
            )}
          </div>
          <p className="font-semibold text-slate-900 text-sm leading-snug truncate">{ticket.title}</p>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STATUS_STYLES[ticket.status]}`}>
            {ticket.status?.replace("_", " ")}
          </span>
          <ChevronRight size={16} className="text-slate-300" />
        </div>
      </div>

      {totalSteps > 0 && (
        <div className="mb-3">
          <div className="flex justify-between text-xs text-slate-400 mb-1">
            <span>{completedSteps}/{totalSteps} steps</span>
            <span>{progressPct}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
            <div
              className={`h-1.5 rounded-full ${progressPct === 100 ? "bg-emerald-500" : "bg-blue-600"}`}
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      )}

      {ticket.due_date && (
        <p className={`flex items-center gap-1 text-xs ${isOverdue ? "text-red-600 font-semibold" : "text-slate-400"}`}>
          {isOverdue && <AlertCircle size={11} />}
          <Clock size={11} />
          {isOverdue ? "OVERDUE — " : ""}
          {format(new Date(ticket.due_date), "MMM d, yyyy")}
        </p>
      )}
    </Link>
  );
}
