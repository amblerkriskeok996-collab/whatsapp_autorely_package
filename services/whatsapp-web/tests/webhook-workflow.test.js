const { expect } = require('chai');
const { handleIncomingWebhookMessage } = require('../src/webhookWorkflow');

describe('webhook-workflow', () => {
    it('skips auto-reply for outbound self messages', async () => {
        const result = await handleIncomingWebhookMessage({
            incomingPayload: {
                from: '8617628627274@c.us',
                to: '8613000000000@c.us',
                body: 'ping',
                fromMe: true
            },
            aiConfig: {},
            ragConfig: {}
        });

        expect(result.decision.shouldReply).to.equal(false);
        expect(result.decision.reason).to.equal('from_me');
        expect(result.reply.text).to.equal('');
        expect(result.ai.used).to.equal(false);
    });

    it('runs ai and rag pipeline when reply is needed', async () => {
        const stubGenerateReply = async ({ messageText }) => ({
            triage: {
                isDiseaseConsultation: true,
                needRag: true,
                keywords: ['bypass surgery'],
                reason: 'cost question'
            },
            triageRaw: '{"need_rag":true}',
            ragResults: [{ keyword: 'bypass surgery', items: [{ rank: 1 }] }],
            ragContextText: 'RAG HIT',
            replyText: `AI reply for: ${messageText}`
        });

        const result = await handleIncomingWebhookMessage({
            incomingPayload: {
                from: '8617628627274@c.us',
                to: '8613000000000@c.us',
                body: 'How much does bypass surgery cost?',
                fromMe: false,
                isGroup: false
            },
            aiConfig: {
                baseUrl: 'https://example.ai',
                apiKey: 'sk-test',
                model: 'demo-model'
            },
            ragConfig: { baseUrl: 'http://localhost:18080', topK: 5 },
            generateReply: stubGenerateReply
        });

        expect(result.decision.shouldReply).to.equal(true);
        expect(result.ai.used).to.equal(true);
        expect(result.ai.triage.needRag).to.equal(true);
        expect(result.ai.rag.resultsCount).to.equal(1);
        expect(result.reply.to).to.equal('8617628627274@c.us');
        expect(result.reply.text).to.equal('AI reply for: How much does bypass surgery cost?');
    });

    it('returns fallback reply when ai pipeline fails', async () => {
        const result = await handleIncomingWebhookMessage({
            incomingPayload: {
                from: '8617628627274@c.us',
                to: '8613000000000@c.us',
                body: 'I need treatment advice',
                fromMe: false,
                isGroup: false
            },
            aiConfig: {
                baseUrl: 'https://example.ai',
                apiKey: 'sk-test',
                model: 'demo-model'
            },
            ragConfig: {},
            generateReply: async () => {
                throw new Error('upstream timeout');
            }
        });

        expect(result.decision.shouldReply).to.equal(true);
        expect(result.ai.used).to.equal(true);
        expect(result.ai.error).to.include('upstream timeout');
        expect(result.reply.text).to.be.a('string');
        expect(result.reply.text.length).to.be.greaterThan(0);
    });
});
