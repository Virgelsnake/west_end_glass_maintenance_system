import { useState, useCallback, useRef } from "react";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import client from "../api/client";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";
import {
  FileText, Upload, Trash2, Loader2, X, AlertCircle,
  FileImage, FileType2, Plus,
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function fileTypeIcon(fileType) {
  if (["jpg", "jpeg", "png", "webp"].includes(fileType)) return <FileImage size={16} className="text-emerald-600" />;
  if (fileType === "pdf") return <FileType2 size={16} className="text-red-600" />;
  return <FileText size={16} className="text-blue-600" />;
}

function fileTypeBadge(fileType) {
  const upper = fileType?.toUpperCase() || "FILE";
  const colors = {
    pdf: "bg-red-100 text-red-700",
    docx: "bg-blue-100 text-blue-700",
    jpg: "bg-emerald-100 text-emerald-700",
    jpeg: "bg-emerald-100 text-emerald-700",
    png: "bg-emerald-100 text-emerald-700",
    webp: "bg-emerald-100 text-emerald-700",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${colors[fileType] || "bg-slate-100 text-slate-600"}`}>
      {upper}
    </span>
  );
}

function formatBytes(bytes) {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function Files() {
  const { role } = useAuth();
  const canEdit = role === "super_admin" || role === "dispatcher";

  const [manuals, setManuals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showUpload, setShowUpload] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await client.get("/manuals");
      setManuals(res.data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useAutoRefresh(load, 60000);

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await client.delete(`/manuals/${deleteTarget._id}`);
      toast.success(`"${deleteTarget.title}" deleted`);
      setDeleteTarget(null);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to delete");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Files</h1>
          <p className="text-sm text-slate-500">
            {manuals.length} manual{manuals.length !== 1 ? "s" : ""} — attach to ticket steps
          </p>
        </div>
        {canEdit && (
          <button
            onClick={() => setShowUpload(true)}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
          >
            <Plus size={16} /> Upload Manual
          </button>
        )}
      </div>

      {/* Loading skeleton */}
      {loading && (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-16 rounded-xl bg-slate-100 animate-pulse" />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && manuals.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-3">
          <FileText size={36} />
          <p className="text-sm">No manuals uploaded yet.</p>
          {canEdit && (
            <button
              onClick={() => setShowUpload(true)}
              className="text-sm text-blue-600 hover:underline"
            >
              Upload your first manual
            </button>
          )}
        </div>
      )}

      {/* Manuals list */}
      {!loading && manuals.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50 text-left">
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Title</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Type</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide hidden sm:table-cell">Filename</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">Size</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">Uploaded</th>
                <th className="px-4 py-3 w-16" />
              </tr>
            </thead>
            <tbody>
              {manuals.map((m) => (
                <tr key={m._id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {fileTypeIcon(m.file_type)}
                      <a
                        href={`${API_BASE}/manuals/${m._id}/file`}
                        target="_blank"
                        rel="noreferrer"
                        className="font-medium text-slate-800 hover:text-blue-600 hover:underline"
                      >
                        {m.title}
                      </a>
                    </div>
                  </td>
                  <td className="px-4 py-3">{fileTypeBadge(m.file_type)}</td>
                  <td className="px-4 py-3 hidden sm:table-cell text-xs text-slate-400 max-w-[180px] truncate">{m.original_filename}</td>
                  <td className="px-4 py-3 hidden md:table-cell text-xs text-slate-400">{formatBytes(m.file_size)}</td>
                  <td className="px-4 py-3 hidden md:table-cell text-xs text-slate-400">
                    {m.uploaded_at ? new Date(m.uploaded_at).toLocaleDateString() : "—"}
                  </td>
                  <td className="px-4 py-3">
                    {canEdit && (
                      <button
                        onClick={() => setDeleteTarget(m)}
                        className="rounded-md p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
                        title="Delete"
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Upload modal */}
      {showUpload && (
        <UploadModal
          onSave={() => { setShowUpload(false); load(); }}
          onClose={() => setShowUpload(false)}
        />
      )}

      {/* Delete confirm */}
      {deleteTarget && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={(e) => { if (e.target === e.currentTarget) setDeleteTarget(null); }}
        >
          <div className="w-full max-w-sm rounded-2xl bg-white shadow-2xl p-6 space-y-4">
            <div className="flex items-center gap-3 text-red-600">
              <AlertCircle size={20} />
              <h3 className="font-semibold">Delete Manual</h3>
            </div>
            <p className="text-sm text-slate-600">
              Delete <strong>"{deleteTarget.title}"</strong>? This cannot be undone. Any ticket steps linked to this manual will lose the document reference.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setDeleteTarget(null)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-60"
              >
                {deleting && <Loader2 size={14} className="animate-spin" />}
                {deleting ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function UploadModal({ onSave, onClose }) {
  const [title, setTitle] = useState("");
  const [file, setFile] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const fileInputRef = useRef(null);

  const ACCEPTED = ".pdf,.docx,.jpg,.jpeg,.png,.webp";

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (!title.trim()) { setError("Title is required."); return; }
    if (!file) { setError("Please select a file."); return; }

    setSaving(true);
    try {
      const fd = new FormData();
      fd.append("title", title.trim());
      fd.append("file", file);
      await client.post("/manuals", fd);
      toast.success("Manual uploaded");
      onSave();
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed.");
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="w-full max-w-sm rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <h2 className="font-semibold text-slate-900">Upload Manual</h2>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-100">
            <X size={18} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Title *</label>
            <input
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              placeholder="e.g. Glass Washer Maintenance Manual"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">File *</label>
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED}
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="flex w-full items-center justify-center gap-2 rounded-lg border-2 border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500 hover:border-blue-400 hover:text-blue-600 transition-colors"
            >
              <Upload size={16} />
              {file ? file.name : "Click to choose file (PDF, DOCX, JPG, PNG, WEBP)"}
            </button>
            {file && (
              <p className="mt-1 text-xs text-slate-400">{formatBytes(file.size)}</p>
            )}
          </div>
          {error && (
            <div className="flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              <AlertCircle size={14} /> {error}
            </div>
          )}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              {saving && <Loader2 size={14} className="animate-spin" />}
              {saving ? "Uploading…" : "Upload"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
