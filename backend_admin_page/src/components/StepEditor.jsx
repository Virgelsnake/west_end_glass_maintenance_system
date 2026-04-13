import { useState, useEffect } from "react";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Plus, X, FileText } from "lucide-react";
import client from "../api/client";
import AttachmentModal from "./AttachmentModal";

const COMPLETION_TYPES = ["confirmation", "note", "photo", "attachment"];

// ── Single sortable row ───────────────────────────────────────────────────────
function StepRow({ item, withSections, onUpdate, onRemove }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: item.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 10 : undefined,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-1.5 rounded-md bg-white border border-slate-200 px-2 py-1.5 mb-1 group"
    >
      {/* Drag handle */}
      <button
        type="button"
        className="text-slate-300 hover:text-slate-500 cursor-grab active:cursor-grabbing touch-none shrink-0"
        {...attributes}
        {...listeners}
        tabIndex={-1}
      >
        <GripVertical size={14} />
      </button>

      {/* Inline section input (dailys only) */}
      {withSections && (
        <input
          value={item.section_name || ""}
          onChange={(e) => onUpdate("section_name", e.target.value)}
          placeholder="Section"
          className="w-24 shrink-0 rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[10px] text-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-400"
        />
      )}

      {/* Label */}
      <input
        value={item.label}
        onChange={(e) => onUpdate("label", e.target.value)}
        placeholder="Item label…"
        className="flex-1 min-w-0 text-xs bg-transparent focus:outline-none text-slate-700 placeholder:text-slate-300"
      />

      {/* Completion type */}
      <select
        value={item.completion_type}
        onChange={(e) => onUpdate("completion_type", e.target.value)}
        className="text-xs rounded border border-slate-200 bg-white px-1 py-0.5 text-slate-600 focus:outline-none shrink-0"
      >
        {COMPLETION_TYPES.map((ct) => (
          <option key={ct} value={ct}>{ct}</option>
        ))}
      </select>

      {/* Manual doc badge */}
      {item.completion_type === "attachment" && item.manual_title && (
        <span className="flex items-center gap-0.5 text-[10px] text-blue-600 bg-blue-50 border border-blue-200 rounded px-1.5 py-0.5 shrink-0 max-w-[100px] truncate" title={item.manual_title}>
          <FileText size={10} />{item.manual_title}
        </span>
      )}
      {item.completion_type === "attachment" && item.send_manual_via_whatsapp && (
        <span className="text-[10px] text-green-600 bg-green-50 border border-green-200 rounded px-1.5 py-0.5 shrink-0">WA</span>
      )}

      {/* Delete */}
      <button
        type="button"
        onClick={onRemove}
        className="text-slate-300 hover:text-red-500 shrink-0 ml-0.5"
      >
        <X size={12} />
      </button>
    </div>
  );
}

// ── StepEditor ────────────────────────────────────────────────────────────────
/**
 * Controlled step/item editor with drag-to-reorder.
 *
 * Props:
 *   items        – { id, label, completion_type, section_name? }[]
 *   onChange     – (updatedItems) => void
 *   withSections – boolean: show inline section input on each row
 *   label        – string: section header label (default "Check Items")
 */
