import { useState, useCallback } from "react";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import client from "../api/client";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";
import {
  Plus, Pencil, Trash2, Play,
  Loader2, X, CalendarClock, AlertCircle, Clock, User,
  ToggleLeft, ToggleRight,
} from "lucide-react";
import StepEditor from "../components/StepEditor";

// ── API helpers ───────────────────────────────────────────────────────────────
export const getDailys = () => client.get("/dailys");
export const createDaily = (data) => client.post("/dailys", data);
export const updateDaily = (id, data) => client.patch(`/dailys/${id}`, data);
export const deleteDaily = (id) => client.delete(`/dailys/${id}`);
export const triggerDaily = (id) => client.post(`/dailys/${id}/trigger`);

// ── Main page ─────────────────────────────────────────────────────────────────
export default function Dailys() {
  const { role } = useAuth();
  const canEdit = role === "super_admin" || role === "dispatcher";

  const [templates, setTemplates] = useState([]);
  const [machines, setMachines] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  const [modalOpen, setModalOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null); // null = create mode
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [triggering, setTriggering] = useState(null);

  const load = useCallback(async () => {
    try {
      const [tRes, mRes, uRes] = await Promise.all([
        getDailys(),
        client.get("/machines"),
        client.get("/users?active=true"),
      ]);
      setTemplates(tRes.data);
      setMachines(mRes.data);
      setUsers(uRes.data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useAutoRefresh(load, 30000);

  async function handleToggleActive(t) {
    try {
      await updateDaily(t._id, { active: !t.active });
      toast.success(`"${t.title}" ${!t.active ? "enabled" : "disabled"}`);
      load();
    } catch {
      toast.error("Failed to update");
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    try {
      await deleteDaily(deleteTarget._id);
      toast.success("Daily template deleted");
      setDeleteTarget(null);
      load();
    } catch {
      toast.error("Failed to delete");
    }
  }

  async function handleTrigger(t) {
    setTriggering(t._id);
    try {
      await triggerDaily(t._id);
      toast.success(`Daily ticket created for ${t.machine_name || t.machine_id}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to trigger daily");
    } finally {
      setTriggering(null);
    }
  }

  function openCreate() {
    setEditTarget(null);
    setModalOpen(true);
  }

  function openEdit(t) {
    setEditTarget(t);
    setModalOpen(true);
  }

  async function handleSave(payload) {
    try {
      if (editTarget) {
        await updateDaily(editTarget._id, payload);
        toast.success("Template updated");
      } else {
        await createDaily(payload);
        toast.success("Daily template created");
      }
      setModalOpen(false);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Save failed");
    }
  }

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Daily Checks</h1>
          <p className="text-sm text-slate-500">
            {templates.length} template{templates.length !== 1 ? "s" : ""} — auto-creates tickets on schedule
          </p>
        </div>
        {canEdit && (
          <button
            onClick={openCreate}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
          >
            <Plus size={16} /> New Daily
          </button>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-16 text-slate-400">
          <Loader2 size={24} className="animate-spin mr-2" /> Loading…
        </div>
      )}

      {/* Empty */}
      {!loading && templates.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-2">
          <CalendarClock size={36} />
          <p className="text-sm">No daily templates yet. Click "New Daily" to create one.</p>
        </div>
      )}

      {/* Template cards */}
      {!loading && templates.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-2 xl:grid-cols-3">
          {templates.map((t) => (
            <TemplateCard
              key={t._id}
              template={t}
              canEdit={canEdit}
              triggering={triggering === t._id}
              onEdit={() => openEdit(t)}
              onDelete={() => setDeleteTarget(t)}
              onTrigger={() => handleTrigger(t)}
              onToggleActive={() => handleToggleActive(t)}
            />
          ))}
        </div>
      )}

      {/* Edit / Create modal */}
      {modalOpen && (
        <TemplateModal
          template={editTarget}
          machines={machines}
          users={users}
          onSave={handleSave}
          onClose={() => setModalOpen(false)}
        />
      )}

      {/* Delete confirm */}
      {deleteTarget && (
        <DeleteConfirmModal
          template={deleteTarget}
          onConfirm={handleDelete}
          onClose={() => setDeleteTarget(null)}
        />
      )}
    </div>
  );
}

// ── Template card ─────────────────────────────────────────────────────────────
function TemplateCard({ template: t, canEdit, triggering, onEdit, onDelete, onTrigger, onToggleActive }) {
  return (
    <div className={`rounded-xl border bg-white shadow-sm p-5 space-y-3 ${t.active ? "border-slate-200" : "border-slate-200 opacity-60"}`}>
      {/* Title + active badge */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold text-slate-800 text-sm leading-snug">{t.title}</h3>
          <p className="text-xs text-slate-500 mt-0.5">{t.machine_id}</p>
        </div>
        <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${t.active ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-500"}`}>
          {t.active ? "Active" : "Inactive"}
        </span>
      </div>

      {/* Meta row */}
      <div className="flex flex-wrap gap-3 text-xs text-slate-500">
        <span className="flex items-center gap-1">
          <Clock size={12} />
          {t.schedule_time} UTC
        </span>
        <span className="flex items-center gap-1">
          <User size={12} />
          {t.assignee_name || t.assigned_to}
        </span>
        <span className="flex items-center gap-1">
          <CalendarClock size={12} />
          {t.items?.length || 0} check item{t.items?.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Section preview */}
      {t.items && t.items.length > 0 && (
        <div className="rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500 max-h-20 overflow-hidden">
          {[...new Set(t.items.map((i) => i.section_name))].join(" · ")}
        </div>
      )}

      {/* Actions */}
      {canEdit && (
        <div className="flex items-center gap-2 pt-1">
          <button
            onClick={onTrigger}
            disabled={triggering}
            title="Create today's ticket now"
            className="flex items-center gap-1 rounded-md bg-emerald-50 px-2.5 py-1.5 text-xs font-medium text-emerald-700 hover:bg-emerald-100 disabled:opacity-50"
          >
            {triggering ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
            Trigger
          </button>
          <button
            onClick={onEdit}
            className="flex items-center gap-1 rounded-md bg-blue-50 px-2.5 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-100"
          >
            <Pencil size={12} /> Edit
          </button>
          <button
            onClick={onToggleActive}
            title={t.active ? "Disable" : "Enable"}
            className="ml-auto rounded-md p-1.5 text-slate-400 hover:bg-slate-100"
          >
            {t.active ? <ToggleRight size={16} className="text-green-600" /> : <ToggleLeft size={16} />}
          </button>
          <button
            onClick={onDelete}
            className="rounded-md p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
          >
            <Trash2 size={14} />
          </button>
        </div>
      )}
    </div>
  );
}

// ── Create / Edit modal ───────────────────────────────────────────────────────
function TemplateModal({ template, machines, users, onSave, onClose }) {
  const isEdit = !!template;

  const [machineId, setMachineId] = useState(template?.machine_id || "");
  const [title, setTitle] = useState(template?.title || "");
  const [assignedTo, setAssignedTo] = useState(template?.assigned_to || "");
  const [scheduleTime, setScheduleTime] = useState(template?.schedule_time || "00:00");
  const [active, setActive] = useState(template?.active ?? true);
  const [items, setItems] = useState(
    template?.items
      ? template.items.map((i) => ({ ...i, id: crypto.randomUUID() }))
      : []
  );
  const [saving, setSaving] = useState(false);

  // Auto-fill title when machine selected in create mode
  function handleMachineChange(mid) {
    setMachineId(mid);
    if (!isEdit && !title) {
      const m = machines.find((m) => m.machine_id === mid);
      if (m) setTitle(`${m.name} Daily Checklist`);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!machineId || !title || !assignedTo) {
      toast.error("Machine, title, and assignee are required");
      return;
    }
    setSaving(true);
    const serializedItems = items.map(({ id, ...rest }, i) => ({ ...rest, item_index: i }));
    await onSave({ machine_id: machineId, title, assigned_to: assignedTo, schedule_time: scheduleTime, active, items: serializedItems });
    setSaving(false);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 p-4 overflow-y-auto">
      <div className="relative w-full max-w-2xl rounded-2xl bg-white shadow-xl my-8">
        {/* Modal header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <h2 className="text-base font-semibold text-slate-900">
            {isEdit ? "Edit Daily Template" : "New Daily Template"}
          </h2>
          <button onClick={onClose} className="rounded-md p-1 text-slate-400 hover:bg-slate-100">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="px-6 py-5 space-y-4">
            {/* Machine + Title */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Machine *</label>
                <select
                  value={machineId}
                  onChange={(e) => handleMachineChange(e.target.value)}
                  required
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select machine…</option>
                  {machines.map((m) => (
                    <option key={m.machine_id} value={m.machine_id}>{m.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Title *</label>
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                  placeholder="e.g. Arrisor Machine Daily Checklist"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Assignee + Time + Active */}
            <div className="grid grid-cols-3 gap-4">
              <div className="col-span-2">
                <label className="block text-xs font-medium text-slate-600 mb-1">Assign To *</label>
                <select
                  value={assignedTo}
                  onChange={(e) => setAssignedTo(e.target.value)}
                  required
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select technician…</option>
                  {users.map((u) => (
                    <option key={u.phone_number} value={u.phone_number}>{u.name} ({u.phone_number})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Time (UTC)</label>
                <input
                  type="time"
                  value={scheduleTime}
                  onChange={(e) => setScheduleTime(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Active toggle */}
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setActive(!active)}
                className="flex items-center gap-2 text-sm font-medium text-slate-700"
              >
                {active
                  ? <ToggleRight size={22} className="text-green-600" />
                  : <ToggleLeft size={22} className="text-slate-400" />}
                {active ? "Enabled — will run on schedule" : "Disabled — will not run"}
              </button>
            </div>

            {/* Items list */}
            <StepEditor
              items={items}
              onChange={setItems}
              withSections
              label="Check Items"
            />
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-2 border-t border-slate-200 px-6 py-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-4 py-2 text-sm text-slate-600 hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {saving && <Loader2 size={14} className="animate-spin" />}
              {isEdit ? "Save Changes" : "Create Template"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Delete confirm ─────────────────────────────────────────────────────────────
function DeleteConfirmModal({ template, onConfirm, onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-sm rounded-2xl bg-white shadow-xl p-6 space-y-4">
        <div className="flex items-center gap-3 text-red-600">
          <AlertCircle size={20} />
          <h2 className="font-semibold">Delete Template</h2>
        </div>
        <p className="text-sm text-slate-600">
          Delete <strong>"{template.title}"</strong>? This will also unschedule its daily job.
          Tickets already created will not be affected.
        </p>
        <div className="flex justify-end gap-2 pt-2">
          <button onClick={onClose} className="rounded-lg px-4 py-2 text-sm text-slate-600 hover:bg-slate-100">
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
