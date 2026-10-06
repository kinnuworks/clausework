'use strict';
// HTTP entry point: reads the request, dispatches through the route table and
// renders every result or error as JSON.

const http = require('http');
const { ApiError, notFound } = require('./errors');
const { match } = require('./routes');

const MAX_BODY = 16 * 1024 * 1024;

function send(res, status, body) {
  if (status === 204 || body === undefined) {
    res.writeHead(status);
    res.end();
    return;
  }
  const text = JSON.stringify(body);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(text),
  });
  res.end(text);
}

function sendError(res, err) {
  if (!(err instanceof ApiError)) {
    console.error(err);
    err = new ApiError(500, 'internal_error', 'internal error');
  }
  send(res, err.status, { error: { code: err.code, message: err.message } });
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on('data', (chunk) => {
      size += chunk.length;
      if (size <= MAX_BODY) chunks.push(chunk);
    });
    req.on('end', () => {
      if (size > MAX_BODY) reject(new ApiError(400, 'malformed_request', 'request body is too large'));
      else resolve(Buffer.concat(chunks).toString('utf8'));
    });
    req.on('error', reject);
  });
}

function decodeParams(params) {
  try {
    return params.map((p) => decodeURIComponent(p));
  } catch {
    throw notFound();
  }
}

async function handle(req, res) {
  try {
    const url = new URL(req.url, 'http://localhost');
    const rawBody = await readBody(req);
    const route = match(req.method, url.pathname);
    if (!route) throw notFound('no such endpoint');
    const ctx = {
      req, method: req.method, path: url.pathname, query: url.searchParams,
      params: decodeParams(route.params), rawBody,
    };
    const result = await route.handler(ctx);
    send(res, result.status, result.body);
  } catch (err) {
    sendError(res, err);
  }
}

const port = Number(process.env.PORT) || 8080;
const server = http.createServer((req, res) => { handle(req, res); });
server.keepAliveTimeout = 65000;
server.on('clientError', (err, socket) => {
  if (socket.writable) socket.end('HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n');
});
server.listen(port, '0.0.0.0', () => console.log(`tablekeeper listening on ${port}`));
