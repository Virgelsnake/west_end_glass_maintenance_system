import { useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";
import client from "../../api/client";
import { toast } from "sonner";
import {
  ArrowLeft, CheckCircle2, Circle, Loader2, Camera, FileText, AlertCircle, Download,
} from "lucide-react";
import { format, isPast } from "date-fns";

const STATUS_STYLES = {
  open: "bg-red-100 text-red-700",
  in_progress: "bg-amber-100 text-amber-700",
  closed: "bg-emerald-100 text-emerald-700",
};

export default function TechTicketDetail() {
  const { id } = useParams();
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeStep, setActiveStep] = useState(null);
  const [noteText, setNoteText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await client.get(`/tech/my-tickets`);
      const found = res.data.find((t) => t._id === id);
      if (found) setTicket(found);
    } catch {
      toast.error("Failed to load ticket");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useAutoRefresh(load, 30000);

  async function completeStep(stepIdx, type) {
    setSubmitting(true);
    try {
      if (type === "note") {
        if (!noteText.trim()) { toast.error("Please add a note before completing."); setSubmitting(false); return; }
        await client.post(`/tech/tickets/${id}/steps/${stepIdx}/note`, { text: noteText.trim() });
        setNoteText("");
      } else {
        await client.post(`/tech/tickets/${id}/steps/${stepIdx}/complete`);
      }
      setActiveStep(null);
      toast.success("Step completed");
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to complete step");
    } finally {
      setSubmitting(false);
    }
  }

  async function uploadPhoto(stepIdx, file) {
    setSubmitting(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      await client.post(`/tech/tickets/${id}/steps/${stepIdx}/photo`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setActiveStep(null);
      toast.success("Photo uploaded and step completed");
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Upload failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function downloadManual(manualId, filename) {
    try {
      const res = await client.get(`/manuals/tech/${manualId}/file`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename || "document";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Failed to download document");
    }
  }

  if (loading) {
    return (
      <div className="min-h-svh bg-slate-50 flex items-center justify-center">
        <Loader2 size={32} className="animate-spin text-blue-600" />
      </div>
    );
  }
  if (!ticket) {
    return (
      <div className="min-h-svh bg-slate-50 flex items-center justify-center p-4">
        <div className="text-center">
          <p className="text-slate-500 mb-3">Ticket not found.</p>
          <Link to="/tech/tickets" className="text-blue-600 underline text-sm">Back to My Tickets</Link>
        </div>
      </div>
    );
  }

  const completedSteps = (ticket.steps || []).filter((s) => s.completed).length;
  const totalSteps = (ticket.steps || []).length;
  const progressPct = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;
  const isOverdue = ticket.due_date && ticket.status !== "closed" && isPast(new Date(ticket.due_date));

  return (
    <div className="min-h-svh bg-slate-50">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-slate-900 px-4 py-3 shadow-md">
        <Link to="/tech/tickets" className="flex items-center gap-1.5 text-slate-300 text-sm hover:text-white mb-1">
          <ArrowLeft size={15} /> My Tickets
        </Link>
        <h1 className="text-white font-bold text-base leading-snug line-clamp-2">{ticket.title}</h1>
        <div className="flex items-center gap-2 mt-1.5">
          <code className="rounded bg-slate-700 px-1.5 py-0.5 text-xs text-slate-300">
            {ticket.machine_id || ticket.location || "—"}
          </code>
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STATUS_STYLES[ticket.status]}`}>
            {ticket.status?.replace("_", " ")}
          </span>
          {isOverdue && (
            <span className="flex items-center gap-1 text-xs font-semibold text-red-400">
              <AlertCircle size={11} /> OVERDUE
            </span>
          )}
        </div>
      </header>

      <main className="max-w-lg mx-auto p-4 space-y-4 pb-10">
        {/* Progress */}
        {totalSteps > 0 && (
          <div className="rounded-2xl bg-white border border-slate-200 shadow-sm p-4">
            <div className="flex justify-between text-sm mb-2">
              <span className="font-semibold text-slate-700">{completedSteps}/{totalSteps} steps complete</span>
              <span className={`font-bold ${progressPct === 100 ? "text-emerald-600" : "text-blue-600"}`}>{progressPct}%</span>
            </div>
            <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
              <div
                className={`h-2 rounded-full transition-all duration-500 ${progressPct === 100 ? "bg-emerald-500" : "bg-blue-600"}`}
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>
        )}

        {/* Due date */}
        {ticket.due_date && (
          <div className={`rounded-2xl border px-4 py-3 text-sm font-medium flex items-center gap-2 ${isOverdue ? "border-red-200 bg-red-50 text-red-700" : "border-slate-200 bg-white text-slate-600"}`}>
            {isOverdue && <AlertCircle size={15} />}
            Due: {format(new Date(ticket.due_date), "EEEE, MMMM d, yyyy")}
          </div>
        )}

        {/* Description */}
        {ticket.description && (
          <div className="rounded-2xl border border-slate-200 bg-white shadow-sm px-4 py-3">
            <p className="text-xs font-semibold text-slate-500 mb-1 uppercase tracking-wider">Notes</p>
            <p className="text-sm text-slate-700 leading-relaxed">{ticket.description}</p>
          </div>
        )}

        {/* Steps */}
        <div className="space-y-3">
          {(ticket.steps || []).map((step, i) => (
            <div
              key={i}
              className={`rounded-2xl border bg-white shadow-sm overflow-hidden transition-all ${
                step.completed ? "border-emerald-200 opacity-70" : "border-slate-200"
              }`}
            >
              <div className="flex items-center gap-3 px-4 py-3">
                {step.completed ? (
                  <CheckCircle2 size={22} className="text-emerald-500 flex-shrink-0" />
                ) : (
                  <Circle size={22} className="text-slate-300 flex-shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-medium ${step.completed ? "line-through text-slate-400" : "text-slate-900"}`}>
                    {i + 1}. {step.label}
                  </p>
                  <p className="text-xs text-slate-400 capitalize mt-0.5">{step.completion_type?.replace("_", " ")}</p>
                  {step.note && (
                    <p className="text-xs text-blue-600 mt-1 italic">&ldquo;{step.note}&rdquo;</p>
                  )}
                  {(step.completion_type === "manual" || step.completion_type === "attachment") && step.manual_id && (
                    <button
                      onClick={() => downloadManual(step.manual_id, step.manual_title)}
                      className="mt-1.5 flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-medium"
                    >
                      <Download size={11} />
                      {step.manual_title || "Download Reference Document"}
                    </button>
                  )}
                </div>
                {!step.completed && (
                  <button
                    onClick={() => setActiveStep(activeStep === i ? null : i)}
                    className={`flex-shrink-0 rounded-xl px-3 py-1.5 text-xs font-semibold transition-colors ${
                      activeStep === i
                        ? "bg-slate-200 text-slate-700"
                        : "bg-blue-600 text-white hover:bg-blue-700"
                    }`}
                  >
                    {activeStep === i ? "Close" : "Complete"}
                  </button>
                )}
              </div>

              {/* Completion UI */}
              {activeStep === i && !step.completed && (
                <div className="px-4 pb-4 pt-0 border-t border-slate-100 space-y-3">
                  {step.completion_type === "confirmation" || step.completion_type === "manual" || step.completion_type === "attachment" ? (
                    <button
                      onClick={() => completeStep(i, "confirmation")}
                      disabled={submitting}
                      className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 py-2.5 text-sm font-bold text-white hover:bg-emerald-700 disabled:opacity-60"
                    >
                      {submitting ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle2 size={16} />}
                      Mark as Done
                    </button>
                  ) : step.completion_type === "note" ? (
                    <div className="space-y-2">
                      <textarea
                        className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none resize-none"
                        rows={3}
                        placeholder="Add your note here…"
                        value={noteText}
                        onChange={(e) => setNoteText(e.target.value)}
                      />
                      <button
                        onClick={() => completeStep(i, "note")}
                        disabled={submitting || !noteText.trim()}
                        className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 py-2.5 text-sm font-bold text-white hover:bg-emerald-700 disabled:opacity-60"
                      >
                        {submitting ? <Loader2 size={16} className="animate-spin" /> : <FileText size={16} />}
                        Submit Note & Complete
                      </button>
                    </div>
                  ) : step.completion_type === "photo" ? (
                    <label className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-blue-600 py-2.5 text-sm font-bold text-white hover:bg-blue-700">
                      {submitting ? <Loader2 size={16} className="animate-spin" /> : <Camera size={16} />}
                      {submitting ? "Uploading…" : "Take / Upload Photo"}
                      <input
                        type="file"
                        accept="image/*"
                        capture="environment"
                        className="hidden"
                        onChange={(e) => {
                          if (e.target.files?.[0]) uploadPhoto(i, e.target.files[0]);
                        }}
                      />
                    </label>
                  ) : null}
                </div>
              )}
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
