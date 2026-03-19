"use client";

type TopicChipProps = {
  label: string;
  onClick?: () => void;
  onRemove?: () => void;
};

export default function TopicChip({ label, onClick, onRemove }: TopicChipProps) {
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full bg-[#C8D5B9] px-3 py-1 text-sm font-medium transition ${
        onClick ? "cursor-pointer hover:bg-[#8FC0A9]" : ""
      }`}
      style={{ color: "#0f172a" }}
      onClick={onClick}
    >
      <span>{label}</span>
      {onRemove && (
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            onRemove();
          }}
          className="rounded-full px-1 text-sm hover:bg-rose-100 hover:text-rose-600"
          style={{ color: "#334155" }}
          aria-label={`Remove ${label}`}
        >
          ×
        </button>
      )}
    </span>
  );
}
