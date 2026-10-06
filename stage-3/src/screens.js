'use strict';
// Browser screens (stage 2): the four screen routes serve the single page
// ui/index.html, and /static/<path> serves files from the ui directory.

const fs = require('fs/promises');
const path = require('path');
const { notFound } = require('./errors');

const UI_DIR = path.resolve(__dirname, '..', 'ui');

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2',
  '.woff': 'font/woff',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.txt': 'text/plain; charset=utf-8',
};

async function fileResult(file) {
  let content;
  try {
    content = await fs.readFile(file);
  } catch {
    throw notFound('no such file');
  }
  const type = TYPES[path.extname(file).toLowerCase()] || 'application/octet-stream';
  return { status: 200, raw: content, contentType: type };
}

function screen() {
  return fileResult(path.join(UI_DIR, 'index.html'));
}

// `relative` is the decoded path after /static/; it must stay inside UI_DIR.
function staticFile(relative) {
  const file = path.resolve(UI_DIR, relative);
  if (!file.startsWith(UI_DIR + path.sep)) throw notFound('no such file');
  return fileResult(file);
}

module.exports = { screen, staticFile };
