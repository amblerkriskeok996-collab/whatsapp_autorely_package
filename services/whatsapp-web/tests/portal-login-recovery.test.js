const { expect } = require('chai');
const {
    isRecoverablePageError,
    runWithSingleRecovery
} = require('../src/portalLoginRecovery');

describe('portal-login-recovery', () => {
    it('detects recoverable closed-page errors', () => {
        expect(isRecoverablePageError(new Error('Protocol error (Page.bringToFront): Session closed. Most likely the page has been closed.'))).to.equal(true);
        expect(isRecoverablePageError(new Error('Target closed'))).to.equal(true);
        expect(isRecoverablePageError(new Error('Navigation timeout'))).to.equal(false);
    });

    it('retries once for recoverable page errors', async () => {
        let openCalls = 0;
        let recoverCalls = 0;

        const result = await runWithSingleRecovery(
            async () => {
                openCalls++;
                if (openCalls === 1) {
                    throw new Error('Session closed');
                }
                return 'ok';
            },
            async () => {
                recoverCalls++;
            }
        );

        expect(result).to.equal('ok');
        expect(openCalls).to.equal(2);
        expect(recoverCalls).to.equal(1);
    });

    it('does not retry for non recoverable errors', async () => {
        let recoverCalls = 0;

        try {
            await runWithSingleRecovery(
                async () => {
                    throw new Error('something else');
                },
                async () => {
                    recoverCalls++;
                }
            );
            throw new Error('should not reach');
        } catch (error) {
            expect(error.message).to.equal('something else');
            expect(recoverCalls).to.equal(0);
        }
    });
});
