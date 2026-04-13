import { useState, useCallback } from "react";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import client from "../api/client";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";
import { Plus, Trash2, Tag, Loader2 } from "lucide-react";

export default function SettingsPage() {
  const { role } = useAuth();
  const canEdit = role === "super_admin" || role === "dispatcher";

  const [types, setTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [adding, setAdding] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await client.get("/ticket-types");
      setTypes(res.data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useAutoRefresh(load, 60000);

  async function handleAdd(e) {
    e.preventDefault();
    if (!newName.trim()) return;
    setAdding(true);
    try {
      await client.post("/ticket-types", { name: newName.trim(), description: newDesc.trim() || null });
      toast.success(`Ticket type "${newName.trim()}" created`);
      setNewName("");
      setNewDesc("");
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create ticket type");
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await client.delete(`/ticket-types/${deleteTarget._id}`);
      toast.success(`Ticket type "${deleteTarget.name}" deleted`);
      setDeleteTarget(null);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to delete ticket type");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="p-6 space-y-8 max-w-3xl">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Settings</h1>
        <p className="text-sm text-slate-500">Manage system settings</p>
      </div>

      {/* Ticket Types section */}
      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <Tag size={18} className="text-slate-500" />
          <h2 className="text-base font-semibold text-slate-800">Ticket Types</h2>
        </div>
        <p className="text-sm text-slate-500">
          Define custom ticket types for non-machine work (e.g., Break Fix, Customer Measurement).
          These allow creating tickets without a machine, with location and contact details instead.
        </p>

        {/* Add form */}
        {canEdit && (
          <form onSubmit={handleAdd} className="rounded-xl border border-slate-200 bg-white shadow-sm p-4 space-y-3">
            <p className="text-sm font-medium text-slate-700">Add Ticket Type</p>
            <div className="flex flex-col sm:flex-row gap-3">
              <input
                type="text"
                placeholder="Name (e.g. Break Fix)"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                maxLength={80}
                required
                className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                type="text"
                placeholder="Description (optional)"
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                maxLength={200}
                className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="submit"
                disabled={adding || !newName.trim()}
                className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap"
              >
                {adding ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                Add Type
              </button>
            </div>
          </form>
        )}

        {/* List */}
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          {loading ? (
            <div className="space-y-0">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="flex gap-4 px-5 py-4 border-b border-slate-50">
                  {[...Array(3)].map((_, j) => (
                    <div key={j} className="h-4 flex-1 animate-pulse rounded bg-slate-100" />
                  ))}
                </div>
              ))}
            </div>
          ) : types.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-slate-400">
              <Tag size={32} className="mb-2 opacity-30" />
              <p className="text-sm">No ticket types defined yet</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-xs font-medium text-slate-500 bg-slate-50">
                  <th className="px-5 py-3 text-left">Name</th>
                  <th className="px-5 py-3 text-left">Description</th>
                  <th className="px-5 py-3 text-left">Created</th>
                  {canEdit && <th className="px-5 py-3 text-left">Actions</th>}
                </tr>
              </thead>
              <tbody>
                {types.map((t) => (
                  <tr key={t._id} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors">
                    <td className="px-5 py-3 font-medium text-slate-800">{t.name}</td>
                    <td className="px-5 py-3 text-slate-500">{t.description || <span className="text-slate-300">—</span>}</td>
                    <td className="px-5 py-3 text-slate-400">
                      {t.created_at ? new Date(t.created_at).toLocaleDateString() : "—"}
                    </td>
                    {canEdit && (
                      <td className="px-5 py-3">
                        <button
                          onClick={() => setDeleteTarget(t)}
                          className="flex items-center gap-1 rounded px-2 py-1 text-xs text-red-500 hover:bg-red-50 hover:text-red-700 transition-colors"
                        >
                          <Trash2 size={13} /> Delete
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {/* Delete confirmation dialog */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="rounded-2xl bg-white p-6 shadow-xl max-w-sm w-full mx-4 space-y-4">
            <h3 className="text-base font-semibold text-slate-900">Delete Ticket Type</h3>
            <p className="text-sm text-slate-600">
              Delete <strong>{deleteTarget.name}</strong>? This cannot be undone.
              If any tickets use this type, deletion will be blocked.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteTarget(null)}
                disabled={deleting}
                className="rounded-lg px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50"
              >
                {deleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
