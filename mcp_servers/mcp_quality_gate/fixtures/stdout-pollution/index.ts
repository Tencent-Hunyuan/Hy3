import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

process.stdout.write('fixture startup banner must be on stderr\n');

const server = new McpServer({ name: 'fixture-polluted', version: '1.0.0' });
await server.connect(new StdioServerTransport());
