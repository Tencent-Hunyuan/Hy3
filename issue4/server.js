// server.js
// Hy3 深度研究助手 — 入口文件

const { createApp, PORT, log } = require('./src/hy3-client');
const { setupResearch } = require('./src/research');
const { setupTranslate } = require('./src/translator');

const app = createApp();
setupResearch(app);
setupTranslate(app);

// ==================== 启动服务 ====================
const server = app.listen(PORT, () => {
  log('Server running at http://localhost:' + PORT);
});

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    log('Error: Port ' + PORT + ' is already in use.');
    log('Please stop the existing process or use a different port.');
    process.exit(1);
  } else {
    throw err;
  }
});
