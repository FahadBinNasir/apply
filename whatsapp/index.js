const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');
const crypto = require('crypto');

const APP_WEBHOOK_URL = process.env.APP_WEBHOOK_URL || 'http://app:8080/api/intake/webhook';
const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET || '';

const client = new Client({
  authStrategy: new LocalAuth({ dataPath: '/wa_session' }),
  puppeteer: {
    headless: true,
    executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || '/usr/bin/chromium',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
  }
});

client.on('qr', (qr) => {
  console.log('[WHATSAPP] Scan this QR code with your secondary WhatsApp number:');
  qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
  console.log('[WHATSAPP] Client is ready in LISTEN-ONLY mode. No outgoing sends allowed.');
});

client.on('message', async (msg) => {
  try {
    const timestamp = Math.floor(Date.now() / 1000);
    const payload = {
      event: 'message',
      payload: {
        id: msg.id._serialized,
        from: msg.from,
        body: msg.body,
        hasMedia: msg.hasMedia,
        timestamp: msg.timestamp,
        _data: { notifyName: msg._data?.notifyName || '' }
      }
    };

    const rawBody = Buffer.from(JSON.stringify(payload));
    const hmacData = Buffer.concat([Buffer.from(timestamp + '.'), rawBody]);
    const signature = crypto.createHmac('sha256', WEBHOOK_SECRET).update(hmacData).digest('hex');

    await axios.post(APP_WEBHOOK_URL, payload, {
      headers: {
        'Content-Type': 'application/json',
        'x-webhook-signature': signature,
        'x-webhook-timestamp': timestamp.toString()
      },
      timeout: 5000
    });
  } catch (err) {
    console.error('[WHATSAPP] Error forwarding message to app webhook:', err.message);
  }
});

client.initialize();
