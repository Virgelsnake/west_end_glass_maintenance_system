import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { username, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <nav style={styles.nav}>
      <img src="/logo.png" alt="" style={{height: 28, width: 28, objectFit: 'contain', marginRight: 8}} />
      <span style={styles.brand}>West End Glass</span>
      <div style={styles.links}>
        <Link style={styles.link} to="/dashboard">Dashboard</Link>
        <Link style={styles.link} to="/tickets">Tickets</Link>
        <Link style={styles.link} to="/users">Users</Link>
        <Link style={styles.link} to="/machines">Machines</Link>
        <Link style={styles.link} to="/audit">Audit Log</Link>
      </div>
      <div style={styles.user}>
        <span style={{ marginRight: 12, color: "#7cadd8" }}>{username}</span>
        <button onClick={handleLogout} style={styles.btn}>Logout</button>
      </div>
    </nav>
  );
}

const styles = {
  nav: { display: "flex", alignItems: "center", background: "#0d2d52", padding: "12px 24px", gap: 20 },
  brand: { color: "#ffffff", fontWeight: "bold", fontSize: 18, marginRight: 24 },
  links: { display: "flex", gap: 16, flex: 1 },
  link: { color: "#7cadd8", textDecoration: "none", fontSize: 14 },
  user: { display: "flex", alignItems: "center" },
  btn: { background: "#ee6300", color: "#ffffff", border: "none", padding: "6px 14px", borderRadius: 4, cursor: "pointer", fontWeight: "bold" },
};
