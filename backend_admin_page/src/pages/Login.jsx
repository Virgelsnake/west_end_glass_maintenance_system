import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await login(username, password);
      navigate("/dashboard");
    } catch {
      setError("Invalid username or password.");
    }
  };

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h2 style={styles.title}>West End Glass</h2>
        <p style={styles.sub}>Admin Control Panel</p>
        <form onSubmit={handleSubmit}>
          <input style={styles.input} placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} required />
          <input style={styles.input} type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          {error && <p style={styles.error}>{error}</p>}
          <button style={styles.btn} type="submit">Login</button>
        </form>
      </div>
    </div>
  );
}

const styles = {
  page: { display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh", background: "#1a1a2e" },
  card: { background: "#fff", padding: 40, borderRadius: 12, width: 320, boxShadow: "0 4px 20px rgba(0,0,0,.3)" },
  title: { margin: "0 0 4px", color: "#1a1a2e", textAlign: "center" },
  sub: { textAlign: "center", color: "#888", marginBottom: 24 },
  input: { width: "100%", padding: "10px 12px", marginBottom: 12, border: "1px solid #ddd", borderRadius: 6, boxSizing: "border-box", fontSize: 14 },
  error: { color: "red", fontSize: 13, marginBottom: 8 },
  btn: { width: "100%", padding: 12, background: "#e2b04a", color: "#1a1a2e", border: "none", borderRadius: 6, fontWeight: "bold", cursor: "pointer", fontSize: 15 },
};
