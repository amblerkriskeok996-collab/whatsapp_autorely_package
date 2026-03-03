#!/usr/bin/env node

const fetch = require('node-fetch');

const FIXED_FROM_JID = '8617628627274@c.us';
const DEFAULT_TO = process.env.MOCK_TO || '8613000000000@c.us';
const DEFAULT_API_URL = process.env.MOCK_API_URL || 'http://localhost:3000/webhook/whatsapp-workflow';
const DEFAULT_BODY = 'mock incoming message from 8617628627274';

function parseArgs(argv) {
    const args = {};
    for (let i = 0; i < argv.length; i += 1) {
        const arg = argv[i];
        if (!arg.startsWith('--')) continue;
        if (arg === '--dry-run') {
            args.dryRun = true;
            continue;
        }
        const key = arg.slice(2);
        const value = argv[i + 1];
        if (!value || value.startsWith('--')) {
            throw new Error(`Missing value for option: ${arg}`);
        }
        args[key] = value;
        i += 1;
    }
    return args;
}

function toBoolean(value, defaultValue = true) {
    if (value === undefined || value === null || value === '') return defaultValue;
    if (typeof value === 'boolean') return value;
    const normalized = String(value).trim().toLowerCase();
    return !['0', 'false', 'no', 'n'].includes(normalized);
}

function buildMockPayload({ to, body, autoSendReply = true }) {
    const timestamp = Math.floor(Date.now() / 1000);
    return {
        event: 'whatsapp.incoming_message',
        source: 'whatsapp-web.js',
        chatId: FIXED_FROM_JID,
        from: FIXED_FROM_JID,
        to: String(to || DEFAULT_TO),
        body: String(body || DEFAULT_BODY),
        text: String(body || DEFAULT_BODY),
        message: String(body || DEFAULT_BODY),
        question: String(body || DEFAULT_BODY),
        type: 'chat',
        timestamp,
        author: FIXED_FROM_JID,
        isGroup: false,
        hasMedia: false,
        fromMe: false,
        autoSendReply: toBoolean(autoSendReply, true)
    };
}

async function postJson(url, payload) {
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    const text = await response.text();
    return {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok,
        body: text
    };
}

async function main() {
    const args = parseArgs(process.argv.slice(2));
    const apiUrl = args['api-url'] || DEFAULT_API_URL;
    const to = args.to || DEFAULT_TO;
    const body = args.body || DEFAULT_BODY;
    const payload = buildMockPayload({
        to,
        body,
        autoSendReply: args['auto-send']
    });

    console.log('Mock sender:', FIXED_FROM_JID);
    console.log('Target URL:', apiUrl);
    console.log('Payload:');
    console.log(JSON.stringify(payload, null, 2));

    if (args.dryRun) {
        console.log('Dry run enabled. Request not sent.');
        return;
    }

    const result = await postJson(apiUrl, payload);
    console.log(`Response: ${result.status} ${result.statusText}`);
    console.log(result.body || '<empty>');

    if (!result.ok) {
        process.exitCode = 1;
    }
}

module.exports = {
    FIXED_FROM_JID,
    parseArgs,
    buildMockPayload
};

if (require.main === module) {
    main().catch((error) => {
        console.error('Mock request failed:', error.message);
        process.exitCode = 1;
    });
}
