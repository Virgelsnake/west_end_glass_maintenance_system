export default function StepList({ steps = [] }) {
  return (
    <div>
      {steps.map((step) => (
        <div key={step.step_index} style={styles.row}>
          <span style={step.completed ? styles.done : styles.pending}>
            {step.completed ? "✓" : "○"}
          </span>
          <div style={{ flex: 1 }}>
            <div style={styles.label}>
              Step {step.step_index}: {step.label}
              <span style={styles.type}>[{step.completion_type}]</span>
            </div>
            {step.note_text && <div style={styles.note}>📝 {step.note_text}</div>}
            {step.photo_path && <div style={styles.note}>📷 Photo attached</div>}
            {step.completed_at && (
              <div style={styles.meta}>
                Completed by {step.completed_by} at {new Date(step.completed_at).toLocaleString()}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

const styles = {
  row: { display: "flex", gap: 12, padding: "10px 0", borderBottom: "1px solid #eee", alignItems: "flex-start" },
  done: { color: "#2e7d32", fontSize: 20, minWidth: 24 },
  pending: { color: "#aaa", fontSize: 20, minWidth: 24 },
  label: { fontWeight: 500 },
  type: { marginLeft: 8, fontSize: 12, color: "#666", fontStyle: "italic" },
  note: { color: "#555", fontSize: 13, marginTop: 4 },
  meta: { color: "#999", fontSize: 11, marginTop: 2 },
};
