import { useState, useCallback, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import client from "../api/client";
import { toast } from "sonner";
import {
  ArrowLeft, CheckCircle2, Circle, AlertCircle, Loader2,
  MessageSquare, ImageIcon, ListTodo, Clock, User, Tag,
  ChevronDown, MapPin, Phone, FileText, Download,
} from "lucide-react";
import { format, formatDistanceToNow, isPast } from "date-fns";

const STATUS_OPTIONS = ["open", "in_progress", "closed"];
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

export default function TicketDetail() {
  const { id } = useParams();
  const [ticket, setTicket] = useState(null);
  const [messages, setMessages] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("steps");
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [showStatusMenu, setShowStatusMenu] = useState(false);

  const load = useCallback(async () => {
    try {
      const [tRes, mRes, uRes] = await Promise.all([
        client.get(`/tickets/${id}`),
        client.get(`/tickets/${id}/messages`).catch(() => ({ data: [] })),
        client.get("/users?active=true").catch(() => ({ data: [] })),
      ]);
      setTicket(tRes.data);
      setMessages(mRes.data);
      setUsers(uRes.data);
    } catch {
      toast.error("Failed to load ticket");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useAutoRefresh(load, 30000);

  async function updateStatus(newStatus) {
    setUpdatingStatus(true);
    setShowStatusMenu(false);
    try {
      await client.patch(`/tickets/${id}`, { status: newStatus });
      toast.success("Status updated");
      load();
    } catch {
      toast.error("Failed to update status");
    } finally {
      setUpdatingStatus(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 size={28} className="animate-spin text-blue-600" />
      </div>
    );
  }
  if (!ticket) {
    return (
      <div className="p-8 text-center text-slate-500">
        Ticket not found.{" "}
        <Link to="/tickets" className="text-blue-600 underline">
          Back to Tickets
        </Link>
      </div>
    );
  }

  const assignedUser = users.find((u) => u.phone_number === ticket.assigned_to);
  const secondaryUser = users.find(
    (u) => u.phone_number === ticket.secondary_assigned_to
  );
  const completedSteps = (ticket.steps || []).filter((s) => s.completed).length;
  const totalSteps = (ticket.steps || []).length;
  const progressPct =
    totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;
  const isOverdue =
    ticket.due_date &&
    ticket.status !== "closed" &&
    isPast(new Date(ticket.due_date));

  return (
    <div className="p-6 space-y-5">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <Link to="/tickets" className="flex items-center gap-1 hover:text-blue-600">
          <ArrowLeft size={14} /> Tickets
        </Link>
        <span>/</span>
        <span className="font-medium text-slate-900 truncate max-w-xs">
          {ticket.title}
        </span>
      </div>

      {/* Title row */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">{ticket.title}</h1>
          <div className="mt-1 flex items-center gap-2 flex-wrap">
            <code className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
              {ticket.machine_id || ticket.location || "—"}
            </code>
            {ticket.category && (
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${
                  CATEGORY_STYLES[ticket.category] || "bg-slate-100 text-slate-600"
                }`}
              >
                {ticket.category}
              </span>
            )}
            <PriorityBadge priority={ticket.priority} />
          </div>
        </div>

        {/* Status selector */}
        <div className="relative">
          <button
            onClick={() => setShowStatusMenu((v) => !v)}
            disabled={updatingStatus}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-semibold transition-opacity ${
              STATUS_STYLES[ticket.status]
            } ${updatingStatus ? "opacity-60" : ""}`}
          >
            {updatingStatus && (
              <Loader2 size={13} className="animate-spin" />
            )}
            {ticket.status
              ?.replace("_", " ")
              .replace(/\b\w/g, (c) => c.toUpperCase())}
            <ChevronDown size={13} />
          </button>
          {showStatusMenu && (
            <div className="absolute right-0 top-full mt-1 z-10 min-w-[140px] rounded-lg border border-slate-200 bg-white shadow-lg py-1">
              {STATUS_OPTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => updateStatus(s)}
                  className={`flex w-full items-center px-3 py-2 text-sm capitalize hover:bg-slate-50 ${
                    ticket.status === s ? "font-semibold text-blue-600" : "text-slate-700"
                  }`}
                >
                  {s.replace("_", " ")}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 2-col layout */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Meta sidebar */}
        <div className="md:col-span-1 rounded-xl border border-slate-200 bg-white shadow-sm p-5 space-y-3 text-sm">
          <InfoRow
            icon={<User size={14} />}
            label="Primary Tech"
            value={assignedUser?.name || ticket.assigned_to || "Unassigned"}
          />
          {secondaryUser && (
            <InfoRow
              icon={<User size={14} />}
              label="Secondary Tech"
              value={secondaryUser.name || ticket.secondary_assigned_to}
            />
          )}
          <InfoRow
            icon={<Clock size={14} />}
            label="Due Date"
            value={
              ticket.due_date ? (
                <span
                  className={
                    isOverdue
                      ? "text-red-600 font-semibold"
                      : "text-slate-700"
                  }
                >
                  {isOverdue && (
                    <AlertCircle size={12} className="inline mr-1" />
                  )}
                  {format(new Date(ticket.due_date), "MMM d, yyyy")}
                </span>
              ) : (
                "—"
              )
            }
          />
          <InfoRow
            icon={<ListTodo size={14} />}
            label="Steps"
            value={`${completedSteps} / ${totalSteps} complete`}
          />
          <InfoRow
            icon={<Tag size={14} />}
            label="Created"
            value={
              ticket.created_at
                ? formatDistanceToNow(new Date(ticket.created_at), {
                    addSuffix: true,
                  })
                : "—"
            }
          />
          {ticket.description && (
            <div className="pt-2 border-t border-slate-100 text-xs text-slate-500 leading-relaxed">
              {ticket.description}
            </div>
          )}
          {ticket.location && (
            <InfoRow
              icon={<MapPin size={14} />}
              label="Location"
              value={ticket.location}
            />
          )}
          {ticket.contact_name && (
            <InfoRow
              icon={<User size={14} />}
              label="Contact"
              value={ticket.contact_name}
            />
          )}
          {ticket.contact_number && (
            <InfoRow
              icon={<Phone size={14} />}
              label="Phone"
              value={ticket.contact_number}
            />
          )}
          {ticket.contact_address && (
            <InfoRow
              icon={<MapPin size={14} />}
              label="Address"
              value={ticket.contact_address}
            />
          )}
        </div>

        {/* Main panel */}
        <div className="md:col-span-2 space-y-4">
          {totalSteps > 0 && (
            <div className="rounded-xl border border-slate-200 bg-white shadow-sm p-4">
              <div className="flex justify-between text-xs text-slate-500 mb-2">
                <span>
                  {completedSteps} of {totalSteps} steps complete
                </span>
                <span className="font-semibold text-slate-700">
                  {progressPct}%
                </span>
              </div>
              <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                <div
                  className={`h-2 rounded-full transition-all duration-500 ${
                    progressPct === 100 ? "bg-emerald-500" : "bg-blue-600"
                  }`}
                  style={{ width: `${progressPct}%` }}
                />
              </div>
            </div>
          )}

          <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
            <div className="flex border-b border-slate-100">
              {[
                { key: "steps", icon: <ListTodo size={14} />, label: "Steps" },
                {
                  key: "messages",
                  icon: <MessageSquare size={14} />,
                  label: `Messages (${messages.length})`,
                },
                { key: "photos", icon: <ImageIcon size={14} />, label: "Photos" },
              ].map((t) => (
                <button
                  key={t.key}
                  onClick={() => setTab(t.key)}
                  className={`flex items-center gap-1.5 px-5 py-3 text-sm font-medium transition-colors ${
                    tab === t.key
                      ? "border-b-2 border-blue-600 text-blue-600"
                      : "text-slate-500 hover:text-slate-700"
                  }`}
                >
                  {t.icon} {t.label}
                </button>
              ))}
            </div>
            <div className="p-5">
              {tab === "steps" && <StepsTab steps={ticket.steps || []} />}
              {tab === "messages" && (
                <MessagesTab messages={messages} users={users} />
              )}
              {tab === "photos" && <PhotosTab ticketId={id} ticket={ticket} />}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function InfoRow({ icon, label, value }) {
  return (
    <div className="flex items-start gap-2">
      <span className="mt-0.5 flex-shrink-0 text-slate-400">{icon}</span>
      <div>
        <div className="text-xs text-slate-400">{label}</div>
        <div className="text-slate-700">{value}</div>
      </div>
    </div>
  );
}

function PriorityBadge({ priority }) {
  const p = parseInt(priority, 10);
  if (p >= 8)
    return (
      <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-bold text-red-700">
        P{p} HIGH
      </span>
    );
  if (p >= 5)
    return (
      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-bold text-amber-700">
        P{p} MED
      </span>
    );
  return (
    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
      P{p}
    </span>
  );
}

function StepsTab({ steps }) {
  const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  if (!steps.length)
    return <p className="text-sm text-slate-400">No steps defined.</p>;
  return (
    <ol className="space-y-3">
      {steps.map((step, i) => (
        <li key={i} className="flex items-start gap-3">
          {step.completed ? (
            <CheckCircle2 size={18} className="text-emerald-500 flex-shrink-0 mt-0.5" />
          ) : (
            <Circle size={18} className="text-slate-300 flex-shrink-0 mt-0.5" />
          )}
          <div className="flex-1">
            <p
              className={`text-sm ${
                step.completed ? "line-through text-slate-400" : "text-slate-700"
              }`}
            >
              {step.label}
            </p>
            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
              <span className="text-xs text-slate-400 capitalize">
                {step.completion_type?.replace("_", " ")}
              </span>
              {step.note_text && (
                <span className="text-xs text-blue-600 italic">
                  &ldquo;{step.note_text}&rdquo;
                </span>
              )}
              {step.completion_type === "attachment" && step.manual_id && (
                <button
                  type="button"
                  onClick={async () => {
                    try {
                      const res = await client.get(`/manuals/${step.manual_id}/file`, { responseType: "blob" });
                      const url = URL.createObjectURL(res.data);
                      window.open(url, "_blank", "noreferrer");
                    } catch { toast.error("Could not open document."); }
                  }}
                  className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-medium"
                >
                  <Download size={11} />
                  {step.manual_title || "Reference Document"}
                </button>
              )}
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}

function MessagesTab({ messages, users }) {
  if (!messages.length)
    return <p className="text-sm text-slate-400">No messages yet.</p>;
  return (
    <div className="space-y-3">
      {messages.map((msg) => {
        const u = users.find((u) => u.phone_number === msg.sender);
        const initials = u?.name?.[0]?.toUpperCase() || "?";
        return (
          <div
            key={msg._id}
            className={`flex gap-2 ${
              msg.direction === "outbound" ? "flex-row-reverse" : ""
            }`}
          >
            <div className="flex-shrink-0 w-7 h-7 rounded-full bg-slate-200 flex items-center justify-center text-xs font-semibold text-slate-600">
              {initials}
            </div>
            <div
              className={`max-w-sm rounded-2xl px-3 py-2 text-sm ${
                msg.direction === "outbound"
                  ? "bg-blue-600 text-white"
                  : "bg-slate-100 text-slate-800"
              }`}
            >
              <p>{msg.content}</p>
              <p
                className={`text-xs mt-1 ${
                  msg.direction === "outbound"
                    ? "text-blue-200"
                    : "text-slate-400"
                }`}
              >
                {msg.timestamp
                  ? formatDistanceToNow(new Date(msg.timestamp), { addSuffix: true })
                  : "unknown time"}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/** Format an ISO/UTC datetime string for display in tiles. */
function formatPhotoDate(isoString) {
  if (!isoString) return null;
  try {
    const d = new Date(isoString);
    return d.toLocaleString(undefined, {
      year: "numeric", month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return null;
  }
}

/** Metadata strip rendered uniformly below every photo tile. */
function PhotoMetaStrip({ meta, fallbackDate }) {
  const dateLabel = meta?.datetime_taken
    ? formatPhotoDate(meta.datetime_taken)
    : fallbackDate
    ? formatPhotoDate(fallbackDate)
    : null;

  const hasGps = meta?.latitude != null && meta?.longitude != null;
  const mapsUrl = hasGps
    ? `https://www.google.com/maps?q=${meta.latitude},${meta.longitude}`
    : null;

  if (!dateLabel && !hasGps) return null;

  return (
    <div className="px-2 py-1.5 flex items-center justify-between gap-1 bg-slate-50 border-t border-slate-200">
      {dateLabel ? (
        <span className="text-xs text-slate-500 truncate leading-tight">{dateLabel}</span>
      ) : (
        <span />
      )}
      {hasGps && (
        <a
          href={mapsUrl}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="shrink-0 inline-flex items-center gap-0.5 text-xs font-medium text-blue-600 hover:text-blue-800 bg-blue-50 px-1.5 py-0.5 rounded"
          title={`${meta.latitude}, ${meta.longitude}`}
        >
          📍 GPS
        </a>
      )}
    </div>
  );
}

function Lightbox({ src, onClose, metadata, fallbackDate }) {
  useEffect(() => {
    if (!src) return;
    function onKey(e) { if (e.key === "Escape") onClose(); }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [src, onClose]);

  if (!src) return null;

  const dateLabel = metadata?.datetime_taken
    ? formatPhotoDate(metadata.datetime_taken)
    : fallbackDate
    ? formatPhotoDate(fallbackDate)
    : null;
  const hasGps = metadata?.latitude != null && metadata?.longitude != null;
  const mapsUrl = hasGps
    ? `https://www.google.com/maps?q=${metadata.latitude},${metadata.longitude}`
    : null;
  const cameraLabel = [metadata?.camera_make, metadata?.camera_model].filter(Boolean).join(" ") || null;
  const showStrip = dateLabel || hasGps || cameraLabel;

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black/85"
      onClick={onClose}
    >
      <button
        onClick={onClose}
        className="absolute top-4 right-4 text-white bg-black/40 rounded-full w-9 h-9 flex items-center justify-center text-lg hover:bg-black/70"
      >
        ✕
      </button>
      <img
        src={src}
        alt="Enlarged"
        className="max-h-[85vh] max-w-[90vw] object-contain rounded-t-lg shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      />
      {showStrip && (
        <div
          className="max-w-[90vw] w-fit bg-black/70 text-white text-xs rounded-b-lg px-4 py-2 flex flex-wrap items-center gap-x-4 gap-y-1"
          onClick={(e) => e.stopPropagation()}
        >
          {dateLabel && <span>📅 {dateLabel}</span>}
          {cameraLabel && <span>📷 {cameraLabel}</span>}
          {hasGps && (
            <a
              href={mapsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-300 hover:text-blue-100 underline"
            >
              📍 {metadata.latitude.toFixed(5)}, {metadata.longitude.toFixed(5)}
            </a>
          )}
        </div>
      )}
    </div>
  );
}

function PhotosTab({ ticketId, ticket }) {
  const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  const [lightbox, setLightbox] = useState(null); // { src, metadata, fallbackDate }

  const refMetaMap = ticket?.reference_photo_metadata || {};

  const refPhotos = (ticket?.reference_photos || []).map((filename) => ({
    filename,
    url: `${API_BASE}/tickets/${ticketId}/photos/${encodeURIComponent(filename)}`,
    metadata: refMetaMap[filename] || null,
  }));

  const stepPhotos = (ticket?.steps || [])
    .filter((s) => s.photo_path)
    .map((s) => ({
      filename: s.photo_path,
      label: s.label,
      stepIndex: s.step_index,
      url: `${API_BASE}/tickets/${ticketId}/photos/${encodeURIComponent(s.photo_path.split("/").pop())}`,
      metadata: s.photo_metadata || null,
      fallbackDate: s.completed_at || null,
    }));

  if (!refPhotos.length && !stepPhotos.length)
    return <p className="text-sm text-slate-400">No photos attached.</p>;

  return (
    <div className="space-y-6">
      <Lightbox
        src={lightbox?.src}
        metadata={lightbox?.metadata}
        fallbackDate={lightbox?.fallbackDate}
        onClose={() => setLightbox(null)}
      />
      {refPhotos.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
            Reference Photos
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {refPhotos.map((p, i) => (
              <div
                key={i}
                className="rounded-lg overflow-hidden border border-slate-200 bg-white"
              >
                <button
                  type="button"
                  onClick={() => setLightbox({ src: p.url, metadata: p.metadata, fallbackDate: null })}
                  className="relative w-full focus:outline-none focus:ring-2 focus:ring-blue-400"
                >
                  <div className="aspect-square w-full overflow-hidden">
                    <img
                      src={p.url}
                      alt={`Reference ${i + 1}`}
                      className="w-full h-full object-cover hover:opacity-90 transition-opacity"
                    />
                  </div>
                  <span className="absolute top-1.5 left-1.5 bg-blue-600 text-white text-xs font-bold px-1.5 py-0.5 rounded">
                    REF
                  </span>
                </button>
                <PhotoMetaStrip meta={p.metadata} fallbackDate={null} />
              </div>
            ))}
          </div>
        </div>
      )}
      {stepPhotos.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
            Step Photos
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {stepPhotos.map((p, i) => (
              <div
                key={i}
                className="rounded-lg overflow-hidden border border-slate-200 bg-white"
              >
                <button
                  type="button"
                  onClick={() => setLightbox({ src: p.url, metadata: p.metadata, fallbackDate: p.fallbackDate })}
                  className="w-full focus:outline-none focus:ring-2 focus:ring-blue-400"
                >
                  <div className="aspect-square w-full overflow-hidden">
                    <img
                      src={p.url}
                      alt={`Step ${p.stepIndex}`}
                      className="w-full h-full object-cover hover:opacity-90 transition-opacity"
                    />
                  </div>
                </button>
                <div className="px-2 py-1 text-xs text-slate-600 font-medium truncate border-t border-slate-100">
                  Step {p.stepIndex + 1}: {p.label}
                </div>
                <PhotoMetaStrip meta={p.metadata} fallbackDate={p.fallbackDate} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
