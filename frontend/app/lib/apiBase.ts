export function getApiBase(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (base && base.trim()) {
    return base.replace(/\/+$/, "");
  }
  if (typeof window !== "undefined") {
    console.warn("NEXT_PUBLIC_API_BASE_URL is not set. Falling back to http://localhost:8000");
  }
  return "http://localhost:8000";
}
