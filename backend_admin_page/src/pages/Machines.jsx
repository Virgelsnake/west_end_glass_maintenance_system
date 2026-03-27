import { useState, useCallback, useEffect } from "react";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import client from "../api/client";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";
import { Plus, Search, MapPin, Copy, Check, AlertCircle, Loader2, X } from "lucide-react";

export default function Machines() {
  const { role } = useAuth();
  const [machines, setMachines] = useState([]);
  const [ticketCounts, setTicketCounts] = useState({});
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [waNumber, setWaNumber] = useState("");

  useEffect(() => {
    client.get("/settings/public").then((r) => {
      if (r.data?.whatsapp_business_number) setWaNumber(r.data.whatsapp_business_number);
    }).catch(() => {});
  }, []);

  const load = useCallback(async () => {
    try {
      const [mRes, tRes] = await Promise.all([
        client.get("/machines"),
        client.get("/tickets?status=open"),
      ]);
      setMachines(mRes.data);
      const counts = {};
      for (const t of tRes.data) {
        counts[t.machine_id] = (counts[t.machine_id] || 0) + 1;
      }
      setTicketCounts(counts);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useAutoRefresh(load, 30000);

  const filtered = machines.filter((m) => {
    const q = search.toLowerCase();
    return (
      !q ||
      m.machine_id?.toLowerCase().includes(q) ||
      m.name?.toLowerCase().includes(q) ||
      m.location?.toLowerCase().includes(q)
    );
  });

  async function handleAdd(payload) {
    try {
      await client.post("/machines", payload);
      toast.success("Machine added");
      setShowAdd(false);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to add machine");
    }
  }

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Machines</h1>
          <p className="text-sm text-slate-500">{filtered.length} machine{filtered.length !== 1 ? "s" : ""}</p>
        </div>
        {(role === "super_admin" || role === "dispatcher") && (
          <button
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
          >
            <Plus size={16} /> Add Machine
          </button>
        )}
      </div>

      <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            className="w-full rounded-lg border border-slate-200 py-1.5 pl-8 pr-3 text-sm focus:border-blue-500 focus:outline-none"
            placeholder="Search ID, name, or location…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-28 rounded-xl bg-slate-100 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {filtered.map((m) => (
            <MachineCard key={m.machine_id} machine={m} openCount={ticketCounts[m.machine_id] || 0} waNumber={waNumber} />
          ))}
          {filtered.length === 0 && (
            <p className="col-span-3 py-12 text-center text-sm text-slate-400">No machines found.</p>
          )}
        </div>
      )}

      {showAdd && <AddMachineModal onSave={handleAdd} onClose={() => setShowAdd(false)} />}
    </div>
  );
}

function MachineCard({ machine: m, openCount, waNumber }) {
  const [copied, setCopied] = useState(false);
  const waLink = waNumber
    ? `https://wa.me/${waNumber}?text=${encodeURIComponent(m.machine_id)}`
    : null;

  function copyLink() {
    if (!waLink) return;
    navigator.clipboard.writeText(waLink).then(() => {
      setCopied(true);
      toast.success("WA link copied!");
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm p-5 flex flex-col gap-2 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <code className="rounded bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">
          {m.machine_id}
        </code>
        {openCount > 0 && (
          <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">
            {openCount} open
          </span>
        )}
      </div>
      <p className="font-semibold text-slate-900 text-sm">{m.name}</p>
      {m.location && (
        <p className="flex items-center gap-1 text-xs text-slate-400">
          <MapPin size={11} /> {m.location}
        </p>
      )}
      {m.description && (
        <p className="text-xs text-slate-400 line-clamp-2">{m.description}</p>
      )}
      {waLink && (
        <button
          onClick={copyLink}
          className="mt-1 flex items-center gap-1.5 self-start rounded-lg border border-green-200 bg-green-50 px-3 py-1.5 text-xs font-medium text-green-700 hover:bg-green-100 transition-colors"
          title={waLink}
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
          {copied ? "Copied!" : "Copy WA Link"}
        </button>
      )}
    </div>
  );
}

function AddMachineModal({ onSave, onClose }) {
  const [form, setForm] = useState({ machine_id: "", name: "", location: "", description: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    if (!form.machine_id.trim() || !form.name.trim()) {
      setError("Machine ID and name are required.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await onSave({
        machine_id: form.machine_id.trim().toUpperCase(),
        name: form.name.trim(),
        location: form.location.trim() || null,
        description: form.description.trim() || null,
      });
    } catch (err) {
      setError(err.response?.data?.detail || "Failed.");
      setSaving(false);
    }
  }

  function setField(k, v) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="w-full max-w-sm rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <h2 className="font-semibold text-slate-900">Add Machine</h2>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-100"><X size={18} /></button>
        </div>
        <form onSubmit={submit} className="p-6 space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Machine ID *</label>
            <input className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-mono uppercase focus:border-blue-500 focus:outline-none"
              placeholder="e.g. CNC-01" value={form.machine_id} onChange={(e) => setField("machine_id", e.target.value)} required />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Name *</label>
            <input className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              placeholder="e.g. CNC Glass Cutter" value={form.name} onChange={(e) => setField("name", e.target.value)} required />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Location</label>
            <input className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              placeholder="e.g. Workshop Bay 3" value={form.location} onChange={(e) => setField("location", e.target.value)} />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Description</label>
            <textarea className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none resize-none"
              rows={2} value={form.description} onChange={(e) => setField("description", e.target.value)} />
          </div>
          {error && (
            <div className="flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              <AlertCircle size={14} /> {error}
            </div>
          )}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600">Cancel</button>
            <button type="submit" disabled={saving} className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white disabled:opacity-60">
              {saving && <Loader2 size={14} className="animate-spin" />} {saving ? "Adding…" : "Add Machine"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
