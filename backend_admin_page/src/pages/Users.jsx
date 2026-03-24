import { useEffect, useState } from "react";
import client from "../api/client";

const LANGUAGES = ["en", "es", "fr", "de", "pt", "ar", "zh"];

export default function Users() {
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState({ phone_number: "", name: "", language: "en" });
  const [error, setError] = useState("");

  useEffect(() => { load(); }, []);

  async function load() {
    const res = await client.get("/users");
    setUsers(res.data);
  }

  async function handleAdd(e) {
    e.preventDefault();
    setError("");
    try {
      await client.post("/users", form);
      setForm({ phone_number: "", name: "", language: "en" });
      load();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to add user.");
    }
  }

  async function handleDeactivate(phone) {
    await client.delete(`/users/${encodeURIComponent(phone)}`);
    load();
  }

  return (
    <div style={styles.page}>
      <h2>Users</h2>
      <form onSubmit={handleAdd} style={styles.form}>
        <input style={styles.input} placeholder="+15551234567" value={form.phone_number} onChange={(e) => setForm({ ...form, phone_number: e.target.value })} required />
        <input style={styles.input} placeholder="Full name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        <select style={styles.select} value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })}>
          {LANGUAGES.map((l) => <option key={l} value={l}>{l}</option>)}
        </select>
        <button style={styles.btn} type="submit">Add User</button>
      </form>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <table style={styles.table}>
        <thead>
          <tr>{["Phone", "Name", "Language", "Active", "Last Activity", "Actions"].map((h) => <th key={h} style={styles.th}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.phone_number}>
              <td style={styles.td}>{u.phone_number}</td>
              <td style={styles.td}>{u.name}</td>
              <td style={styles.td}>{u.language}</td>
              <td style={styles.td}>{u.active ? "✓" : "✗"}</td>
              <td style={styles.td}>{u.last_activity ? new Date(u.last_activity).toLocaleString() : "—"}</td>
              <td style={styles.td}>
                {u.active && (
                  <button style={styles.deactivate} onClick={() => handleDeactivate(u.phone_number)}>Deactivate</button>
                )}
              </td>
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
  select: { padding: "8px 10px", border: "1px solid #ddd", borderRadius: 4 },
  btn: { background: "#1a1a2e", color: "#fff", border: "none", padding: "8px 16px", borderRadius: 4, cursor: "pointer" },
  table: { width: "100%", borderCollapse: "collapse", background: "#fff", borderRadius: 8, overflow: "hidden", boxShadow: "0 2px 8px rgba(0,0,0,.08)" },
  th: { background: "#f5f5f5", padding: "10px 14px", textAlign: "left", fontSize: 13, color: "#666" },
  td: { padding: "10px 14px", borderBottom: "1px solid #f0f0f0", fontSize: 14 },
  deactivate: { background: "#e57373", color: "#fff", border: "none", padding: "4px 10px", borderRadius: 4, cursor: "pointer", fontSize: 12 },
};
