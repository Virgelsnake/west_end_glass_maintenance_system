export default function ConversationView({ messages = [] }) {
  return (
    <div style={styles.container}>
      {messages.map((msg, i) => (
        <div key={i} style={msg.direction === "inbound" ? styles.inbound : styles.outbound}>
          <div style={styles.bubble}>
            {msg.content}
            {msg.ai_generated && <span style={styles.aiTag}> 🤖</span>}
          </div>
          <div style={styles.meta}>
            {msg.direction === "inbound" ? msg.phone_number : "System"}
            {" · "}
            {new Date(msg.timestamp).toLocaleTimeString()}
          </div>
        </div>
      ))}
    </div>
  );
}

const styles = {
  container: { display: "flex", flexDirection: "column", gap: 8, padding: 12, background: "#f0f4f0", borderRadius: 8, maxHeight: 500, overflowY: "auto" },
  inbound: { alignSelf: "flex-start", maxWidth: "70%" },
  outbound: { alignSelf: "flex-end", maxWidth: "70%" },
  bubble: { background: "#fff", padding: "8px 12px", borderRadius: 12, boxShadow: "0 1px 2px rgba(0,0,0,.1)", fontSize: 14 },
  aiTag: { fontSize: 11, color: "#888" },
  meta: { fontSize: 11, color: "#999", marginTop: 2, paddingLeft: 4 },
};
