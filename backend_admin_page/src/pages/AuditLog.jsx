import { useState, useCallback } from "react";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import client from "../api/client";
import { Search, Filter, RefreshCw } from "lucide-react";
import { format, formatDistanceToNow } from "date-fns";

const EVENT_COLORS = {
  ticket_created: "bg-blue-100 text-blue-700",
  ticket_updated: "bg-amber-100 text-amber-700",
  ticket_closed: "bg-emerald-100 text-emerald-700",
  step_completed: "bg-purple-100 text-purple-700",
  user_added: "bg-teal-100 text-teal-700",
  login: "bg-slate-100 text-slate-600",
};

export default function AuditLog() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [eventFilter, setEventFilter] = useState("");

  const load = useCallback(async () => {
    try {
      const res = await client.get("/audit?limit=200");
      setLogs(res.data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useAutoRefresh(load, 30000);

  const eventTypes = [...new Set(logs.map((l) => l.event))].sort();

  const filtered = logs.filter((l) => {
    const matchEvent = !eventFilter || l.event === eventFilter;
    const q = search.toLowerCase();
    const matchQ =
      !q ||
      l.actor?.toLowerCase().includes(q) ||
      l.event?.toLowerCase().includes(q) ||
      JSON.stringify(l.details || {}).toLowerCase().includes(q);
    return matchEvent && matchQ;
  });

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Audit Log</h1>
          <p className="text-sm text-slate-500">{filtered.length} events</p>
        </div>
        <button onClick={load} className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50">
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
        <div className="relative flex-1 min-w-[180px]">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            className="w-full rounded-lg border border-slate-200 py-1.5 pl-8 pr-3 text-sm focus:border-blue-500 focus:outline-none"
            placeholder="Search actor or event…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-1.5">
          <Filter size={13} className="text-slate-400" />
          <select
            className="rounded-lg border border-slate-200 px-2 py-1.5 text-xs focus:border-blue-500 focus:outline-none"
            value={eventFilter}
            onChange={(e) => setEventFilter(e.target.value)}
          >
            <option value="">All Events</option>
            {eventTypes.map((t) => (
              <option key={t} value={t}>{t ? t.replace(/_/g, " ") : "—"}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        {loading ? (
          <div className="space-y-0">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="flex gap-4 px-5 py-3 border-b border-slate-50">
                {[...Array(4)].map((_, j) => (
                  <div key={j} className="h-4 flex-1 animate-pulse rounded bg-slate-100" />
                ))}
              </div>
            ))}
          </div>
        ) : (
          <div className="divide-y divide-slate-50">
            {filtered.length === 0 ? (
              <p className="py-12 text-center text-sm text-slate-400">No events found.</p>
            ) : filtered.map((log, i) => (
              <div key={i} className="flex items-start gap-4 px-5 py-3 hover:bg-slate-50 transition-colors">
                <div className="flex-shrink-0 pt-0.5">
                  <span
                    className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium capitalize whitespace-nowrap ${
                      EVENT_COLORS[log.event] || "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {log.event?.replace(/_/g, " ")}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-700">
                    <span className="font-medium text-slate-900">{log.actor}</span>
                    {log.details && Object.keys(log.details).length > 0 && (
                      <span className="ml-1 text-slate-400 text-xs">
                        — {Object.entries(log.details).map(([k, v]) => `${k}: ${v}`).join(", ")}
                      </span>
                    )}
                  </p>
                </div>
                <div className="flex-shrink-0 text-right">
                  <p className="text-xs text-slate-400">
                    {formatDistanceToNow(new Date(log.timestamp), { addSuffix: true })}
                  </p>
                  <p className="text-xs text-slate-300">
                    {format(new Date(log.timestamp), "MMM d, HH:mm")}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
