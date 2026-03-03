const { expect } = require('chai');
const {
    extractPhoneFromJid,
    buildIncomingWebhookPayload
} = require('../src/webhookPayload');

describe('webhook-payload', () => {
    it('extracts phone from whatsapp jid', () => {
        expect(extractPhoneFromJid('8617628627274@c.us')).to.equal('8617628627274');
        expect(extractPhoneFromJid('foo@bar')).to.equal('');
    });

    it('builds webhook payload with sender/recipient/message metadata', () => {
        const payload = buildIncomingWebhookPayload({
            from: '8617628627274@c.us',
            to: '',
            body: 'How much does bypass surgery cost?',
            type: 'chat',
            timestamp: 1772179000,
            author: '8617628627274@c.us',
            isGroup: false,
            hasMedia: false,
            fromMe: false,
            _data: { notifyName: 'Alice' },
            id: { _serialized: 'false_8617628627274@c.us_ABC' }
        }, '8613000000000@c.us');

        expect(payload.to).to.equal('8613000000000@c.us');
        expect(payload.chatId).to.equal('8617628627274@c.us');
        expect(payload.text).to.equal('How much does bypass surgery cost?');
        expect(payload.message).to.equal('How much does bypass surgery cost?');
        expect(payload.question).to.equal('How much does bypass surgery cost?');
        expect(payload.userPhone).to.equal('8617628627274');
        expect(payload.senderAccount.jid).to.equal('8617628627274@c.us');
        expect(payload.senderAccount.phone).to.equal('8617628627274');
        expect(payload.senderAccount.pushName).to.equal('Alice');
        expect(payload.recipientAccount.jid).to.equal('8613000000000@c.us');
        expect(payload.recipientAccount.phone).to.equal('8613000000000');
        expect(payload.messageContent.text).to.equal('How much does bypass surgery cost?');
        expect(payload.sentAt.unix).to.equal(1772179000);
        expect(new Date(payload.sentAt.iso).getTime()).to.be.greaterThan(0);
    });

    it('keeps quoted message details when present', () => {
        const payload = buildIncomingWebhookPayload({
            from: '8617628627274@c.us',
            to: '8613000000000@c.us',
            body: 'Please refer to my previous question',
            quotedMessage: {
                body: 'How much does bypass surgery cost?',
                author: '8613800000000@c.us'
            }
        });

        expect(payload.quotedMessage).to.deep.equal({
            body: 'How much does bypass surgery cost?',
            author: '8613800000000@c.us'
        });
    });
});
