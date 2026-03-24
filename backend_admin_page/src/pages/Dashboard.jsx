import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "../api/client";

export default function Dashboard() {
  const [stats, setStats] = useState({ open: 0, in_progress: 0, closed: 0 });

  useEffect(() => {
    async function load() {
      const [open, ip, closed] = await Promise.all([
        client.get("/tickets?status=open"),
        client.get("/tickets?status=in_progress"),
        client.get("/tickets?status=closed"),
      ]);
      setStats({
        open: open.data.length,
        in_progress: ip.data.length,
        closed: closed.data.length,
      });
    }
    load();
  }, []);

  return (
    <div style={styles.page}>
      <h2>Dashboard</h2>
      <div style={styles.cards}>
        <StatCard label="Open Tickets" value={stats.open} color="#e57373" to="/tickets?status=open" />
        <StatCard label="In Progress" value={stats.in_progress} color="#ffb74d" to="/tickets?status=in_progress" />
        <StatCard label="Closed Today" value={stats.closed} color="#81c784" to="/tickets?status=closed" />
      </div>
    </div>
  );
}

function StatCard({ label, value, color, to }) {
  return (
    <Link to={to} style={{ ...styles.card, borderTop: `4px solid ${color}` }}>
      <div style={styles.num}>{value}</div>
      <div style={styles.lbl}>{label}</div>
    </Link>
  );
}

const styles = {
  page: { padding: 32 },
  cards: { display: "flex", gap: 20, marginTop: 24 },
  card: { background: "#fff", borderRadius: 10, padding: 24, minWidth: 160, boxShadow: "0 2px 8px rgba(0,0,0,.08)", textDecoration: "none", color: "inherit" },
  num: { fontSize: 42, fontWeight: "bold", color: "#333" },
  lbl: { color: "#666", marginTop: 4 },
};
