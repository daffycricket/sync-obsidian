import { SyncService } from '../sync-service';
import { App, Vault, TFile, TFolder, requestUrl } from 'obsidian';
import { SyncObsidianSettings, DEFAULT_SETTINGS, SyncReportEntry } from '../types';

// Mock requestUrl pour ApiClient
const mockRequestUrl = requestUrl as jest.MockedFunction<typeof requestUrl>;

// Polyfill crypto pour Node.js
import { webcrypto } from 'crypto';
if (!global.crypto) {
    (global as any).crypto = webcrypto;
}

describe('SyncService', () => {
    let service: SyncService;
    let mockApp: App;
    let mockSettings: SyncObsidianSettings;
    let statusChangeCallback: jest.Mock;

    beforeEach(() => {
        mockApp = new App();
        mockSettings = { ...DEFAULT_SETTINGS, serverUrl: 'https://api.test.com', accessToken: 'test-token' };
        statusChangeCallback = jest.fn();
        service = new SyncService(mockApp, mockSettings, statusChangeCallback);
        mockRequestUrl.mockReset();
    });

    describe('getMimeType (tested via collectLocalAttachments behavior)', () => {
        // Test indirect via la création du service
        // On teste directement via une méthode helper exposée ou via réflexion

        it('should return correct MIME types for common extensions', () => {
            // Accès à la méthode privée via any
            const getMimeType = (service as any).getMimeType.bind(service);

            // Images
            expect(getMimeType('image.png')).toBe('image/png');
            expect(getMimeType('photo.jpg')).toBe('image/jpeg');
            expect(getMimeType('photo.jpeg')).toBe('image/jpeg');
            expect(getMimeType('animation.gif')).toBe('image/gif');
            expect(getMimeType('modern.webp')).toBe('image/webp');
            expect(getMimeType('vector.svg')).toBe('image/svg+xml');
            expect(getMimeType('bitmap.bmp')).toBe('image/bmp');
            expect(getMimeType('favicon.ico')).toBe('image/x-icon');
        });

        it('should return correct MIME types for documents', () => {
            const getMimeType = (service as any).getMimeType.bind(service);

            expect(getMimeType('document.pdf')).toBe('application/pdf');
            expect(getMimeType('document.doc')).toBe('application/msword');
            expect(getMimeType('document.docx')).toBe('application/vnd.openxmlformats-officedocument.wordprocessingml.document');
            expect(getMimeType('spreadsheet.xls')).toBe('application/vnd.ms-excel');
            expect(getMimeType('spreadsheet.xlsx')).toBe('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
            expect(getMimeType('presentation.ppt')).toBe('application/vnd.ms-powerpoint');
            expect(getMimeType('presentation.pptx')).toBe('application/vnd.openxmlformats-officedocument.presentationml.presentation');
        });

        it('should return correct MIME types for audio/video', () => {
            const getMimeType = (service as any).getMimeType.bind(service);

            expect(getMimeType('audio.mp3')).toBe('audio/mpeg');
            expect(getMimeType('audio.wav')).toBe('audio/wav');
            expect(getMimeType('video.mp4')).toBe('video/mp4');
            expect(getMimeType('video.webm')).toBe('video/webm');
        });

        it('should return correct MIME types for archives', () => {
            const getMimeType = (service as any).getMimeType.bind(service);

            expect(getMimeType('archive.zip')).toBe('application/zip');
            expect(getMimeType('archive.rar')).toBe('application/x-rar-compressed');
            expect(getMimeType('archive.7z')).toBe('application/x-7z-compressed');
            expect(getMimeType('archive.tar')).toBe('application/x-tar');
            expect(getMimeType('archive.gz')).toBe('application/gzip');
        });

        it('should return correct MIME types for text files', () => {
            const getMimeType = (service as any).getMimeType.bind(service);

            expect(getMimeType('file.txt')).toBe('text/plain');
            expect(getMimeType('data.json')).toBe('application/json');
            expect(getMimeType('config.xml')).toBe('application/xml');
            expect(getMimeType('data.csv')).toBe('text/csv');
        });

        it('should return application/octet-stream for unknown extensions', () => {
            const getMimeType = (service as any).getMimeType.bind(service);

            expect(getMimeType('file.xyz')).toBe('application/octet-stream');
            expect(getMimeType('file.unknown')).toBe('application/octet-stream');
            expect(getMimeType('file.abc123')).toBe('application/octet-stream');
        });

        it('should return null for empty path', () => {
            const getMimeType = (service as any).getMimeType.bind(service);

            // Fichier sans extension : ext est undefined, donc retourne null
            expect(getMimeType('')).toBeNull();
        });

        it('should handle paths with multiple dots', () => {
            const getMimeType = (service as any).getMimeType.bind(service);

            expect(getMimeType('my.file.name.png')).toBe('image/png');
            expect(getMimeType('archive.tar.gz')).toBe('application/gzip');
        });

        it('should be case insensitive', () => {
            const getMimeType = (service as any).getMimeType.bind(service);

            expect(getMimeType('IMAGE.PNG')).toBe('image/png');
            expect(getMimeType('Photo.JPG')).toBe('image/jpeg');
            expect(getMimeType('Document.PDF')).toBe('application/pdf');
        });
    });

    describe('computeHash', () => {
        it('should compute SHA-256 hash for simple text', async () => {
            const computeHash = (service as any).computeHash.bind(service);

            // Hash connu pour "hello"
            const hash = await computeHash('hello');
            expect(hash).toBe('2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824');
        });

        it('should return same hash for identical content', async () => {
            const computeHash = (service as any).computeHash.bind(service);

            const hash1 = await computeHash('test content');
            const hash2 = await computeHash('test content');
            expect(hash1).toBe(hash2);
        });

        it('should return different hash for different content', async () => {
            const computeHash = (service as any).computeHash.bind(service);

            const hash1 = await computeHash('content A');
            const hash2 = await computeHash('content B');
            expect(hash1).not.toBe(hash2);
        });

        it('should handle empty string', async () => {
            const computeHash = (service as any).computeHash.bind(service);

            // SHA-256 hash of empty string
            const hash = await computeHash('');
            expect(hash).toBe('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855');
        });

        it('should handle unicode characters', async () => {
            const computeHash = (service as any).computeHash.bind(service);

            const hash = await computeHash('héllo wörld 你好');
            expect(hash).toHaveLength(64); // SHA-256 produces 64 hex characters
        });
    });

    describe('computeBinaryHash', () => {
        it('should compute SHA-256 hash for binary content', async () => {
            const computeBinaryHash = (service as any).computeBinaryHash.bind(service);

            const encoder = new TextEncoder();
            const buffer = encoder.encode('hello').buffer;
            const hash = await computeBinaryHash(buffer);

            // Same as text hash for "hello"
            expect(hash).toBe('2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824');
        });

        it('should return same hash for identical binary content', async () => {
            const computeBinaryHash = (service as any).computeBinaryHash.bind(service);

            const encoder = new TextEncoder();
            const buffer1 = encoder.encode('binary data').buffer;
            const buffer2 = encoder.encode('binary data').buffer;

            const hash1 = await computeBinaryHash(buffer1);
            const hash2 = await computeBinaryHash(buffer2);
            expect(hash1).toBe(hash2);
        });

        it('should handle empty ArrayBuffer', async () => {
            const computeBinaryHash = (service as any).computeBinaryHash.bind(service);

            const buffer = new ArrayBuffer(0);
            const hash = await computeBinaryHash(buffer);
            expect(hash).toBe('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855');
        });
    });

    describe('extractErrorDetails', () => {
        it('should detect invalid characters in path', () => {
            const extractErrorDetails = (service as any).extractErrorDetails.bind(service);

            const result = extractErrorDetails(new Error('test'), 'file:name.md');
            expect(result).toContain(':');
        });

        it('should detect multiple invalid characters', () => {
            const extractErrorDetails = (service as any).extractErrorDetails.bind(service);

            const result = extractErrorDetails(new Error('test'), 'file:name?.md');
            expect(result).toContain(':');
            expect(result).toContain('?');
        });

        it('should return undefined for valid paths', () => {
            const extractErrorDetails = (service as any).extractErrorDetails.bind(service);

            const result = extractErrorDetails(new Error('test'), 'folder/valid-file.md');
            expect(result).toBeUndefined();
        });

        it('should detect all problematic characters', () => {
            const extractErrorDetails = (service as any).extractErrorDetails.bind(service);

            // Test each problematic character: \ : * ? " < > |
            expect(extractErrorDetails(new Error(''), 'file:name.md')).toBeDefined();
            expect(extractErrorDetails(new Error(''), 'file*name.md')).toBeDefined();
            expect(extractErrorDetails(new Error(''), 'file?name.md')).toBeDefined();
            expect(extractErrorDetails(new Error(''), 'file"name.md')).toBeDefined();
            expect(extractErrorDetails(new Error(''), 'file<name.md')).toBeDefined();
            expect(extractErrorDetails(new Error(''), 'file>name.md')).toBeDefined();
            expect(extractErrorDetails(new Error(''), 'file|name.md')).toBeDefined();
        });
    });

    describe('detectDeletedFiles', () => {
        it('should return empty array when knownPaths is empty', () => {
            const detectDeletedFiles = (service as any).detectDeletedFiles.bind(service);
            const currentPaths = new Set(['file1.md', 'file2.md']);

            expect(detectDeletedFiles(currentPaths, [])).toEqual([]);
            expect(detectDeletedFiles(currentPaths, null)).toEqual([]);
            expect(detectDeletedFiles(currentPaths, undefined)).toEqual([]);
        });

        it('should return empty array when no files were deleted', () => {
            const detectDeletedFiles = (service as any).detectDeletedFiles.bind(service);
            const currentPaths = new Set(['file1.md', 'file2.md']);
            const knownPaths = ['file1.md', 'file2.md'];

            expect(detectDeletedFiles(currentPaths, knownPaths)).toEqual([]);
        });

        it('should return deleted files', () => {
            const detectDeletedFiles = (service as any).detectDeletedFiles.bind(service);
            const currentPaths = new Set(['file1.md']);
            const knownPaths = ['file1.md', 'file2.md', 'file3.md'];

            const result = detectDeletedFiles(currentPaths, knownPaths);
            expect(result).toEqual(['file2.md', 'file3.md']);
        });

        it('should return all known files when all are deleted', () => {
            const detectDeletedFiles = (service as any).detectDeletedFiles.bind(service);
            const currentPaths = new Set<string>();
            const knownPaths = ['file1.md', 'file2.md'];

            const result = detectDeletedFiles(currentPaths, knownPaths);
            expect(result).toEqual(['file1.md', 'file2.md']);
        });
    });

    describe('determineStatus', () => {
        it('should return "error" when errorType is provided', () => {
            const determineStatus = (service as any).determineStatus.bind(service);

            expect(determineStatus([], [], 'server')).toBe('error');
            expect(determineStatus([], [], 'network')).toBe('error');
            expect(determineStatus([], [], 'auth')).toBe('error');
            expect(determineStatus([], [], 'local')).toBe('error');
        });

        it('should return "warning" when there are conflicts', () => {
            const determineStatus = (service as any).determineStatus.bind(service);

            const conflicts = [{ path: 'test.md', conflict_file: 'test (conflit).md' }];
            expect(determineStatus(conflicts, [])).toBe('warning');
        });

        it('should return "warning" when there are failed files', () => {
            const determineStatus = (service as any).determineStatus.bind(service);

            const failed = [{ path: 'test.md', error: 'Error' }];
            expect(determineStatus([], failed)).toBe('warning');
        });

        it('should return "warning" when there are both conflicts and failed', () => {
            const determineStatus = (service as any).determineStatus.bind(service);

            const conflicts = [{ path: 'a.md', conflict_file: 'a (conflit).md' }];
            const failed = [{ path: 'b.md', error: 'Error' }];
            expect(determineStatus(conflicts, failed)).toBe('warning');
        });

        it('should return "success" when no errors, conflicts, or failures', () => {
            const determineStatus = (service as any).determineStatus.bind(service);

            expect(determineStatus([], [])).toBe('success');
        });
    });

    describe('cleanupHistory', () => {
        it('should remove entries older than reportHistoryHours', () => {
            // Setup settings with history
            const now = new Date();
            const oldEntry: SyncReportEntry = {
                timestamp: new Date(now.getTime() - 25 * 60 * 60 * 1000).toISOString(), // 25 hours ago
                status: 'success',
                duration_ms: 100,
                sent: [],
                received: [],
                deleted: [],
                conflicts: [],
                failed: [],
                bytes_up: 0,
                bytes_down: 0
            };
            const recentEntry: SyncReportEntry = {
                timestamp: new Date(now.getTime() - 1 * 60 * 60 * 1000).toISOString(), // 1 hour ago
                status: 'success',
                duration_ms: 100,
                sent: [],
                received: [],
                deleted: [],
                conflicts: [],
                failed: [],
                bytes_up: 0,
                bytes_down: 0
            };

            mockSettings.syncHistory = [recentEntry, oldEntry];
            mockSettings.reportHistoryHours = 24;

            const cleanupHistory = (service as any).cleanupHistory.bind(service);
            cleanupHistory();

            expect(mockSettings.syncHistory).toHaveLength(1);
            expect(mockSettings.syncHistory[0]).toBe(recentEntry);
        });

        it('should keep all entries within reportHistoryHours', () => {
            const now = new Date();
            const entries: SyncReportEntry[] = [
                {
                    timestamp: new Date(now.getTime() - 1 * 60 * 60 * 1000).toISOString(),
                    status: 'success',
                    duration_ms: 100,
                    sent: [],
                    received: [],
                    deleted: [],
                    conflicts: [],
                    failed: [],
                    bytes_up: 0,
                    bytes_down: 0
                },
                {
                    timestamp: new Date(now.getTime() - 12 * 60 * 60 * 1000).toISOString(),
                    status: 'success',
                    duration_ms: 100,
                    sent: [],
                    received: [],
                    deleted: [],
                    conflicts: [],
                    failed: [],
                    bytes_up: 0,
                    bytes_down: 0
                }
            ];

            mockSettings.syncHistory = entries;
            mockSettings.reportHistoryHours = 24;

            const cleanupHistory = (service as any).cleanupHistory.bind(service);
            cleanupHistory();

            expect(mockSettings.syncHistory).toHaveLength(2);
        });
    });

    describe('addReportToHistory', () => {
        it('should replace all history in "last" mode', () => {
            mockSettings.reportMode = 'last';
            mockSettings.syncHistory = [
                {
                    timestamp: new Date().toISOString(),
                    status: 'success',
                    duration_ms: 100,
                    sent: [],
                    received: [],
                    deleted: [],
                    conflicts: [],
                    failed: [],
                    bytes_up: 0,
                    bytes_down: 0
                }
            ];

            const newReport: SyncReportEntry = {
                timestamp: new Date().toISOString(),
                status: 'warning',
                duration_ms: 200,
                sent: [{ path: 'test.md' }],
                received: [],
                deleted: [],
                conflicts: [],
                failed: [],
                bytes_up: 100,
                bytes_down: 0
            };

            const addReportToHistory = (service as any).addReportToHistory.bind(service);
            addReportToHistory(newReport);

            expect(mockSettings.syncHistory).toHaveLength(1);
            expect(mockSettings.syncHistory[0].status).toBe('warning');
        });

        it('should prepend to history in "history" mode', () => {
            mockSettings.reportMode = 'history';
            mockSettings.reportHistoryHours = 24;
            const existingReport: SyncReportEntry = {
                timestamp: new Date().toISOString(),
                status: 'success',
                duration_ms: 100,
                sent: [],
                received: [],
                deleted: [],
                conflicts: [],
                failed: [],
                bytes_up: 0,
                bytes_down: 0
            };
            mockSettings.syncHistory = [existingReport];

            const newReport: SyncReportEntry = {
                timestamp: new Date().toISOString(),
                status: 'warning',
                duration_ms: 200,
                sent: [],
                received: [],
                deleted: [],
                conflicts: [],
                failed: [],
                bytes_up: 0,
                bytes_down: 0
            };

            const addReportToHistory = (service as any).addReportToHistory.bind(service);
            addReportToHistory(newReport);

            expect(mockSettings.syncHistory).toHaveLength(2);
            expect(mockSettings.syncHistory[0].status).toBe('warning'); // New one first
            expect(mockSettings.syncHistory[1].status).toBe('success'); // Old one second
        });
    });

    describe('updateSettings', () => {
        it('should update internal settings and API client', () => {
            const newSettings: SyncObsidianSettings = {
                ...DEFAULT_SETTINGS,
                serverUrl: 'https://new-server.com',
                accessToken: 'new-token'
            };

            service.updateSettings(newSettings);

            // Verify by making a request that would use the new URL
            mockRequestUrl.mockResolvedValueOnce({
                status: 200,
                text: '{}',
                json: {}
            });

            // Use the API client indirectly
            (service as any).apiClient.checkHealth();

            expect(mockRequestUrl).toHaveBeenCalledWith(
                expect.objectContaining({
                    url: 'https://new-server.com/health'
                })
            );
        });
    });

    describe('getStatus', () => {
        it('should return initial status as idle', () => {
            expect(service.getStatus()).toBe('idle');
        });
    });

    describe('login', () => {
        it('should return true and set token on successful login', async () => {
            mockRequestUrl.mockResolvedValueOnce({
                status: 200,
                text: '{}',
                json: { access_token: 'new-token', token_type: 'bearer' }
            });

            const result = await service.login('user', 'pass');

            expect(result).toBe(true);
            expect(mockSettings.accessToken).toBe('new-token');
        });

        it('should return false on failed login', async () => {
            mockRequestUrl.mockRejectedValueOnce(new Error('Invalid credentials'));

            const result = await service.login('user', 'wrong');

            expect(result).toBe(false);
        });
    });
});
