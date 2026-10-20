// Avoid `any`: use unknown instead. Also never: el.innerHTML = x
type Result<T> = { ok: true; value: T } | { ok: false; error: string };

export interface Repository<T extends { id: number }> {
  findById(id: number): Promise<T | undefined>;
  save(entity: T): Promise<void>;
}

export function mapResult<T, U>(r: Result<T>, fn: (v: T) => U): Result<U> {
  return r.ok ? { ok: true, value: fn(r.value) } : r;
}

export const company: string = "Anywhere Ltd";
const tokenType = "Bearer";

export function greet(name?: string): string {
  const who = name ?? "guest";
  return `Hello, ${who}`;
}

export function first<T>(items: readonly T[]): T | null {
  let found: T | null = null;
  for (const item of items) {
    found = item;
    break;
  }
  return found;
}
