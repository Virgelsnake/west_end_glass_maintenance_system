const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function PhotoGallery({ ticketId, steps = [] }) {
  const photoSteps = steps.filter((s) => s.photo_path);

  if (!photoSteps.length) return <p style={{ color: "#aaa" }}>No photos attached.</p>;

  return (
    <div style={styles.grid}>
      {photoSteps.map((step) => {
        const filename = step.photo_path.split("/").pop();
        const token = localStorage.getItem("access_token");
        const src = `${API_BASE}/tickets/${ticketId}/photos/${filename}`;
        return (
          <div key={step.step_index} style={styles.card}>
            <img
              src={src}
              alt={`Step ${step.step_index}`}
              style={styles.img}
              onError={(e) => { e.target.style.display = "none"; }}
            />
            <div style={styles.caption}>Step {step.step_index}: {step.label}</div>
          </div>
        );
      })}
    </div>
  );
}

const styles = {
  grid: { display: "flex", flexWrap: "wrap", gap: 12 },
  card: { width: 180, background: "#fafafa", border: "1px solid #ddd", borderRadius: 8, overflow: "hidden" },
  img: { width: "100%", height: 140, objectFit: "cover" },
  caption: { padding: "6px 8px", fontSize: 12, color: "#555" },
};
