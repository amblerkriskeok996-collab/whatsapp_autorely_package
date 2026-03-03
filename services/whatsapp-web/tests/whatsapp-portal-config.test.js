const { expect } = require('chai');
const path = require('path');
const {
    getSessionCleanupTargets,
    buildPortalPuppeteerOptions,
    shouldDisableLibraryUserAgent
} = require('../src/whatsappPortalConfig');

describe('whatsapp-portal-config', () => {
    it('returns auth and cache cleanup targets under project root', () => {
        const projectRoot = path.resolve('D:/code/programs/Whatsapp/whatsapp-web');
        const targets = getSessionCleanupTargets(projectRoot);

        expect(targets).to.deep.equal([
            path.resolve(projectRoot, '.wwebjs_auth'),
            path.resolve(projectRoot, '.wwebjs_cache')
        ]);
    });

    it('uses system chrome channel by default for qr login compatibility', () => {
        const options = buildPortalPuppeteerOptions({});
        expect(options.headless).to.equal(false);
        expect(options.channel).to.equal('chrome');
    });

    it('allows disabling system chrome channel by env flag', () => {
        const options = buildPortalPuppeteerOptions({ WA_USE_SYSTEM_CHROME: 'false' });
        expect(options.headless).to.equal(false);
        expect(options).to.not.have.property('channel');
    });

    it('disables library default userAgent unless explicitly enabled', () => {
        expect(shouldDisableLibraryUserAgent({})).to.equal(true);
        expect(shouldDisableLibraryUserAgent({ WA_USE_LIBRARY_DEFAULT_UA: 'true' })).to.equal(false);
    });
});
