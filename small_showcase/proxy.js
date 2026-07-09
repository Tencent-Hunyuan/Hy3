#!/usr/bin/env node
/**
 * 小说设定编写器 · 本地 CORS 代理（可选）
 *
 * 用途：当浏览器直连混元 API 被跨域（CORS）拦截时使用。
 * 仅在你本机运行，转发你的请求，密钥不经过任何第三方。
 *
 * 使用步骤：
 *   1. 安装 Node.js（已装可跳过）
 *   2. 终端运行：node proxy.js
 *   3. 在程序「① API 设置」里把 Base URL 改为：http://localhost:8787/v1
 *   4. 正常生成小说设定即可
 *
 * 关闭：Ctrl + C
 */

const http = require('http');
const https = require('https');

const PORT = 8787;
const TARGET_HOST = 'api.hunyuan.cloud.tencent.com';

const server = http.createServer((req, res) => {
  // 放开跨域
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }

  // 仅转发 /v1 开头的路径
  const path = req.url.startsWith('/v1') ? req.url : ('/v1' + req.url);

  const proxyReq = https.request({
    host: TARGET_HOST,
    path,
    method: req.method,
    headers: {
      'Content-Type': req.headers['content-type'] || 'application/json',
      'Authorization': req.headers['authorization'] || ''
    }
  }, proxyRes => {
    res.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(res);
  });

  proxyReq.on('error', err => {
    res.writeHead(502, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('代理转发失败：' + err.message);
  });

  req.pipe(proxyReq);
});

server.listen(PORT, () => {
  console.log('✓ 本地 CORS 代理已启动： http://localhost:' + PORT);
  console.log('  请将程序 Base URL 设置为： http://localhost:' + PORT + '/v1');
});
