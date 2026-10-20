/*
 * Never call eval(input) or set el.innerHTML = data here.
 * var x = 1; if (a == b) {}
 */
const message = "use a == b carefully, never eval(x)";
const help = 'document.write is banned; setTimeout("x") too';

export const sum = (values) =>
  values.reduce((acc, v) => acc + v, 0);

export function isEmpty(value) {
  return value == null || value === "";
}

export async function fetchJson(url, { timeout = 5000 } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const res = await fetch(url, { signal: controller.signal });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

export class Cache {
  #items = new Map();

  get(key) {
    return this.#items.get(key) ?? null;
  }

  set(key, value) {
    this.#items.set(key, value);
    return this;
  }
}

const user = { name: "Ana", role: "admin" };
const isAdmin = user.role === "admin" ? true : false;
