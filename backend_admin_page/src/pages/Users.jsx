import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import client from "../api/client";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";
import {
  Plus, Search, KeyRound, AlertCircle, Loader2, X, Phone,
  ToggleLeft, ToggleRight, Ticket,
} from "lucide-react";

export default function Users() {
  const { role } = useAuth();
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [pinTarget, setPinTarget] = useState(null);
  const [filterActive, setFilterActive] = useState(true);

  const load = useCallback(async () => {
    try {
      const res = await client.get("/users");
      setUsers(res.data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useAutoRefresh(load, 30000);

  const filtered = users.filter((u) => {
    const matchActive = filterActive ? u.active !== false : true;
    const q = search.toLowerCase();
    const matchQ = !q || u.name?.toLowerCase().includes(q) || u.phone_number?.includes(q);
    return matchActive && matchQ;
  });

  async function handleAdd(payload) {
    try {
      await client.post("/users", payload);
      toast.success("Technician added");
      setShowAdd(false);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to add technician");
    }
  }

  async function toggleActive(user) {
    try {
      await client.patch(`/users/${user.phone_number}`, { active: !user.active });
      toast.success(`${user.name} ${!user.active ? "activated" : "deactivated"}`);
      load();
    } catch {
      toast.error("Failed to update status");
    }
  }

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Technicians</h1>
          <p className="text-sm text-slate-500">{filtered.length} technician{filtered.length !== 1 ? "s" : ""}</p>
        </div>
        {(role === "super_admin" || role === "dispatcher") && (
          <button
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
          >
            <Plus size={16} /> Add Technician
          </button>
        )}
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
        <div className="relative flex-1 min-w-[180px]">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            className="w-full rounded-lg border border-slate-200 py-1.5 pl-8 pr-3 text-sm focus:border-blue-500 focus:outline-none"
            placeholder="Search name or phone…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <button
          onClick={() => setFilterActive((v) => !v)}
          className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
            filterActive ? "border-blue-200 bg-blue-50 text-blue-700" : "border-slate-200 text-slate-600"
          }`}
        >
          {filterActive ? <ToggleRight size={14} /> : <ToggleLeft size={14} />}
          Active only
        </button>
      </div>

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-32 rounded-xl bg-slate-100 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {filtered.map((u) => (
            <div key={u.phone_number} className="rounded-xl border border-slate-200 bg-white shadow-sm p-5 flex flex-col gap-3">
              <button
                className="flex items-start justify-between text-left w-full hover:opacity-80 transition-opacity"
                onClick={() => navigate(`/tickets?assigned_to=${encodeURIComponent(u.phone_number)}`)}
                title="View tickets for this technician"
                aria-label={`View tickets for ${u.name}`}
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-sm font-bold text-blue-700">
                    {u.name?.[0]?.toUpperCase() || "?"}
                  </div>
                  <div>
                    <p className="font-semibold text-sm text-slate-900">{u.name}</p>
                    <p className="flex items-center gap-1 text-xs text-slate-400">
                      <Phone size={11} /> {u.phone_number}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      u.active !== false ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {u.active !== false ? "Active" : "Inactive"}
                  </span>
                  <Ticket size={14} className="text-slate-400" aria-hidden="true" />
                </div>
              </button>
              {(role === "super_admin" || role === "dispatcher") && (
                <div className="flex gap-2 pt-1 border-t border-slate-50">
                  <button
                    onClick={() => setPinTarget(u)}
                    className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
                  >
                    <KeyRound size={12} /> Set PIN
                  </button>
                  <button
                    onClick={() => toggleActive(u)}
                    className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium ${
                      u.active !== false
                        ? "border-red-100 text-red-600 hover:bg-red-50"
                        : "border-emerald-100 text-emerald-600 hover:bg-emerald-50"
                    }`}
                  >
                    {u.active !== false ? "Deactivate" : "Activate"}
                  </button>
                </div>
              )}
            </div>
          ))}
          {filtered.length === 0 && (
            <p className="col-span-3 py-12 text-center text-sm text-slate-400">No technicians found.</p>
          )}
        </div>
      )}

      {showAdd && <AddUserModal onSave={handleAdd} onClose={() => setShowAdd(false)} />}
      {pinTarget && (
        <SetPinModal
          user={pinTarget}
          onClose={() => setPinTarget(null)}
          onSaved={() => { setPinTarget(null); toast.success("PIN updated"); }}
        />
      )}
    </div>
  );
}

function AddUserModal({ onSave, onClose }) {
  const [form, setForm] = useState({ name: "", phone_number: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    if (!form.name.trim() || !form.phone_number.trim()) {
      setError("Name and phone are required.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await onSave({ name: form.name.trim(), phone_number: form.phone_number.trim() });
    } catch (err) {
      setError(err.response?.data?.detail || "Failed.");
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="w-full max-w-sm rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <h2 className="font-semibold text-slate-900">Add Technician</h2>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-100"><X size={18} /></button>
        </div>
        <form onSubmit={submit} className="p-6 space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Full Name *</label>
            <input className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} required />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">WhatsApp Phone *</label>
            <input className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              placeholder="+44770000000"
              value={form.phone_number} onChange={(e) => setForm((f) => ({ ...f, phone_number: e.target.value }))} required />
          </div>
          {error && (
            <div className="flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              <AlertCircle size={14} /> {error}
            </div>
          )}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50">Cancel</button>
            <button type="submit" disabled={saving} className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60">
              {saving && <Loader2 size={14} className="animate-spin" />} {saving ? "Adding…" : "Add"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function SetPinModal({ user, onClose, onSaved }) {
  const [pin, setPin] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    if (pin.length < 4) { setError("PIN must be at least 4 digits."); return; }
    setSaving(true);
    setError("");
    try {
      await client.post(`/users/${user.phone_number}/set-pin`, { pin });
      onSaved();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to set PIN.");
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="w-full max-w-xs rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <h2 className="font-semibold text-slate-900">Set PIN — {user.name}</h2>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-100"><X size={18} /></button>
        </div>
        <form onSubmit={submit} className="p-6 space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">New PIN (4–8 digits)</label>
            <input type="password" inputMode="numeric" pattern="[0-9]*" maxLength={8}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-center text-xl tracking-widest focus:border-blue-500 focus:outline-none"
              value={pin} onChange={(e) => setPin(e.target.value.replace(/[^0-9]/g, ""))} />
          </div>
          {error && (
            <div className="flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              <AlertCircle size={14} /> {error}
            </div>
          )}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600">Cancel</button>
            <button type="submit" disabled={saving} className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white disabled:opacity-60">
              {saving && <Loader2 size={14} className="animate-spin" />} {saving ? "Saving…" : "Save PIN"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
