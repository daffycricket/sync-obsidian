/**
 * Tests pour report-formatter.ts
 */

import { SyncReportEntry } from '../types';
import {
    getStatusIcon,
    getStatusLabel,
    getErrorTypeLabel,
    formatSize,
    formatDuration,
    formatReportEntry,
    generateReportContent
} from '../report-formatter';

describe('Report Formatter - Status Helpers', () => {
    describe('getStatusIcon', () => {
        it('should return ✅ for success', () => {
            expect(getStatusIcon('success')).toBe('✅');
        });

        it('should return ⚠️ for warning', () => {
            expect(getStatusIcon('warning')).toBe('⚠️');
        });

        it('should return ❌ for error', () => {
            expect(getStatusIcon('error')).toBe('❌');
        });
    });

    describe('getStatusLabel', () => {
        it('should return OK for success', () => {
            expect(getStatusLabel('success')).toBe('OK');
        });

        it('should return WARNING for warning', () => {
            expect(getStatusLabel('warning')).toBe('WARNING');
        });

        it('should return ERREUR for error', () => {
            expect(getStatusLabel('error')).toBe('ERREUR');
        });
    });

    describe('getErrorTypeLabel', () => {
        it('should return serveur for server', () => {
            expect(getErrorTypeLabel('server')).toBe('serveur');
        });

        it('should return locale for local', () => {
            expect(getErrorTypeLabel('local')).toBe('locale');
        });

        it('should return réseau for network', () => {
            expect(getErrorTypeLabel('network')).toBe('réseau');
        });

        it('should return authentification for auth', () => {
            expect(getErrorTypeLabel('auth')).toBe('authentification');
        });
    });
});

describe('Report Formatter - formatSize', () => {
    it('should return "0 o" for zero bytes', () => {
        expect(formatSize(0)).toBe('0 o');
    });

    it('should format bytes with + sign', () => {
        expect(formatSize(100)).toBe('+100 o');
        expect(formatSize(500)).toBe('+500 o');
    });

    it('should format negative bytes with - sign', () => {
        expect(formatSize(-100)).toBe('-100 o');
    });

    it('should format kilobytes', () => {
        expect(formatSize(1024)).toBe('+1.0 Ko');
        expect(formatSize(2048)).toBe('+2.0 Ko');
        expect(formatSize(1536)).toBe('+1.5 Ko');
    });

    it('should format megabytes', () => {
        expect(formatSize(1024 * 1024)).toBe('+1.0 Mo');
        expect(formatSize(2.5 * 1024 * 1024)).toBe('+2.5 Mo');
    });

    it('should handle negative kilobytes and megabytes', () => {
        expect(formatSize(-1024)).toBe('-1.0 Ko');
        expect(formatSize(-1024 * 1024)).toBe('-1.0 Mo');
    });
});

describe('Report Formatter - formatDuration', () => {
    it('should format milliseconds under 1 second', () => {
        expect(formatDuration(100)).toBe('100ms');
        expect(formatDuration(500)).toBe('500ms');
        expect(formatDuration(999)).toBe('999ms');
    });

    it('should format seconds for 1000ms and above', () => {
        expect(formatDuration(1000)).toBe('1.0s');
        expect(formatDuration(1500)).toBe('1.5s');
        expect(formatDuration(2000)).toBe('2.0s');
    });

    it('should handle large durations', () => {
        expect(formatDuration(60000)).toBe('60.0s');
        expect(formatDuration(90500)).toBe('90.5s');
    });
});

