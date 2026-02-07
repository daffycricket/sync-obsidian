/**
 * @jest-environment jsdom
 */
import { Setting } from 'obsidian';
import { SyncObsidianSettingTab } from '../settings';
import { DEFAULT_SETTINGS } from '../types';

jest.mock('../main');

describe('SyncObsidianSettingTab', () => {
    let tab: SyncObsidianSettingTab;
    let mockPlugin: any;
    let mockApp: any;

    beforeEach(() => {
        (Setting as any).instances = [];

        mockApp = {
            vault: {
                getMarkdownFiles: jest.fn().mockReturnValue([]),
            },
        };

        mockPlugin = {
            settings: { ...DEFAULT_SETTINGS, password: 'testpass' },
            saveSettings: jest.fn().mockResolvedValue(undefined),
            setupAutoSync: jest.fn(),
            updateStatusBar: jest.fn(),
            syncService: {
                sync: jest.fn().mockResolvedValue(undefined),
                updateSettings: jest.fn(),
            },
        };

        tab = new SyncObsidianSettingTab(mockApp as any, mockPlugin as any);
    });

    function getPasswordSetting(): any {
        return (Setting as any).instances.find(
            (s: any) => s._name === 'Mot de passe'
        );
    }

    describe('Toggle visibilité mot de passe', () => {
        it('devrait masquer le mot de passe par défaut', () => {
            tab.display();

            const passwordSetting = getPasswordSetting();
            expect(passwordSetting).toBeDefined();

            const inputEl = passwordSetting._textComponents[0].inputEl;
            expect(inputEl.type).toBe('password');

            const eyeButton = passwordSetting._extraButtonComponents[0];
            expect(eyeButton).toBeDefined();
            expect(eyeButton._icon).toBe('eye');
            expect(eyeButton._tooltip).toBe('Afficher le mot de passe');
        });

        it('devrait afficher le mot de passe au clic sur eye', () => {
            tab.display();

            const passwordSetting = getPasswordSetting();
            const inputEl = passwordSetting._textComponents[0].inputEl;
            const eyeButton = passwordSetting._extraButtonComponents[0];

            eyeButton._clickHandler();

            expect(inputEl.type).toBe('text');
            expect(eyeButton._icon).toBe('eye-off');
            expect(eyeButton._tooltip).toBe('Masquer le mot de passe');
        });

        it('devrait remasquer le mot de passe au second clic', () => {
            tab.display();

            const passwordSetting = getPasswordSetting();
            const inputEl = passwordSetting._textComponents[0].inputEl;
            const eyeButton = passwordSetting._extraButtonComponents[0];

            eyeButton._clickHandler(); // afficher
            eyeButton._clickHandler(); // masquer

            expect(inputEl.type).toBe('password');
            expect(eyeButton._icon).toBe('eye');
            expect(eyeButton._tooltip).toBe('Afficher le mot de passe');
        });
    });
});
