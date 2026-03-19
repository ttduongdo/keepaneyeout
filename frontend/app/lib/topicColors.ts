const BASE_PALETTE = ["#FAF3DD", "#C8D5B9", "#8FC0A9", "#68B0AB", "#4A7C59"];

export const TOPIC_COLORS: Record<string, string> = {
  ML: "#8FC0A9",
  Robotics: "#68B0AB",
  Security: "#4A7C59",
  Audio: "#C8D5B9"
};

function clamp(value: number) {
  return Math.max(0, Math.min(255, value));
}

function shade(hex: string, amount: number): string {
  const normalized = hex.replace("#", "");
  const num = parseInt(normalized, 16);
  const r = clamp((num >> 16) + amount);
  const g = clamp(((num >> 8) & 0xff) + amount);
  const b = clamp((num & 0xff) + amount);
  return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
}

export function isDarkColor(hex: string): boolean {
  const normalized = hex.replace("#", "");
  const num = parseInt(normalized, 16);
  const r = (num >> 16) & 0xff;
  const g = (num >> 8) & 0xff;
  const b = num & 0xff;
  const luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
  return luminance < 0.55;
}

const EXTENDED_PALETTE = [
  ...BASE_PALETTE,
  ...BASE_PALETTE.map((color) => shade(color, -16)),
  ...BASE_PALETTE.map((color) => shade(color, 12))
];

function hashTopic(topic: string): number {
  let hash = 0;
  for (let i = 0; i < topic.length; i += 1) {
    hash = (hash * 31 + topic.charCodeAt(i)) >>> 0;
  }
  return hash;
}

export function getTopicColor(topic?: string | null): string {
  if (!topic) {
    return BASE_PALETTE[0];
  }
  if (TOPIC_COLORS[topic]) {
    return TOPIC_COLORS[topic];
  }
  const index = hashTopic(topic) % EXTENDED_PALETTE.length;
  return EXTENDED_PALETTE[index];
}