describe('Report Formatter - formatReportEntry', () => {
    const baseEntry: SyncReportEntry = {
        timestamp: '2024-01-15T10:30:00.000Z',
        status: 'success',
        duration_ms: 1500,
        sent: [],
        received: [],
        deleted: [],
        conflicts: [],
        failed: [],
        bytes_up: 0,
        bytes_down: 0
    };

    it('should format success entry with no changes', () => {
        const result = formatReportEntry(baseEntry);

        expect(result).toContain('✅ OK');
        expect(result).toContain('↑ Envoyées (0)');
        expect(result).toContain('↓ Reçues (0)');
        expect(result).toContain('Aucun changement');
    });

    it('should format entry with sent files', () => {
        const entry: SyncReportEntry = {
            ...baseEntry,
            sent: [
                { path: 'note1.md', size_delta: 100 },
                { path: 'note2.md', size_delta: 200 }
            ],
            bytes_up: 300
        };
        const result = formatReportEntry(entry);

        expect(result).toContain('↑ Envoyées (2)');
        expect(result).toContain('• note1.md');
        expect(result).toContain('• note2.md');
    });

    it('should format entry with received files and size delta', () => {
        const entry: SyncReportEntry = {
            ...baseEntry,
            received: [{ path: 'note.md', size_delta: 500 }],
            bytes_down: 500
        };
        const result = formatReportEntry(entry);

        expect(result).toContain('↓ Reçues (1)');
        expect(result).toContain('• note.md (+500 o)');
    });

    it('should format entry with deleted files', () => {
        const entry: SyncReportEntry = {
            ...baseEntry,
            deleted: ['old.md', 'deleted.md']
        };
        const result = formatReportEntry(entry);

        expect(result).toContain('🗑 Supprimées (2)');
        expect(result).toContain('• old.md');
        expect(result).toContain('• deleted.md');
    });

    it('should format entry with conflicts', () => {
        const entry: SyncReportEntry = {
            ...baseEntry,
            status: 'warning',
            conflicts: [{
                path: 'conflict.md',
                conflict_file: 'conflict (conflit 2024-01-15).md'
            }]
        };
        const result = formatReportEntry(entry);

        expect(result).toContain('⚠️ WARNING');
        expect(result).toContain('⚠️ Conflits (1)');
        expect(result).toContain('• conflict.md');
        expect(result).toContain('→ Fichier créé : conflict (conflit 2024-01-15).md');
    });

    it('should format entry with failed files', () => {
        const entry: SyncReportEntry = {
            ...baseEntry,
            status: 'warning',
            sent: [{ path: 'good.md' }],
            failed: [{
                path: 'bad:file.md',
                error: 'Invalid characters',
                details: 'Caractères problématiques : :'
            }]
        };
        const result = formatReportEntry(entry);

        expect(result).toContain('Sync partielle : 1/2 fichiers synchronisés');
        expect(result).toContain('❌ Échecs (1)');
        expect(result).toContain('• bad:file.md');
        expect(result).toContain('Erreur : Invalid characters');
        expect(result).toContain('Caractères problématiques : :');
    });

    it('should format error entry', () => {
        const entry: SyncReportEntry = {
            ...baseEntry,
            status: 'error',
            error_type: 'network',
            error_message: 'Connection refused',
            error_details: 'Server unreachable'
        };
        const result = formatReportEntry(entry);

        expect(result).toContain('❌ ERREUR');
        expect(result).toContain('Type : Erreur réseau');
        expect(result).toContain('Message : Connection refused');
        expect(result).toContain('Détails : Server unreachable');
    });

    it('should include stack trace when showStackTrace is true', () => {
        const entry: SyncReportEntry = {
            ...baseEntry,
            status: 'error',
            error_type: 'server',
            error_message: 'Internal error',
            stack_trace: 'Error: Internal error\n    at someFunction()'
        };

        const withStack = formatReportEntry(entry, true);
        const withoutStack = formatReportEntry(entry, false);

        expect(withStack).toContain('Stack trace :');
        expect(withStack).toContain('at someFunction()');
        expect(withoutStack).not.toContain('Stack trace :');
    });

    it('should show duration and transfer stats', () => {
        const entry: SyncReportEntry = {
            ...baseEntry,
            sent: [{ path: 'note.md' }],
            bytes_up: 1024,
            bytes_down: 2048
        };
        const result = formatReportEntry(entry);

        expect(result).toContain('⏱️ Durée : 1.5s');
        expect(result).toContain('📦 ↑+1.0 Ko ↓+2.0 Ko');
    });
});

describe('Report Formatter - generateReportContent', () => {
    const baseEntry: SyncReportEntry = {
        timestamp: '2024-01-15T10:30:00.000Z',
        status: 'success',
        duration_ms: 1500,
        sent: [],
        received: [],
        deleted: [],
        conflicts: [],
        failed: [],
        bytes_up: 0,
        bytes_down: 0
    };

    it('should return message for empty history', () => {
        expect(generateReportContent([])).toBe('Aucune synchronisation enregistrée.');
        expect(generateReportContent(null as any)).toBe('Aucune synchronisation enregistrée.');
    });

    it('should format single entry', () => {
        const result = generateReportContent([baseEntry]);

        expect(result).toContain('✅ OK');
        expect(result).toContain('Aucun changement');
    });

    it('should format multiple entries', () => {
        const entries: SyncReportEntry[] = [
            { ...baseEntry, timestamp: '2024-01-15T10:00:00.000Z' },
            { ...baseEntry, timestamp: '2024-01-15T11:00:00.000Z' }
        ];
        const result = generateReportContent(entries);

        // Should have two separators (one per entry)
        const separatorCount = (result.match(/───────────────────────────────────────────────────────/g) || []).length;
        expect(separatorCount).toBe(4); // 2 entries × 2 separators each
    });

    it('should pass showStackTrace to formatReportEntry', () => {
        const entry: SyncReportEntry = {
            ...baseEntry,
            status: 'error',
            error_type: 'server',
            stack_trace: 'Error stack here'
        };

        const withStack = generateReportContent([entry], true);
        const withoutStack = generateReportContent([entry], false);

        expect(withStack).toContain('Stack trace :');
        expect(withoutStack).not.toContain('Stack trace :');
    });
});
