import { useCallback, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  addMonths,
  eachDayOfInterval,
  endOfMonth,
  format,
  getDay,
  isSameMonth,
  startOfMonth,
  subMonths,
} from "date-fns";
import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import client from "../api/client";
import { useAutoRefresh } from "../hooks/useAutoRefresh";

const WEEK_DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const STATUS_STYLES = {
  open: "bg-red-100 text-red-700",
  in_progress: "bg-amber-100 text-amber-700",
  closed: "bg-emerald-100 text-emerald-700",
};

function getTicketDate(ticket) {
  const raw = ticket.scheduled_date || ticket.due_date || ticket.created_at;
  if (!raw) return null;
  const parsed = new Date(raw);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function getMachineIdentifier(ticket) {
  return ticket.machine_id || ticket.location || "";
}

function hasPositivePriority(ticket) {
  return typeof ticket.priority === "number" && ticket.priority > 0;
}

function statusRank(status) {
  if (status === "open" || status === "in_progress") return 0;
  return 1;
}

export default function Calendar() {
  const [tickets, setTickets] = useState([]);
  const [users, setUsers] = useState([]);
  const [ticketTypes, setTicketTypes] = useState([]);
  const [month, setMonth] = useState(startOfMonth(new Date()));
  const [statusFilter, setStatusFilter] = useState("");
  const [ownerFilter, setOwnerFilter] = useState("");
  const [machineFilter, setMachineFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [ticketTypeFilter, setTicketTypeFilter] = useState("");

  const load = useCallback(async () => {
    try {
      const [ticketsRes, usersRes, ticketTypesRes] = await Promise.all([
        client.get("/tickets"),
        client.get("/users"),
        client.get("/ticket-types"),
      ]);
      setTickets(ticketsRes.data || []);
      setUsers(usersRes.data || []);
      setTicketTypes(ticketTypesRes.data || []);
    } catch {
      toast.error("Failed to load calendar data");
    }
  }, []);

  useAutoRefresh(load, 30000);

  const userMap = useMemo(() => {
    const map = {};
    users.forEach((user) => {
      map[user.phone_number] = user.name;
    });
    return map;
  }, [users]);

  const ownerOptions = useMemo(() => {
    const values = new Set();
    tickets.forEach((ticket) => {
      if (ticket.assigned_to) values.add(ticket.assigned_to);
    });
    return [...values].sort();
  }, [tickets]);

  const machineOptions = useMemo(() => {
    const values = new Set();
    tickets.forEach((ticket) => {
      const machine = getMachineIdentifier(ticket);
      if (machine) values.add(machine);
    });
    return [...values].sort();
  }, [tickets]);

  const priorityOptions = useMemo(() => {
    const values = new Set();
    tickets.forEach((ticket) => {
      if (hasPositivePriority(ticket)) values.add(ticket.priority);
    });
    return [...values].sort((a, b) => b - a);
  }, [tickets]);

  const ticketTypeMap = useMemo(() => {
    const map = {};
    ticketTypes.forEach((ticketType) => {
      map[ticketType._id] = ticketType.name;
    });
    return map;
  }, [ticketTypes]);

  const monthStart = startOfMonth(month);
  const monthEnd = endOfMonth(month);
  const monthDays = eachDayOfInterval({ start: monthStart, end: monthEnd });
  const leadingEmptyCells = Array.from({ length: getDay(monthStart) });
  const ticketsByDay = (() => {
    const map = {};
    tickets
      .filter((ticket) => {
        const ticketDate = getTicketDate(ticket);
        if (!ticketDate || !isSameMonth(ticketDate, monthStart)) return false;
        if (statusFilter && ticket.status !== statusFilter) return false;
        if (ownerFilter && ticket.assigned_to !== ownerFilter) return false;
        if (machineFilter && getMachineIdentifier(ticket) !== machineFilter) return false;
        if (priorityFilter && (!hasPositivePriority(ticket) || String(ticket.priority) !== priorityFilter)) return false;
        if (ticketTypeFilter && ticket.ticket_type_id !== ticketTypeFilter) return false;
        return true;
      })
      .sort((a, b) => {
        const activeSort = statusRank(a.status) - statusRank(b.status);
        if (activeSort !== 0) return activeSort;
        const prioritySort = Number(b.priority || 0) - Number(a.priority || 0);
        if (prioritySort !== 0) return prioritySort;
        return (a.title || "").localeCompare(b.title || "");
      })
      .forEach((ticket) => {
        const ticketDate = getTicketDate(ticket);
        const key = format(ticketDate, "yyyy-MM-dd");
        if (!map[key]) map[key] = [];
        map[key].push(ticket);
      });
    return map;
  })();

  return (
    <div className="p-6 space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <CalendarDays size={22} className="text-slate-700" />
          <h1 className="text-xl font-semibold text-slate-900">Calendar</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="rounded-lg border border-slate-200 bg-white p-2 text-slate-600 hover:bg-slate-50"
            onClick={() => setMonth((m) => subMonths(m, 1))}
            aria-label="Previous month"
          >
            <ChevronLeft size={16} />
          </button>
          <div className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 min-w-[160px] text-center">
            {format(monthStart, "MMMM yyyy")}
          </div>
          <button
            className="rounded-lg border border-slate-200 bg-white p-2 text-slate-600 hover:bg-slate-50"
            onClick={() => setMonth((m) => addMonths(m, 1))}
            aria-label="Next month"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-3">
        <select className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="closed">Closed</option>
        </select>

        <select className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" value={ownerFilter} onChange={(e) => setOwnerFilter(e.target.value)}>
          <option value="">All owners</option>
          {ownerOptions.map((owner) => (
            <option key={owner} value={owner}>{userMap[owner] || owner}</option>
          ))}
        </select>

        <select className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" value={machineFilter} onChange={(e) => setMachineFilter(e.target.value)}>
          <option value="">All machines</option>
          {machineOptions.map((machine) => (
            <option key={machine} value={machine}>{machine}</option>
          ))}
        </select>

        <select className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)}>
          <option value="">All priorities</option>
          {priorityOptions.map((priority) => (
            <option key={priority} value={String(priority)}>Priority {priority}</option>
          ))}
        </select>

        <select className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" value={ticketTypeFilter} onChange={(e) => setTicketTypeFilter(e.target.value)}>
          <option value="">All ticket types</option>
          {ticketTypes.map((ticketType) => (
            <option key={ticketType._id} value={ticketType._id}>{ticketType.name}</option>
          ))}
        </select>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
        <div className="grid grid-cols-7 bg-slate-50 border-b border-slate-200">
          {WEEK_DAYS.map((day) => (
            <div key={day} className="px-2 py-2 text-xs font-semibold text-slate-500 uppercase">{day}</div>
          ))}
        </div>

        <div className="grid grid-cols-7 auto-rows-[160px]">
          {leadingEmptyCells.map((_, idx) => (
            <div key={`empty-${idx}`} className="border-r border-b border-slate-100 bg-slate-50/50" />
          ))}

          {monthDays.map((day) => {
            const key = format(day, "yyyy-MM-dd");
            const dayTickets = ticketsByDay[key] || [];
            const dayParams = new URLSearchParams({ date_from: key, date_to: key });
            if (statusFilter) dayParams.set("status", statusFilter);
            if (ownerFilter) dayParams.set("assigned_to", ownerFilter);
            if (machineFilter) dayParams.set("machine", machineFilter);
            if (ticketTypeFilter) dayParams.set("ticket_type_id", ticketTypeFilter);
            return (
              <div key={key} className="min-h-40 border-r border-b border-slate-100 p-2 overflow-y-auto">
                <Link to={`/tickets?${dayParams.toString()}`} className="mb-2 inline-block text-xs font-semibold text-slate-600 hover:text-blue-700 hover:underline">
                  {format(day, "d")}
                </Link>
                <div className="space-y-1.5">
                  {dayTickets.map((ticket) => (
                    <Link
                      key={ticket._id}
                      to={`/tickets/${ticket._id}`}
                      className="block rounded-md border border-slate-200 bg-slate-50 p-1.5 hover:border-blue-300 hover:bg-blue-50"
                    >
                      <p className="truncate text-xs font-semibold text-slate-800">{ticket.title || "Untitled Ticket"}</p>
                      <div className="mt-1 flex items-center gap-1 flex-wrap">
                        <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium capitalize ${STATUS_STYLES[ticket.status] || "bg-slate-100 text-slate-600"}`}>
                          {(ticket.status || "open").replace("_", " ")}
                        </span>
                        <span className="rounded-full bg-slate-200 px-1.5 py-0.5 text-[10px] font-medium text-slate-700">
                          {userMap[ticket.assigned_to] || ticket.assigned_to || "Unassigned"}
                        </span>
                        {getMachineIdentifier(ticket) && (
                          <span className="rounded-full bg-blue-100 px-1.5 py-0.5 text-[10px] font-medium text-blue-700">
                            {getMachineIdentifier(ticket)}
                          </span>
                        )}
                        {ticket.ticket_type_id && (
                          <span className="rounded-full bg-indigo-100 px-1.5 py-0.5 text-[10px] font-medium text-indigo-700">
                            {ticketTypeMap[ticket.ticket_type_id] || "Custom"}
                          </span>
                        )}
                        {hasPositivePriority(ticket) && (
                          <span className="rounded-full bg-purple-100 px-1.5 py-0.5 text-[10px] font-medium text-purple-700">
                            P{ticket.priority}
                          </span>
                        )}
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
