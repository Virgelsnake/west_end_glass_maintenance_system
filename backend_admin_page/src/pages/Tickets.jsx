import { useEffect, useState, useRef, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import client from "../api/client";
import StepEditor from "../components/StepEditor";

const COLUMNS = [
  { key: "machine_id",  label: "Machine ID" },
  { key: "title",       label: "Title" },
  { key: "assigned_to", label: "Assigned To" },
  { key: "priority",    label: "Priority" },
  { key: "status",      label: "Status" },
  { key: "created_at",  label: "Created" },
];

function SortIcon({ active, dir }) {
  if (!active) return <span style={{ color: "#ccc", fontSize: 10, marginLeft: 3 }}>⇅</span>;
  return <span style={{ fontSize: 10, marginLeft: 3 }}>{dir === "asc" ? "↑" : "↓"}</span>;
}

export default function Tickets() {
  const [tickets, setTickets] = useState([]);
  const [searchParams] = useSearchParams();
  const [statusFilter, setStatusFilter] = useState(searchParams.get("status") || "");
  const [search, setSearch] = useState(searchParams.get("machine") || "");
  const [assignedFilter, setAssignedFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [sortKey, setSortKey] = useState("priority");
  const [sortDir, setSortDir] = useState("desc");
  const [showCreate, setShowCreate] = useState(false);
  const [machines, setMachines] = useState([]);
  const [users, setUsers] = useState([]);

  useEffect(() => { load(); }, [statusFilter]);

  async function load() {
    const params = statusFilter ? `?status=${statusFilter}` : "";
    const res = await client.get(`/tickets${params}`);
    setTickets(res.data);
  }

  async function openCreate() {
    const [mRes, uRes] = await Promise.all([
      client.get("/machines"),
      client.get("/users"),
    ]);
    setMachines(mRes.data);
    setUsers(uRes.data.filter((u) => u.active));
    setShowCreate(true);
  }

  function handleCreate() {
    setShowCreate(false);
    load();
  }

  function toggleSort(key) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "priority" ? "desc" : "asc");
    }
  }

  const displayed = useMemo(() => {
    const q = search.trim().toLowerCase();
    const fromTs = dateFrom ? new Date(dateFrom).getTime() : null;
    const toTs   = dateTo   ? new Date(dateTo + "T23:59:59").getTime() : null;

    let rows = tickets.filter((t) => {
      if (q) {
        const hit =
          (t.machine_id || "").toLowerCase().includes(q) ||
          (t.title || "").toLowerCase().includes(q);
        if (!hit) return false;
      }
      if (assignedFilter && (t.assigned_to || "") !== assignedFilter) return false;
      if (fromTs || toTs) {
        const ts = t.created_at ? new Date(t.created_at).getTime() : 0;
        if (fromTs && ts < fromTs) return false;
        if (toTs   && ts > toTs)   return false;
      }
      return true;
    });

    rows = [...rows].sort((a, b) => {
      let av = a[sortKey] ?? "";
      let bv = b[sortKey] ?? "";
      if (sortKey === "created_at") {
        av = av ? new Date(av).getTime() : 0;
        bv = bv ? new Date(bv).getTime() : 0;
      } else if (sortKey === "priority") {
        av = Number(av);
        bv = Number(bv);
      } else {
        av = String(av).toLowerCase();
        bv = String(bv).toLowerCase();
      }
      if (av < bv) return sortDir === "asc" ? -1 : 1;
      if (av > bv) return sortDir === "asc" ? 1 : -1;
      return 0;
    });

    return rows;
  }, [tickets, search, assignedFilter, dateFrom, dateTo, sortKey, sortDir]);

  const assigneeOptions = useMemo(() => {
    const seen = new Set();
    return tickets
      .map((t) => t.assigned_to)
      .filter((v) => v && !seen.has(v) && seen.add(v))
      .sort();
  }, [tickets]);

  const hasFilters = search || assignedFilter || dateFrom || dateTo;

  return (
    <div style={styles.page}>
      {/* Header */}
      <div style={styles.header}>
        <h2 style={{ margin: 0 }}>Tickets</h2>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <select style={styles.select} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All statuses</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="closed">Closed</option>
          </select>
          <button style={styles.btnCreate} onClick={openCreate}>+ New Ticket</button>
        </div>
      </div>

      {/* Filter bar */}
      <div style={styles.filterBar}>
        <div style={styles.filterGroup}>
          <label style={styles.filterLabel}>Search</label>
          <input
            style={{ ...styles.filterInput, width: 200 }}
            placeholder="Machine ID or title…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div style={styles.filterGroup}>
          <label style={styles.filterLabel}>Assigned To</label>
          <select style={styles.filterInput} value={assignedFilter} onChange={(e) => setAssignedFilter(e.target.value)}>
            <option value="">Anyone</option>
            {assigneeOptions.map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
        </div>
        <div style={styles.filterGroup}>
          <label style={styles.filterLabel}>From</label>
          <input type="date" style={styles.filterInput} value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        </div>
        <div style={styles.filterGroup}>
          <label style={styles.filterLabel}>To</label>
          <input type="date" style={styles.filterInput} value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </div>
        {hasFilters && (
          <button
            style={styles.btnClear}
            onClick={() => { setSearch(""); setAssignedFilter(""); setDateFrom(""); setDateTo(""); }}
          >
            Clear
          </button>
        )}
        <span style={{ marginLeft: "auto", fontSize: 12, color: "#999", alignSelf: "flex-end", paddingBottom: 2 }}>
          {displayed.length} ticket{displayed.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Table */}
      <table style={styles.table}>
        <thead>
          <tr>
            {COLUMNS.map(({ key, label }) => (
              <th
                key={key}
                style={{ ...styles.th, cursor: "pointer", userSelect: "none", whiteSpace: "nowrap" }}
                onClick={() => toggleSort(key)}
              >
                {label}<SortIcon active={sortKey === key} dir={sortDir} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {displayed.map((t) => (
            <tr key={t._id} style={styles.tr}>
              <td style={styles.td}><code style={{ fontSize: 12 }}>{t.machine_id}</code></td>
              <td style={styles.td}>
                <Link to={`/tickets/${t._id}`} style={{ color: "#1976d2" }}>{t.title}</Link>
              </td>
              <td style={styles.td}>{t.assigned_to || "—"}</td>
              <td style={styles.td}><PriorityBadge priority={t.priority} /></td>
              <td style={styles.td}><StatusBadge status={t.status} /></td>
              <td style={styles.td}>
                {t.created_at ? new Date(t.created_at).toLocaleDateString() : "—"}
              </td>
            </tr>
          ))}
          {displayed.length === 0 && (
            <tr>
              <td colSpan={6} style={{ ...styles.td, textAlign: "center", color: "#999", padding: 32 }}>
                No tickets match your filters.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {showCreate && (
        <CreateTicketModal
          machines={machines}
          users={users}
          onSave={handleCreate}
          onClose={() => setShowCreate(false)}
        />
      )}
    </div>
  );
}

function CreateTicketModal({ machines, users, onSave, onClose }) {
  const [form, setForm] = useState({
    machine_id: machines[0]?.machine_id || "",
    title: "",
    description: "",
    assigned_to: "",
    priority: 1,
  });
  const [steps, setSteps] = useState([{ id: crypto.randomUUID(), label: "", completion_type: "confirmation" }]);
  const [photos, setPhotos] = useState([]);
  const [photoPreviews, setPhotoPreviews] = useState([]);
  const fileInputRef = useRef(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function handlePhotoChange(e) {
    const files = Array.from(e.target.files || []);
    const remaining = 5 - photos.length;
    const toAdd = files.slice(0, remaining);
    setPhotos((prev) => [...prev, ...toAdd]);
    setPhotoPreviews((prev) => [...prev, ...toAdd.map((f) => URL.createObjectURL(f))]);
    e.target.value = "";
  }

  function removePhoto(i) {
    URL.revokeObjectURL(photoPreviews[i]);
    setPhotos((prev) => prev.filter((_, idx) => idx !== i));
    setPhotoPreviews((prev) => prev.filter((_, idx) => idx !== i));
  }

  function setField(field, val) {
    setForm((f) => ({ ...f, [field]: val }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (!form.machine_id || !form.title.trim()) {
      setError("Machine and title are required.");
      return;
    }
    if (steps.some((s) => !s.label.trim())) {
      setError("All steps must have a label.");
      return;
    }
    setSaving(true);
    try {
      const res = await client.post("/tickets", {
        ...form,
        assigned_to: form.assigned_to || null,
        priority: parseInt(form.priority, 10) || 1,
        steps: steps.map(({ id, ...rest }, i) => ({
          step_index: i,
          label: rest.label.trim(),
          completion_type: rest.completion_type,
          completed: false,
        })),
      });
      const ticketId = res.data._id;
      if (photos.length > 0) {
        const fd = new FormData();
        photos.forEach((p) => fd.append("photos", p));
        try {
          const photoRes = await client.post(`/tickets/${ticketId}/reference_photos`, fd);
          if (form.assigned_to && photoRes.data.whatsapp_sent) {
            toast.success("Reference photos sent to technician via WhatsApp.");
          } else if (form.assigned_to && !photoRes.data.whatsapp_sent) {
            toast.warning("Ticket created but WhatsApp delivery failed.");
          }
        } catch {
          toast.warning("Ticket created but photo upload failed.");
        }
      }
      onSave();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to create ticket.");
      setSaving(false);
    }
  }

  return (
    <div style={modal.overlay} onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={modal.box}>
        <div style={modal.header}>
          <h3 style={{ margin: 0 }}>New Ticket</h3>
          <button onClick={onClose} style={modal.closeBtn}>✕</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={modal.grid}>
            <label style={modal.label}>Machine *</label>
            <select style={modal.input} value={form.machine_id} onChange={(e) => setField("machine_id", e.target.value)} required>
              {machines.map((m) => (
                <option key={m.machine_id} value={m.machine_id}>{m.machine_id} — {m.name}</option>
              ))}
              {machines.length === 0 && <option value="">No machines registered</option>}
            </select>

            <label style={modal.label}>Title *</label>
            <input
              style={modal.input}
              placeholder="e.g. Monthly lubrication check"
              value={form.title}
              onChange={(e) => setField("title", e.target.value)}
              required
            />

            <label style={modal.label}>Description</label>
            <textarea
              style={{ ...modal.input, height: 60, resize: "vertical" }}
              placeholder="Optional notes for the technician"
              value={form.description}
              onChange={(e) => setField("description", e.target.value)}
            />

            <label style={modal.label}>Assign To</label>
            <select style={modal.input} value={form.assigned_to} onChange={(e) => setField("assigned_to", e.target.value)}>
              <option value="">— Unassigned —</option>
              {users.map((u) => (
                <option key={u.phone_number} value={u.phone_number}>{u.name} ({u.phone_number})</option>
              ))}
            </select>

            <label style={modal.label}>Priority</label>
            <input
              type="number" min={1} max={10}
              style={{ ...modal.input, width: 80 }}
              value={form.priority}
              onChange={(e) => setField("priority", e.target.value)}
            />
          </div>

          <div style={{ marginTop: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <strong style={{ fontSize: 14 }}>Reference Photos</strong>
              {photos.length < 5 && (
                <button type="button" onClick={() => fileInputRef.current?.click()} style={modal.btnAdd}>
                  + Add Photo
                </button>
              )}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple
              style={{ display: "none" }}
              onChange={handlePhotoChange}
            />
            {photoPreviews.length > 0 ? (
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
                {photoPreviews.map((src, i) => (
                  <div key={i} style={{ position: "relative", width: 80, height: 80 }}>
                    <img src={src} alt="" style={{ width: 80, height: 80, objectFit: "cover", borderRadius: 6, border: "1px solid #ddd" }} />
                    <button
                      type="button"
                      onClick={() => removePhoto(i)}
                      style={{ position: "absolute", top: -6, right: -6, background: "#e53935", color: "#fff", border: "none", borderRadius: "50%", width: 18, height: 18, cursor: "pointer", fontSize: 11, lineHeight: "18px", padding: 0 }}
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ fontSize: 12, color: "#999", marginBottom: 12 }}>No photos attached (max 5).</p>
            )}
            {form.assigned_to && photos.length > 0 && (
              <p style={{ fontSize: 12, color: "#2196f3", marginBottom: 10 }}>
                📲 Will send {photos.length} photo{photos.length > 1 ? "s" : ""} to assigned technician via WhatsApp.
              </p>
            )}
          </div>

          <div style={{ marginTop: 4 }}>
            <StepEditor
              items={steps}
              onChange={setSteps}
              label="Steps"
            />
          </div>

          {error && <p style={{ color: "#e53935", marginTop: 12, fontSize: 13 }}>{error}</p>}

          <div style={modal.footer}>
            <button type="button" onClick={onClose} style={modal.btnCancel}>Cancel</button>
            <button type="submit" style={modal.btnSave} disabled={saving}>
              {saving ? "Creating…" : "Create Ticket"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const colors = { open: "#e57373", in_progress: "#ffb74d", closed: "#81c784" };
  return (
    <span style={{ background: colors[status] || "#ddd", padding: "2px 8px", borderRadius: 12, fontSize: 12, fontWeight: "bold" }}>
      {status}
    </span>
  );
}

function PriorityBadge({ priority }) {
  const color = priority >= 7 ? "#e53935" : priority >= 4 ? "#fb8c00" : "#757575";
  return <span style={{ color, fontWeight: "bold" }}>{priority}</span>;
}

const styles = {
  page: { padding: 32 },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 },
  select: { padding: "6px 10px", borderRadius: 4, border: "1px solid #ddd" },
  btnCreate: { background: "#1a1a2e", color: "#fff", border: "none", padding: "8px 16px", borderRadius: 4, cursor: "pointer", fontWeight: "bold" },
  filterBar: { display: "flex", alignItems: "flex-end", gap: 12, flexWrap: "wrap", background: "#fff", border: "1px solid #e5e7eb", borderRadius: 8, padding: "12px 16px", marginBottom: 16, boxShadow: "0 1px 4px rgba(0,0,0,.05)" },
  filterGroup: { display: "flex", flexDirection: "column", gap: 3 },
  filterLabel: { fontSize: 11, color: "#888", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em" },
  filterInput: { padding: "6px 10px", border: "1px solid #ddd", borderRadius: 4, fontSize: 13 },
  btnClear: { alignSelf: "flex-end", background: "none", border: "1px solid #ddd", color: "#666", padding: "6px 12px", borderRadius: 4, cursor: "pointer", fontSize: 12 },
  table: { width: "100%", borderCollapse: "collapse", background: "#fff", borderRadius: 8, overflow: "hidden", boxShadow: "0 2px 8px rgba(0,0,0,.08)" },
  th: { background: "#f5f5f5", padding: "10px 14px", textAlign: "left", fontSize: 13, color: "#666" },
  td: { padding: "10px 14px", borderBottom: "1px solid #f0f0f0", fontSize: 14 },
  tr: {},
};

const modal = {
  overlay: { position: "fixed", inset: 0, background: "rgba(0,0,0,.45)", display: "flex", justifyContent: "center", alignItems: "flex-start", zIndex: 1000, overflowY: "auto", padding: "40px 16px" },
  box: { background: "#fff", borderRadius: 10, width: "100%", maxWidth: 600, padding: 28, position: "relative" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 },
  closeBtn: { background: "none", border: "none", fontSize: 18, cursor: "pointer", color: "#888", lineHeight: 1 },
  grid: { display: "grid", gridTemplateColumns: "110px 1fr", gap: "10px 12px", alignItems: "center" },
  label: { fontSize: 13, color: "#555", textAlign: "right", paddingRight: 8 },
  input: { padding: "7px 10px", border: "1px solid #ddd", borderRadius: 4, fontSize: 14, width: "100%", boxSizing: "border-box" },
  stepRow: { display: "flex", gap: 8, alignItems: "center", marginBottom: 8 },
  stepNum: { fontSize: 13, color: "#aaa", width: 22, textAlign: "right", flexShrink: 0 },
  btnAdd: { background: "none", border: "1px solid #1a1a2e", color: "#1a1a2e", padding: "4px 10px", borderRadius: 4, cursor: "pointer", fontSize: 12 },
  btnRemove: { background: "none", border: "1px solid #e57373", color: "#e57373", borderRadius: 4, cursor: "pointer", padding: "2px 8px", fontSize: 14 },
  footer: { display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 24 },
  btnCancel: { background: "#f5f5f5", border: "1px solid #ddd", padding: "8px 16px", borderRadius: 4, cursor: "pointer" },
  btnSave: { background: "#1a1a2e", color: "#fff", border: "none", padding: "8px 20px", borderRadius: 4, cursor: "pointer", fontWeight: "bold" },
};

