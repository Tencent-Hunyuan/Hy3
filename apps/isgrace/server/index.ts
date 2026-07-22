import express from 'express';
import cors from 'cors';
import { router } from './routes';

const app = express();

app.set('trust proxy', 'loopback');
app.use(cors({ origin: process.env.CLIENT_ORIGIN ?? 'http://localhost:5173', credentials: true }));
app.use(express.json({ limit: '25mb' }));
app.use('/api', router);

const port = process.env.PORT ? parseInt(process.env.PORT) : 3001;
// Bind to loopback only (both IPv4 + IPv6 via the 'localhost' hostname) — never
// reachable from outside the box, regardless of firewall config. The public
// nginx/Caddy reverse proxy on the same machine is the only thing that talks to it.
const host = process.env.HOST ?? 'localhost';
app.listen(port, host, () => {
  console.log(`[isgrace-server] listening on http://${host}:${port}`);
});
