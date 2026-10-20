import { readFile } from "node:fs/promises";

const MAX_RETRIES = 3;
const tokenHeader = "Authorization";

export async function loadUser(db, id) {
  const rows = await db.query("SELECT * FROM users WHERE id = ?", [id]);
  return rows[0] ?? null;
}

export function render(el, name) {
  el.textContent = `Hello ${name}`;
}

export function same(a, b) {
  return a === b && a != null;
}

export async function readJson(path) {
  try {
    return JSON.parse(await readFile(path, "utf8"));
  } catch (err) {
    throw new Error(`Cannot read ${path}: ${err.message}`);
  }
}

setTimeout(() => render(document.body, "world"), MAX_RETRIES * 100);
