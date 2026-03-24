import { useEffect, useState } from "react";
import client from "../api/client";

const EVENT_TYPES = [
  "", "ticket_created", "ticket_updated", "ticket_closed", "ticket_reopened",
  "message_received", "message_sent", "note_added", "photo_attached",
  "step_completed", "user_added", "user_deactivated", "auth_failure"
];

export default function AuditLog() {
  const [logs, setLogs] = useState([]);
  const [filters, setFilters] = useState({ event: "", actor: "", machine_id: "", ticket_id: "" });
  const [skip, setSkip] = useState(0);
  const LIMIT = 50;

  useEffect(() => { load(0); }, [filters]);

  async function load(newSkip = 0) {
    const params = new URLSearchParams({ limit: LIMIT, skip: newSkip });
    Object.entries(filters).forEach(([k, v]) => { if (v) params.append(k, v); });
    const res = await client.get(`/audit?${params}`);
    setLogs(res.data);
    setSkip(newSkip);
  }

  return (
    <div style={styles.page}>
      <h2>Audit Log</h2>
      <div style={styles.filters}>
        <select style={styles.select} value={filters.event} onChange={(e) => setFilters({ ...filters, event: e.target.value })}>
          {EVENT_TYPES.map((t) => <option key={t} value={t}>{t || "All Events"}</option>)}
        </select>
        <input style={styles.input} placeholder="Actor (phone or admin)" value={filters.actor} onChange={(e) => setFilters({ ...filters, actor: e.target.value })} />
        <input style={styles.input} placeholder="Machine ID" value={filters.machine_id} onChange={(e) => setFilters({ ...filters, machine_id: e.target.value })} />
        <input style={styles.input} placeholder="Ticket ID" value={filters.ticket_id} onChange={(e) => setFilters({ ...filters, ticket_id: e.target.value })} />
      </div>
      <table style={styles.table}>
        <thead>
          <tr>{["Timestamp", "Event", "Actor", "Machine", "Ticket", "Payload"].map((h) => <th key={h} style={styles.th}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr key={log._id}>
              <td style={styles.td}>{new Date(log.timestamp).toLocaleString()}</td>
              <td style={styles.td}><code>{log.event}</code></td>
              <td style={styles.td}>{log.actor || "—"}</td>
              <td style={styles.td}>{log.machine_id || "—"}</td>
              <td style={styles.td}>{log.ticket_id ? log.ticket_id.slice(-6) : "—"}</td>
              <td style={styles.td}><pre style={styles.pre}>{JSON.stringify(log.payload, null, 1)}</pre></td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={styles.pagination}>
        <button disabled={skip === 0} onClick={() => load(Math.max(0, skip - LIMIT))} style={styles.pgBtn}>← Prev</button>
        <button disabled={logs.length < LIMIT} onClick={() => load(skip + LIMIT)} style={styles.pgBtn}>Next →</button>
      </div>
    </div>
  );
}

const styles = {
  page: { padding: 32 },
  filters: { display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" },
  select: { padding: "7px 10px", border: "1px solid #ddd", borderRadius: 4 },
  input: { padding: "7px 12px", border: "1px solid #ddd", borderRadius: 4, fontSize: 14 },
  table: { width: "100%", borderCollapse: "collapse", background: "#fff", borderRadius: 8, overflow: "hidden", boxShadow: "0 2px 8px rgba(0,0,0,.08)" },
  th: { background: "#f5f5f5", padding: "10px 14px", textAlign: "left", fontSize: 13, color: "#666" },
  td: { padding: "8px 12px", borderBottom: "1px solid #f0f0f0", fontSize: 13, verticalAlign: "top" },
  pre: { margin: 0, fontSize: 11, maxWidth: 200, whiteSpace: "pre-wrap", wordBreak: "break-all" },
  pagination: { display: "flex", gap: 8, marginTop: 16, justifyContent: "flex-end" },
  pgBtn: { padding: "6px 14px", border: "1px solid #ddd", borderRadius: 4, cursor: "pointer" },
};
