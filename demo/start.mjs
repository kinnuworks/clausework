// Start the unmodified stage-4 server, wait until it is healthy, then seed demo data.
import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";
const port = process.env.PORT || "8080";
const base = `http://127.0.0.1:${port}`;
const server = spawn("node", ["src/server.js"], { cwd: "/app", stdio: "inherit", env: process.env });
server.on("exit", (code) => process.exit(code ?? 1));
for (const sig of ["SIGTERM", "SIGINT"]) process.on(sig, () => server.kill(sig));
const seed = readFileSync("/demo/seed.json", "utf8");
for (let i = 0; i < 120; i++) {
  try {
    const h = await fetch(`${base}/health`);
    if (h.ok) {
      const r = await fetch(`${base}/_test/reset`, { method: "POST", headers: { "content-type": "application/json" }, body: seed });
      console.log(`demo data loaded: ${r.status}`);
      break;
    }
  } catch {}
  await new Promise((r) => setTimeout(r, 500));
}
