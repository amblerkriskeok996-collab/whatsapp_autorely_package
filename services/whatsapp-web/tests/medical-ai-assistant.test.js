const { expect } = require('chai');
const {
    extractJsonObject,
    normalizeTriageResult,
    buildRagContextText
} = require('../src/medicalAiAssistant');

describe('medical-ai-assistant', () => {
    it('extracts json object from markdown code fence', () => {
        const raw = [
            '```json',
            '{"is_disease_consultation":true,"need_rag":true,"keywords":["心脏搭桥"],"reason":"用户问手术费用"}',
            '```'
        ].join('\n');

        const parsed = extractJsonObject(raw);
        expect(parsed.is_disease_consultation).to.equal(true);
        expect(parsed.need_rag).to.equal(true);
        expect(parsed.keywords).to.deep.equal(['心脏搭桥']);
    });

    it('normalizes triage output to safe defaults', () => {
        const normalized = normalizeTriageResult({
            is_disease_consultation: 'yes',
            need_rag: 1,
            keywords: [' 心脏搭桥 ', '', '心外科'],
            reason: ''
        });

        expect(normalized.isDiseaseConsultation).to.equal(true);
        expect(normalized.needRag).to.equal(true);
        expect(normalized.keywords).to.deep.equal(['心脏搭桥', '心外科']);
        expect(normalized.reason).to.be.a('string');
    });

    it('formats rag records into readable context text', () => {
        const text = buildRagContextText([
            {
                keyword: '心脏搭桥',
                items: [
                    {
                        rank: 1,
                        drg_name: '冠状动脉旁路移植术',
                        start_cost_cny: 120000,
                        cap_cost_cny: 350000,
                        score: 8.2
                    }
                ]
            }
        ]);

        expect(text).to.include('关键词: 心脏搭桥');
        expect(text).to.include('冠状动脉旁路移植术');
        expect(text).to.include('120000');
        expect(text).to.include('350000');
    });
});
