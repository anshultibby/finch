/**
 * Robinhood agentic trading — on-device OAuth for the native app.
 *
 * Robinhood's agent OAuth client only allowlists LOOPBACK redirects
 * (http://127.0.0.1:PORT) — the RFC 8252 native-app flow, exactly how Claude
 * Code connects. Hosted https callbacks are rejected, so this MUST run on the
 * user's device: we start a tiny loopback HTTP listener, open the consent page
 * in an in-app browser (which can reach the app's own 127.0.0.1), capture the
 * `code`, then hand it to the backend to exchange + store.
 *
 * ⚠️ Requires native modules + an EAS dev build (NOT Expo Go):
 *     npx expo install expo-crypto expo-web-browser
 *     npm install react-native-tcp-socket   # then rebuild the dev client
 *
 * This file is verified in design against a working desktop loopback prototype;
 * the in-app iOS listener still needs an on-device test.
 */
import { Platform } from 'react-native';
import * as Crypto from 'expo-crypto';
import * as WebBrowser from 'expo-web-browser';
import { robinhoodApi } from './api';

// react-native-tcp-socket has no web implementation — load it lazily so the
// web bundle (React Native Web) doesn't break. The connect flow is native-only.
let TcpSocket: any;
function getTcpSocket(): any {
  if (Platform.OS === 'web') {
    throw new Error('Robinhood connect is only available in the native app');
  }
  if (!TcpSocket) {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const mod = require('react-native-tcp-socket');
    TcpSocket = mod?.default ?? mod;
  }
  return TcpSocket;
}

const REGISTER_URL = 'https://agent.robinhood.com/oauth/trading/register';
const AUTHORIZE_URL = 'https://robinhood.com/oauth';
const SCOPE = 'internal';
const PORT = 8765;
const REDIRECT_URI = `http://127.0.0.1:${PORT}/callback`;
const TIMEOUT_MS = 3 * 60 * 1000; // allow time for Robinhood's device approval

function toBase64Url(b64: string): string {
  return b64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

async function randomBase64Url(bytes: number): Promise<string> {
  const buf = await Crypto.getRandomBytesAsync(bytes);
  // btoa over a binary string
  let bin = '';
  buf.forEach((c) => (bin += String.fromCharCode(c)));
  return toBase64Url(global.btoa ? global.btoa(bin) : Buffer.from(buf).toString('base64'));
}

async function makePkce(): Promise<{ verifier: string; challenge: string }> {
  const verifier = await randomBase64Url(32);
  const challengeB64 = await Crypto.digestStringAsync(
    Crypto.CryptoDigestAlgorithm.SHA256,
    verifier,
    { encoding: Crypto.CryptoEncoding.BASE64 },
  );
  return { verifier, challenge: toBase64Url(challengeB64) };
}

/** Start a one-shot loopback listener and resolve with the OAuth query params. */
function captureLoopbackCode(): Promise<{ code?: string; state?: string; error?: string }> {
  return new Promise((resolve, reject) => {
    const server = getTcpSocket().createServer((socket: any) => {
      socket.on('data', (data: any) => {
        const req = data.toString();
        const match = req.match(/GET \/callback\?([^ ]*) /);
        socket.write(
          'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n' +
            '<html><body style="font-family:-apple-system;text-align:center;padding-top:60px">' +
            '<h2>Robinhood connected ✓</h2><p>Return to Finch.</p></body></html>',
        );
        socket.destroy();
        try { server.close(); } catch {}
        if (!match) return resolve({ error: 'no_callback' });
        const qs = new URLSearchParams(match[1]);
        resolve({
          code: qs.get('code') ?? undefined,
          state: qs.get('state') ?? undefined,
          error: qs.get('error') ?? undefined,
        });
      });
    });
    server.on('error', reject);
    server.listen({ port: PORT, host: '127.0.0.1' });
    setTimeout(() => { try { server.close(); } catch {}; reject(new Error('timed_out')); }, TIMEOUT_MS);
  });
}

async function registerClient(): Promise<string> {
  const res = await fetch(REGISTER_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      client_name: 'Finch iOS',
      redirect_uris: [REDIRECT_URI],
      grant_types: ['authorization_code', 'refresh_token'],
      response_types: ['code'],
      token_endpoint_auth_method: 'none',
    }),
  });
  const { client_id } = await res.json();
  if (!client_id) throw new Error('registration_failed');
  return client_id;
}

/**
 * Run the full on-device connect flow. Opens Robinhood consent, captures the
 * code on loopback, and posts it to the backend to store the user's tokens.
 */
export async function connectRobinhood(userId: string): Promise<void> {
  const clientId = await registerClient();
  const { verifier, challenge } = await makePkce();
  const state = await randomBase64Url(9);

  const params = new URLSearchParams({
    response_type: 'code',
    client_id: clientId,
    redirect_uri: REDIRECT_URI,
    code_challenge: challenge,
    code_challenge_method: 'S256',
    scope: SCOPE,
    state,
  });

  const codePromise = captureLoopbackCode();
  // Open consent; user logs in, taps Allow, approves on their RH app. The
  // redirect to 127.0.0.1 is caught by codePromise above.
  WebBrowser.openBrowserAsync(`${AUTHORIZE_URL}?${params.toString()}`).catch(() => {});

  const result = await codePromise;
  WebBrowser.dismissBrowser().catch(() => {});

  if (result.error || !result.code || result.state !== state) {
    throw new Error(result.error || 'connect_failed');
  }
  await robinhoodApi.nativeExchange(userId, {
    code: result.code,
    code_verifier: verifier,
    client_id: clientId,
    redirect_uri: REDIRECT_URI,
  });
}
