const { expect } = require('chai');
const {
    createPortalState,
    transitionPortalState,
    isPortalReady,
    buildLoginAction
} = require('../src/accountPortalState');

describe('account-portal-state', () => {
    it('starts in initializing state', () => {
        const state = createPortalState(1000);

        expect(state.status).to.equal('initializing');
        expect(state.updatedAt).to.equal(1000);
        expect(isPortalReady(state)).to.equal(false);
    });

    it('allows opening home only after ready state', () => {
        const state = transitionPortalState(createPortalState(), 'ready');

        expect(isPortalReady(state)).to.equal(true);
        expect(buildLoginAction(state)).to.deep.equal({
            allowed: true,
            message: 'Account is ready'
        });
    });

    it('requests re-login after qr, auth failure and disconnect states', () => {
        const qrState = transitionPortalState(createPortalState(), 'qr');
        const authFailState = transitionPortalState(createPortalState(), 'auth_failure', 'session invalid');
        const disconnectedState = transitionPortalState(createPortalState(), 'disconnected', 'LOGOUT');

        expect(buildLoginAction(qrState)).to.deep.equal({
            allowed: false,
            message: 'Account expired, please login again'
        });
        expect(buildLoginAction(authFailState)).to.deep.equal({
            allowed: false,
            message: 'Account expired, please login again'
        });
        expect(buildLoginAction(disconnectedState)).to.deep.equal({
            allowed: false,
            message: 'Account expired, please login again'
        });
    });

    it('blocks login while switching account', () => {
        const state = transitionPortalState(createPortalState(), 'switching_account');

        expect(buildLoginAction(state)).to.deep.equal({
            allowed: false,
            message: 'Switching account, please wait'
        });
    });
});
