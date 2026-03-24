import { useEffect, useState } from "react";
import client from "../api/client";

export default function Machines() {
  const [machines, setMachines] = useState([]);
  const [form, setForm] = useState({ machine_id: "", name: "", location: "", notes: "" });
  const [error, setError] = useState("");

  useEffect(() => { load(); }, []);

  async function load() {
    const res = await client.get("/machines");
    setMachines(res.data);
  }

  async function handleAdd(e) {
    e.preventDefault();
    setError("");
    try {
      await client.post("/machines", form);
      setForm({ machine_id: "", name: "", location: "", notes: "" });
      load();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to add machine.");
    }
  }

  return (
    <div style={styles.page}>
      <h2>Machines</h2>
      <form onSubmit={handleAdd} style={styles.form}>
        <input style={styles.input} placeholder="WEG-MACHINE-0001" value={form.machine_id} onChange={(e) => setForm({ ...form, machine_id: e.target.value })} required />
        <input style={styles.input} placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        <input style={styles.input} placeholder="Location (optional)" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
        <button style={styles.btn} type="submit">Add Machine</button>
      </form>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <table style={styles.table}>
        <thead>
          <tr>{["Machine ID", "Name", "Location", "Registered"].map((h) => <th key={h} style={styles.th}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {machines.map((m) => (
            <tr key={m.machine_id}>
              <td style={styles.td}><code>{m.machine_id}</code></td>
              <td style={styles.td}>{m.name}</td>
              <td style={styles.td}>{m.location || "—"}</td>
              <td style={styles.td}>{new Date(m.created_at).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const styles = {
  page: { padding: 32 },
  form: { display: "flex", gap: 8, marginBottom: 20, flexWrap: "wrap" },
  input: { padding: "8px 12px", border: "1px solid #ddd", borderRadius: 4, fontSize: 14 },
  btn: { background: "#1a1a2e", color: "#fff", border: "none", padding: "8px 16px", borderRadius: 4, cursor: "pointer" },
  table: { width: "100%", borderCollapse: "collapse", background: "#fff", borderRadius: 8, overflow: "hidden", boxShadow: "0 2px 8px rgba(0,0,0,.08)" },
  th: { background: "#f5f5f5", padding: "10px 14px", textAlign: "left", fontSize: 13, color: "#666" },
  td: { padding: "10px 14px", borderBottom: "1px solid #f0f0f0", fontSize: 14 },
};
