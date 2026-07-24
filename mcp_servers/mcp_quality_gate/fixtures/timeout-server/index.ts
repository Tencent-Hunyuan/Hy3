import { writeFileSync } from 'node:fs';

const pidFile = process.env.FIXTURE_PID_FILE;
if (pidFile !== undefined) {
  writeFileSync(pidFile, String(process.pid), 'utf8');
}

setInterval(() => undefined, 1000);