export default function StepEditor({
  items = [],
  onChange,
  withSections = false,
  label = "Check Items",
}) {
  const [newLabel, setNewLabel] = useState("");
  const [newType, setNewType] = useState("confirmation");
  const [manuals, setManuals] = useState([]);
  const [newManualId, setNewManualId] = useState("");
  const [showAttachmentModal, setShowAttachmentModal] = useState(false);
  const [newSendViaWa, setNewSendViaWa] = useState(false);

  useEffect(() => {
    client.get("/manuals").then((r) => setManuals(r.data)).catch(() => {});
  }, []);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  function handleDragEnd(event) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = items.findIndex((i) => i.id === active.id);
    const newIndex = items.findIndex((i) => i.id === over.id);
    onChange(arrayMove(items, oldIndex, newIndex));
  }

  function updateItem(id, field, value) {
    onChange(items.map((i) => (i.id === id ? { ...i, [field]: value } : i)));
  }

  function removeItem(id) {
    onChange(items.filter((i) => i.id !== id));
  }

  function addItem() {
    if (!nnewItem = {
      id: crypto.randomUUID(),
      label: newLabel.trim(),
      completion_type: newType,
      ...(withSections ? { section_name: "" } : {}),
    };
    onChange([...items, newItem]);
    setNewLabel("");
    setNewType("confirmation");
  }

  function handleAttachmentSelect(attachment) {
    if (!newLabel.trim()) return;
    const newItem = {
      id: crypto.randomUUID(),
      label: newLabel.trim(),
      completion_type: "attachment",
      ...(withSections ? { section_name: "" } : {}),
      manual_id: attachment.manual_id,
      manual_title: attachment.manual_title,
      send_manual_via_whatsapp: attachment.send_manual_via_whatsapp,
    };
    onChange([...items, newItem]);
    setNewLabel("");
    setNewType("confirmation");
    setShowAttachmentModal"");
    setNewSendViaWa(false);
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <label className="text-xs font-medium text-slate-600">
          {label} ({items.length})
        </label>
        {withSections && (
          <span className="text-[10px] text-slate-400">Drag to reorder · edit section name inline</span>
        )}
        {!withSections && (
          <span className="text-[10px] text-slate-400">Drag to reorder</span>
        )}
      </div>

      {/* Add row — above the list */}
      <div className="flex gap-2 mb-2">
        <input
          value={newLabel}
          onChange={(e) => setNewLabel(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addItem(); } }}
          placeholder={withSections ? "New check item label…" : "New step description…"}
          className="flex-1 rounded-lg border border-slate-300 px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <select
          value={newType}
          onChange={(e) => { setNewType(e.target.value); }}
          className="text-xs rounded-lg border border-slate-300 bg-white px-1.5 py-1.5 text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500 shrink-0"
        >
          {COMPLETION_TYPES.map((ct) => (
            <option key={ct} value={ct}>{ct}</option>
          ))}
        </select>
        {newType === "attachment" && (
          <button
            type="button"
            onClick={() => setShowAttachmentModal(true)}
            className="flex items-center gap-1 rounded-lg bg-purple-50 border border-purple-200 px-3 py-1.5 text-xs font-medium text-purple-700 hover:bg-purple-100 shrink-0"
          >
            <FileText size={12} /> Pick Attachment
          </button>
        )}
        <button
          type="button"
          onClick={() => {
            if (newType === "attachment") {
              setShowAttachmentModal(true);
            } else {
              addItem();
            }
          }}
          title="Add item"
          className="flex items-center gap-1 rounded-lg bg-blue-50 border border-blue-200 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-100"
        >
          <Plus size={12} /> Add
        </button>
      </div>

      {/* List */}
      {items.length === 0 ? (
        <p className="text-xs text-slate-400 py-3 text-center border border-dashed border-slate-200 rounded-lg">
          No items yet — type above and press Add or Enter.
        </p>
      ) : (
        <div className="max-h-72 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50 p-2">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext items={items.map((i) => i.id)} strategy={verticalListSortingStrategy}>
              {items.map((item) => (
                <StepRow
                  key={item.id}
                  item={item}
                  withSections={withSections}
                  onUpdate={(field, value) => updateItem(item.id, field, value)}
                  onRemove={() => removeItem(item.id)}
                />
              ))}
            </SortableContext>
          </DndContext>
        </div>
      )}

      <AttachmentModal
        isOpen={showAttachmentModal}
        manuals={manuals}
        onConfirm={handleAttachmentSelect}
        onClose={() => setShowAttachmentModal(false)}
      />
    </div>
  );
}

