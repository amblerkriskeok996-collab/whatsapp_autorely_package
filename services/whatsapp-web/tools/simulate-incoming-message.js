#!/usr/bin/env node

const fetch = require('node-fetch');

const DEFAULT_API_URL = process.env.N8N_WEBHOOK_URL || 'http://localhost:3000/webhook/whatsapp-workflow';
const DEFAULT_REPLY_URL = process.env.REPLY_WEBHOOK_URL || 'http://localhost:8082/webhook/reply';
const DEFAULT_FROM = '+86 176 2862 7274';
const DEFAULT_BODY = '~1326535786lm';
const DEFAULT_TO = process.env.SIMULATED_TO || 'self@c.us';
const DEFAULT_REPLY_MESSAGE = process.env.SIMULATED_REPLY_MESSAGE || '';

function parseArgs(argv) {
    const args = {};
    for (let i = 0; i < argv.length; i += 1) {
        const arg = argv[i];
        if (!arg.startsWith('--')) continue;

        if (arg === '--dry-run') {
            args.dryRun = true;
            continue;
        }
        if (arg === '--with-reply') {
            args.withReply = true;
            continue;
        }

        const key = arg.slice(2);
        const next = argv[i + 1];
        if (!next || next.startsWith('--')) {
            throw new Error(`Missing value for option: ${arg}`);
        }
        args[key] = next;
        i += 1;
    }
    return args;
}

function normalizePhone(raw) {
    const trimmed = String(raw || '').trim();
    if (!trimmed) {
        throw new Error('Phone number is empty');
    }
    const hasPlus = trimmed.startsWith('+');
    const digits = trimmed.replace(/\D/g, '');
    if (!digits) {
        throw new Error(`Invalid phone number: ${raw}`);
    }
    return `${hasPlus ? '+' : ''}${digits}`;
}

function toWhatsappId(rawPhone) {
    const normalized = normalizePhone(rawPhone);
    const digitsOnly = normalized.replace(/^\+/, '');
    return `${digitsOnly}@c.us`;
}

function buildPayload({ from, to, body }) {
    const fromId = toWhatsappId(from);
    const toId = to.includes('@') ? to : toWhatsappId(to);

    return {
        from: fromId,
        to: toId,
        body,
        type: 'chat',
        timestamp: Math.floor(Date.now() / 1000),
        author: fromId,
        isGroup: false,
        hasMedia: false,
        fromMe: false
    };
}

async function postJson(url, payload) {
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    });

    const responseText = await response.text();

    return {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok,
        body: responseText
    };
}

async function main() {
    const args = parseArgs(process.argv.slice(2));
    const apiUrl = args['api-url'] || DEFAULT_API_URL;
    const replyUrl = args['reply-url'] || DEFAULT_REPLY_URL;
    const from = args.from || DEFAULT_FROM;
    const to = args.to || DEFAULT_TO;
    const body = args.body || DEFAULT_BODY;
    const withReply = Boolean(args.withReply || args['reply-message'] || DEFAULT_REPLY_MESSAGE);
    const replyMessage = args['reply-message'] || DEFAULT_REPLY_MESSAGE || `自动回复测试：已收到 "${body}"`;

    const payload = buildPayload({ from, to, body });

    console.log('Step 1/2 - Simulated incoming message payload:');
    console.log(JSON.stringify(payload, null, 2));
    console.log(`Inbound API: ${apiUrl}`);

    if (args.dryRun) {
        console.log('Dry run enabled. Request was not sent.');
        return;
    }

    const inboundResult = await postJson(apiUrl, payload);
    console.log(`Inbound response: ${inboundResult.status} ${inboundResult.statusText}`);
    console.log(inboundResult.body || '<empty>');

    if (!inboundResult.ok) {
        process.exitCode = 1;
        return;
    }

    if (!withReply) {
        console.log('Step 2/2 skipped. Pass --with-reply to force sending a reply back to the same user.');
        return;
    }

    const replyPayload = {
        to: payload.from,
        message: replyMessage
    };

    console.log('Step 2/2 - Triggering reply webhook payload:');
    console.log(JSON.stringify(replyPayload, null, 2));
    console.log(`Reply API: ${replyUrl}`);

    const replyResult = await postJson(replyUrl, replyPayload);
    console.log(`Reply response: ${replyResult.status} ${replyResult.statusText}`);
    console.log(replyResult.body || '<empty>');

    if (!replyResult.ok) {
        process.exitCode = 1;
    }
}

module.exports = {
    parseArgs,
    normalizePhone,
    toWhatsappId,
    buildPayload
};

if (require.main === module) {
    main().catch((error) => {
        console.error('Simulation failed:', error.message);
        process.exitCode = 1;
    });
}
