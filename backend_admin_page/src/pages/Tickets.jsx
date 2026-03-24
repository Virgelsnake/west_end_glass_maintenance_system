import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import client from "../api/client";

export default function Tickets() {
  const [tickets, setTickets] = useState([]);
  const [searchParams] = useSearchParams();
  const [filter, setFilter] = useState(searchParams.get("status") || "");

  useEffect(() => {
    load();
  }, [filter]);

  async function load() {
    const params = filter ? `?status=${filter}` : "";
    const res = await client.get(`/tickets${params}`);
    setTickets(res.data);
  }

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <h2>Tickets</h2>
        <select style={styles.select} value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="">All</option>
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="closed">Closed</option>
        </select>
      </div>
      <table style={styles.table}>
        <thead>
          <tr>
            {["Machine ID", "Title", "Assigned To", "Priority", "Status", "Created"].map((h) => (
              <th key={h} style={styles.th}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {tickets.map((t) => (
            <tr key={t._id} style={styles.tr}>
              <td style={styles.td}>{t.machine_id}</td>
              <td style={styles.td}>
                <Link to={`/tickets/${t._id}`}>{t.title}</Link>
              </td>
              <td style={styles.td}>{t.assigned_to || "—"}</td>
              <td style={styles.td}>{t.priority}</td>
              <td style={styles.td}><StatusBadge status={t.status} /></td>
              <td style={styles.td}>{new Date(t.created_at).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
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

const styles = {
  page: { padding: 32 },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 },
  select: { padding: "6px 10px", borderRadius: 4, border: "1px solid #ddd" },
  table: { width: "100%", borderCollapse: "collapse", background: "#fff", borderRadius: 8, overflow: "hidden", boxShadow: "0 2px 8px rgba(0,0,0,.08)" },
  th: { background: "#f5f5f5", padding: "10px 14px", textAlign: "left", fontSize: 13, color: "#666" },
  td: { padding: "10px 14px", borderBottom: "1px solid #f0f0f0", fontSize: 14 },
  tr: { cursor: "pointer" },
};
