/**
 * Raw PDF / image payloads for the config studio (quota-limited browser localStorage).
 */
export type LocalImportedFile = {
  id: string;
  name: string;
  mimeType: string;
  dataUrl: string;
};

/** localStorage key for files attached to the Curriculum panel */
export const LS_IMPORT_CURRICULUM = "curriculum" as const;
/** localStorage key for files attached to the Content panel */
export const LS_IMPORT_CONTENT = "content" as const;

export type LocalImportBucket = typeof LS_IMPORT_CURRICULUM | typeof LS_IMPORT_CONTENT;

export function truncateFileLabel(name: string, maxChars = 15): string {
  if (name.length <= maxChars) return name;
  return `${name.slice(0, Math.max(maxChars - 3, 1)).trimEnd()}…`;
}

export function readImportedFiles(bucket: LocalImportBucket): LocalImportedFile[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(bucket);
    if (!raw?.trim()) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isImportedFileShape);
  } catch {
    return [];
  }
}

export function writeImportedFiles(
  bucket: LocalImportBucket,
  files: LocalImportedFile[],
): void {
  if (typeof window === "undefined") return;
  if (files.length === 0) {
    localStorage.removeItem(bucket);
    return;
  }
  localStorage.setItem(bucket, JSON.stringify(files));
}

function isImportedFileShape(x: unknown): x is LocalImportedFile {
  if (x === null || typeof x !== "object") return false;
  const o = x as Record<string, unknown>;
  return (
    typeof o.id === "string" &&
    typeof o.name === "string" &&
    typeof o.mimeType === "string" &&
    typeof o.dataUrl === "string"
  );
}

export function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}
