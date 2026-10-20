interface User {
  id: number;
  name: string;
}

const passwordLabel: string = "Password";

export function display(user: User, el: HTMLElement): void {
  el.textContent = user.name;
}

export function parse(raw: unknown): User | null {
  if (typeof raw === "object" && raw !== null && "id" in raw) {
    return raw as User;
  }
  return null;
}

export const isEqual = <T>(a: T, b: T): boolean => a === b;
