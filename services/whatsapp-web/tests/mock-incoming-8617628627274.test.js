const { expect } = require('chai');
const {
    FIXED_FROM_JID,
    buildMockPayload
} = require('../tools/mock-incoming-8617628627274');

describe('mock-incoming-8617628627274 tool', () => {
    it('uses fixed sender jid for mock user', () => {
        expect(FIXED_FROM_JID).to.equal('8617628627274@c.us');
    });

    it('builds payload with fixed from/chatId and configurable body', () => {
        const payload = buildMockPayload({
            to: '8613000000000@c.us',
            body: 'test incoming message'
        });

        expect(payload.chatId).to.equal('8617628627274@c.us');
        expect(payload.from).to.equal('8617628627274@c.us');
        expect(payload.author).to.equal('8617628627274@c.us');
        expect(payload.to).to.equal('8613000000000@c.us');
        expect(payload.body).to.equal('test incoming message');
        expect(payload.fromMe).to.equal(false);
        expect(payload.isGroup).to.equal(false);
        expect(payload.autoSendReply).to.equal(true);
    });

    it('supports disabling auto send reply for dry integration testing', () => {
        const payload = buildMockPayload({
            to: '8613000000000@c.us',
            body: 'test incoming message',
            autoSendReply: false
        });

        expect(payload.autoSendReply).to.equal(false);
    });
});
