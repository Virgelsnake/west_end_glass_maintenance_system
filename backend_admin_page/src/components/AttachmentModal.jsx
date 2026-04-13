import { useState } from "react";
import { X, FileText, Send } from "lucide-react";

export default function AttachmentModal({
  isOpen,
  manuals = [],
  onConfirm,
  onClose,
}) {
  const [selectedManualId, setSelectedManualId] = useState("");
  const [sendViaWa, setSendViaWa] = useState(false);

  function handleConfirm() {
    if (!selectedManualId) return;
    const manual = manuals.find((m) => m._id === selectedManualId);
    onConfirm({
      manual_id: selectedManualId,
      manual_title: manual?.title || null,
      send_manual_via_whatsapp: sendViaWa,
    });
    setSelectedManualId("");
    setSendViaWa(false);
  }

  function handleClose() {
    setSelectedManualId("");
    setSendViaWa(false);
    onClose();
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="flex items-center justify-between p-4 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">Select Attachment</h2>
          <button
            onClick={handleClose}
            className="text-slate-400 hover:text-slate-600"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-4 space-y-3">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-2">
              Available Documents
            </label>
            <select
              value={selectedManualId}
              onChange={(e) => setSelectedManualId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">— choose a document —</option>
              {manuals.map((m) => (
                <option key={m._id} value={m._id}>
                  {m.title}
                </option>
              ))}
            </select>
          </div>

          <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
            <input
              type="checkbox"
              checked={sendViaWa}
              onChange={(e) => setSendViaWa(e.target.checked)}
              className="rounded"
            />
            <Send size={14} />
            Send to technician via WhatsApp
          </label>
        </div>

        <div className="flex gap-2 p-4 border-t border-slate-200 bg-slate-50">
          <button
            onClick={handleClose}
            className="flex-1 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={!selectedManualId}
            className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <FileText size={16} />
            Add Attachment
          </button>
        </div>
      </div>
    </div>
  );
}
