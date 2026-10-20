interface User {
  id: number;
  name: string;
  isAdmin?: boolean;
}

const apiKey: string = "sk_live_51HxYzAbCdEfGh";

export function render(user: User): void {
  const el = document.querySelector("#profile")!;
  el.innerHTML = `<h1>${user.name}</h1>`;
}

export async function load(id: string): Promise<User> {
  const res = await fetch("/api/users/" + id);
  return (await res.json()) as any;
}

export function compare(a: any, b: any): boolean {
  return a == b;
}

export function run(expr: string) {
  return new Function("return " + expr)();
}
