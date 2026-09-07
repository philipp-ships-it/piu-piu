/** Statische Vorschau ohne Pakete. Nur docs/ wird auf localhost ausgeliefert. */
import {createServer} from 'node:http';
import {readFile, stat} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../docs');
const types = {'.html':'text/html; charset=utf-8', '.css':'text/css; charset=utf-8', '.js':'text/javascript; charset=utf-8', '.svg':'image/svg+xml', '.zip':'application/zip'};
const server = createServer(async (request, response) => {
  try {
    const url = new URL(request.url, 'http://localhost');
    let relative = decodeURIComponent(url.pathname).replace(/^\/+/, '') || 'index.html';
    const filename = path.resolve(root, relative);
    if (!filename.startsWith(root + path.sep)) { response.writeHead(403); response.end('Zugriff verweigert'); return; }
    const info = await stat(filename);
    if (!info.isFile()) throw new Error('Keine Datei');
    response.setHeader('Content-Type', types[path.extname(filename)] || 'application/octet-stream');
    response.setHeader('X-Content-Type-Options', 'nosniff');
    response.setHeader('Cache-Control', 'no-store');
    response.end(await readFile(filename));
  } catch { response.writeHead(404); response.end('Datei nicht gefunden'); }
});
server.listen(Number(process.env.PORT || 4173), '127.0.0.1', () => console.log('PIU PIU: http://127.0.0.1:' + server.address().port));
