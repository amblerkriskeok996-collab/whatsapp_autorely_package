const { expect } = require('chai');
const {
    parseArgs,
    normalizePhone,
    toWhatsappId,
    buildPayload
} = require('../tools/simulate-incoming-message');

describe('simulate-incoming-message tool', () => {
    it('normalizes phone and maps to whatsapp id', () => {
        expect(normalizePhone('+86 176 2862 7274')).to.equal('+8617628627274');
        expect(toWhatsappId('+86 176 2862 7274')).to.equal('8617628627274@c.us');
    });

    it('builds incoming payload with expected shape', () => {
        const payload = buildPayload({
            from: '+86 176 2862 7274',
            to: 'self@c.us',
            body: '心脏搭桥价格多少'
        });

        expect(payload.from).to.equal('8617628627274@c.us');
        expect(payload.to).to.equal('self@c.us');
        expect(payload.body).to.equal('心脏搭桥价格多少');
        expect(payload.type).to.equal('chat');
        expect(payload.fromMe).to.equal(false);
    });

    it('parses boolean flags correctly', () => {
        const args = parseArgs(['--with-reply', '--body', 'x']);
        expect(args.withReply).to.equal(true);
        expect(args.body).to.equal('x');
    });
});
