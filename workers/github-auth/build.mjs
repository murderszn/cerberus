import { cp, mkdir, rm } from 'node:fs/promises';
const root = new URL('../../', import.meta.url);
const out = new URL('./public/', import.meta.url);
await rm(out, { recursive: true, force: true });
await mkdir(out, { recursive: true });
// Explicit public assets only; never publish the repo, secrets, or account data.
for (const file of ['index.html', 'agent.html', 'shop.html', 'releases.html', 'cerberus-classic.html', 'favicon.ico', 'logo.png', 'assets', 'documentation']) {
  await cp(new URL(file, root), new URL(file, out), { recursive: true });
}
