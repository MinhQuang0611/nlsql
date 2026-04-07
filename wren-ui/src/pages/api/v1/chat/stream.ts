import type { NextApiRequest, NextApiResponse } from 'next';
import http from 'http';

/**
 * SSE Passthrough proxy for /api/v1/chat/stream
 *
 * Next.js rewrites() buffer the entire response before forwarding to client.
 * This API route acts as a true streaming passthrough by using Node.js http.request
 * directly, piping chunks to the response as they arrive.
 */
export const config = {
  api: {
    // Disable body parsing so we can forward raw body
    bodyParser: false,
    responseLimit: false,
  },
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse,
) {
  if (req.method !== 'POST') {
    res.status(405).end('Method Not Allowed');
    return;
  }

  const backendUrl = process.env.WREN_ENGINE_URL || 'http://app:8388';
  const url = new URL(`${backendUrl}/api/v1/chat/stream`);

  // Buffer the incoming body
  const bodyChunks: Buffer[] = [];
  await new Promise<void>((resolve, reject) => {
    req.on('data', (chunk: Buffer) => bodyChunks.push(chunk));
    req.on('end', resolve);
    req.on('error', reject);
  });
  const rawBody = Buffer.concat(bodyChunks);

  const options: http.RequestOptions = {
    hostname: url.hostname,
    port: url.port || 80,
    path: url.pathname,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(rawBody),
    },
  };

  return new Promise<void>((resolve, reject) => {
    const proxyReq = http.request(options, (proxyRes) => {
      // Set SSE response headers
      res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
        'X-Accel-Buffering': 'no',
      });

      // Pipe each chunk IMMEDIATELY to the client as it arrives
      proxyRes.on('data', (chunk: Buffer) => {
        res.write(chunk);
        // Force flush on each chunk
        if ((res as any).flush) (res as any).flush();
      });

      proxyRes.on('end', () => {
        res.end();
        resolve();
      });

      proxyRes.on('error', (err) => {
        console.error('[SSE Proxy] proxyRes error:', err);
        res.end();
        reject(err);
      });
    });

    proxyReq.on('error', (err) => {
      console.error('[SSE Proxy] proxyReq error:', err);
      res.status(502).end('Bad Gateway');
      reject(err);
    });

    // Handle client disconnect
    req.on('close', () => {
      proxyReq.destroy();
    });

    proxyReq.write(rawBody);
    proxyReq.end();
  });
}
