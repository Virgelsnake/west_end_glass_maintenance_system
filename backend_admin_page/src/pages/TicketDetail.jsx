import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import client from "../api/client";
import StepList from "../components/StepList";
import ConversationView from "../components/ConversationView";
import PhotoGallery from "../components/PhotoGallery";

export default function TicketDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [ticket, setTicket] = useState(null);
  const [messages, setMessages] = useState([]);
  const [tab, setTab] = useState("steps");
  const [sendText, setSendText] = useState("");

  useEffect(() => {
    loadTicket();
    loadMessages();
  }, [id]);

  async function loadTicket() {
    const res = await client.get(`/tickets/${id}`);
    setTicket(res.data);
  }

  async function loadMessages() {
    const res = await client.get(`/tickets/${id}/messages`);
    setMessages(res.data);
  }

  async function handleClose() {
    await client.post(`/tickets/${id}/close`);
    loadTicket();
  }

  async function handleReopen() {
    await client.post(`/tickets/${id}/reopen`);
    loadTicket();
  }

  async function handleSend(e) {
    e.preventDefault();
    if (!sendText.trim()) return;
    await client.post(`/tickets/${id}/messages`, { text: sendText });
    setSendText("");
    loadMessages();
  }

  if (!ticket) return <div style={{ padding: 32 }}>Loading...</div>;

  return (
    <div style={styles.page}>
      <button onClick={() => navigate("/tickets")} style={styles.back}>← Back</button>
      <div style={styles.header}>
        <div>
          <h2 style={{ margin: 0 }}>{ticket.title}</h2>
          <p style={styles.sub}>Machine: {ticket.machine_id} · Assigned: {ticket.assigned_to || "Unassigned"}</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {ticket.status !== "closed" ? (
            <button style={styles.btnRed} onClick={handleClose}>Close Ticket</button>
          ) : (
            <button style={styles.btnGreen} onClick={handleReopen}>Reopen Ticket</button>
          )}
        </div>
      </div>

      <div style={styles.tabs}>
        {["steps", "conversation", "photos"].map((t) => (
          <button key={t} style={tab === t ? styles.tabActive : styles.tab} onClick={() => setTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      <div style={styles.body}>
        {tab === "steps" && <StepList steps={ticket.steps} />}
        {tab === "conversation" && (
          <>
            <ConversationView messages={messages} />
            <form onSubmit={handleSend} style={styles.sendForm}>
              <input
                style={styles.sendInput}
                placeholder="Send a message as admin..."
                value={sendText}
                onChange={(e) => setSendText(e.target.value)}
              />
              <button style={styles.sendBtn} type="submit">Send</button>
            </form>
          </>
        )}
        {tab === "photos" && <PhotoGallery ticketId={id} steps={ticket.steps} />}
      </div>
    </div>
  );
}

const styles = {
  page: { padding: 32 },
  back: { background: "none", border: "none", color: "#1976d2", cursor: "pointer", fontSize: 14, marginBottom: 12 },
  header: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 },
  sub: { color: "#888", margin: "4px 0 0" },
  tabs: { display: "flex", gap: 4, marginBottom: 20 },
  tab: { padding: "8px 16px", border: "1px solid #ddd", borderRadius: 4, background: "#fff", cursor: "pointer" },
  tabActive: { padding: "8px 16px", border: "none", borderRadius: 4, background: "#1a1a2e", color: "#fff", cursor: "pointer" },
  body: { background: "#fff", borderRadius: 8, padding: 20, boxShadow: "0 2px 8px rgba(0,0,0,.08)" },
  btnRed: { background: "#e57373", color: "#fff", border: "none", padding: "8px 16px", borderRadius: 4, cursor: "pointer", fontWeight: "bold" },
  btnGreen: { background: "#81c784", color: "#fff", border: "none", padding: "8px 16px", borderRadius: 4, cursor: "pointer", fontWeight: "bold" },
  sendForm: { display: "flex", gap: 8, marginTop: 12 },
  sendInput: { flex: 1, padding: "8px 12px", border: "1px solid #ddd", borderRadius: 4 },
  sendBtn: { background: "#1a1a2e", color: "#fff", border: "none", padding: "8px 16px", borderRadius: 4, cursor: "pointer" },
};
