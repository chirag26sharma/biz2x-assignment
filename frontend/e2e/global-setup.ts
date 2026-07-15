const apiBase = process.env.PLAYWRIGHT_API_BASE ?? "http://localhost:5001";

export default async function globalSetup() {
  const maxAttempts = 45;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      const ready = await fetch(`${apiBase}/ready`);
      if (!ready.ok) throw new Error(`ready status ${ready.status}`);
      const users = await fetch(`${apiBase}/api/auth/users`);
      if (!users.ok) throw new Error(`users status ${users.status}`);
      return;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }
  throw new Error(`Backend API not ready at ${apiBase}`);
}
