import { useState, useCallback } from "react";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import client from "../api/client";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";
import {
  Plus, Shield, KeyRound, AlertCircle, Loader2, X, UserX, UserCheck,
} from "lucide-react";

const ROLES = ["super_admin", "dispatcher", "viewer"];
const ROLE_STYLES = {
  super_admin: "bg-purple-100 text-purple-700",
  dispatcher: "bg-blue-100 text-blue-700",
  viewer: "bg-slate-100 text-slate-600",
};
const ROLE_LABELS = {
  super_admin: "Super Admin",
  dispatcher: "Dispatcher",
  viewer: "Viewer",
};

export default function Admins() {
  const { username: meUsername } = useAuth();
  const [admins, setAdmins] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [resetTarget, setResetTarget] = useState(null);

  const load = useCallback(async () => {
    try {
      const res = await client.get("/admins");
      setAdmins(res.data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useAutoRefresh(load, 30000);

  async function handleAdd(payload) {
    try {
      await client.post("/admins", payload);
      toast.success("Admin account created");
      setShowAdd(false);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create admin");
    }
  }

  async function toggleActive(admin) {
    try {
      await client.patch(`/admins/${admin.username}`, { active: !admin.active });
      toast.success(`${admin.full_name || admin.username} ${!admin.active ? "activated" : "deactivated"}`);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to update");
    }
  }

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Admin Accounts</h1>
          <p className="text-sm text-slate-500">{admins.length} admin{admins.length !== 1 ? "s" : ""}</p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
        >
          <Plus size={16} /> Add Admin
        </button>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        {loading ? (
          <div className="space-y-0">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="flex gap-4 px-5 py-4 border-b border-slate-50">
                {[...Array(4)].map((_, j) => (
                  <div key={j} className="h-4 flex-1 animate-pulse rounded bg-slate-100" />
                ))}
              </div>
            ))}
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-xs font-medium text-slate-500 bg-slate-50">
                <th className="px-5 py-3 text-left">Name</th>
                <th className="px-3 py-3 text-left">Username</th>
                <th className="px-3 py-3 text-left">Role</th>
                <th className="px-3 py-3 text-left">Status</th>
                <th className="px-3 py-3 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {admins.map((admin) => (
                <tr key={admin.username} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-xs font-bold text-slate-600">
                        {(admin.full_name || admin.username)[0]?.toUpperCase()}
                      </div>
                      <div>
                        <p className="font-medium text-slate-900">{admin.full_name || admin.username}</p>
                        {admin.last_login && (
                          <p className="text-xs text-slate-400">
                            Last login: {new Date(admin.last_login).toLocaleDateString()}
                          </p>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-3 py-3 text-slate-500">@{admin.username}</td>
                  <td className="px-3 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${ROLE_STYLES[admin.role] || "bg-slate-100 text-slate-600"}`}>
                      {ROLE_LABELS[admin.role] || admin.role}
                    </span>
                  </td>
                  <td className="px-3 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${admin.active !== false ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
                      {admin.active !== false ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-3 py-3">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setResetTarget(admin)}
                        className="flex items-center gap-1 rounded-md border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50"
                      >
                        <KeyRound size={11} /> Reset PW
                      </button>
                      {admin.username !== meUsername && (
                        <button
                          onClick={() => toggleActive(admin)}
                          className={`flex items-center gap-1 rounded-md border px-2 py-1 text-xs ${
                            admin.active !== false
                              ? "border-red-100 text-red-600 hover:bg-red-50"
                              : "border-emerald-100 text-emerald-600 hover:bg-emerald-50"
                          }`}
                        >
                          {admin.active !== false ? <UserX size={11} /> : <UserCheck size={11} />}
                          {admin.active !== false ? "Deactivate" : "Activate"}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showAdd && <AddAdminModal onSave={handleAdd} onClose={() => setShowAdd(false)} />}
      {resetTarget && (
        <ResetPasswordModal
          admin={resetTarget}
          onClose={() => setResetTarget(null)}
          onSaved={() => { setResetTarget(null); toast.success("Password updated"); }}
        />
      )}
    </div>
  );
}

function AddAdminModal({ onSave, onClose }) {
  const [form, setForm] = useState({ username: "", full_name: "", password: "", role: "dispatcher" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    if (!form.username.trim() || !form.password || form.password.length < 8) {
      setError("Username required. Password must be at least 8 characters.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await onSave({ ...form, username: form.username.trim().toLowerCase() });
    } catch (err) {
      setError(err.response?.data?.detail || "Failed.");
      setSaving(false);
    }
  }

  function setField(k, v) { setForm((f) => ({ ...f, [k]: v })); }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="w-full max-w-sm rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <h2 className="font-semibold text-slate-900">Add Admin Account</h2>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-100"><X size={18} /></button>
        </div>
        <form onSubmit={submit} className="p-6 space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Full Name</label>
            <input className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              value={form.full_name} onChange={(e) => setField("full_name", e.target.value)} />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Username *</label>
            <input className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              value={form.username} onChange={(e) => setField("username", e.target.value)} required />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Password *</label>
            <input type="password" className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              value={form.password} onChange={(e) => setField("password", e.target.value)} required />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Role</label>
            <select className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              value={form.role} onChange={(e) => setField("role", e.target.value)}>
              {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
            </select>
          </div>
          {error && (
            <div className="flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              <AlertCircle size={14} /> {error}
            </div>
          )}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600">Cancel</button>
            <button type="submit" disabled={saving} className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white disabled:opacity-60">
              {saving && <Loader2 size={14} className="animate-spin" />} {saving ? "Creating…" : "Create Admin"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ResetPasswordModal({ admin, onClose, onSaved }) {
  const [password, setPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    if (password.length < 8) { setError("Password must be at least 8 characters."); return; }
    setSaving(true);
    setError("");
    try {
      await client.post(`/admins/${admin.username}/set-password`, { new_password: password });
      onSaved();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed.");
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="w-full max-w-xs rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <h2 className="font-semibold text-slate-900">Reset Password</h2>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-100"><X size={18} /></button>
        </div>
        <form onSubmit={submit} className="p-6 space-y-4">
          <p className="text-sm text-slate-500">Setting new password for <strong>{admin.full_name || admin.username}</strong>.</p>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">New Password</label>
            <input type="password" className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
          </div>
          {error && (
            <div className="flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              <AlertCircle size={14} /> {error}
            </div>
          )}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600">Cancel</button>
            <button type="submit" disabled={saving} className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white disabled:opacity-60">
              {saving && <Loader2 size={14} className="animate-spin" />} {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
