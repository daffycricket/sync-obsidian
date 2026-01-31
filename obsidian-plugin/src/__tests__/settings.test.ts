/**
 * Tests pour les fonctions utilitaires de settings.ts
 *
 * Note: La classe SyncObsidianSettingTab a des dépendances fortes sur le plugin Obsidian.
 * Ces tests se concentrent sur les fonctions de formatage en les testant via des helpers extraits.
 */

import { SyncReportEntry } from '../types';

// Helpers de formatage extraits pour les tests
// Ces fonctions répliquent la logique de settings.ts pour les tests unitaires

function getStatusIcon(status: "success" | "warning" | "error"): string {
    switch (status) {
        case "success": return "✅";
        case "warning": return "⚠️";
        case "error": return "❌";
    }
}

function getStatusLabel(status: "success" | "warning" | "error"): string {
    switch (status) {
        case "success": return "OK";
        case "warning": return "WARNING";
        case "error": return "ERREUR";
    }
}

function getErrorTypeLabel(type: "server" | "local" | "network" | "auth"): string {
    switch (type) {
        case "server": return "serveur";
        case "local": return "locale";
        case "network": return "réseau";
        case "auth": return "authentification";
    }
}

function formatSize(bytes: number): string {
    if (bytes === 0) return "0 o";

    const sign = bytes < 0 ? "-" : "+";
    const absBytes = Math.abs(bytes);

    if (absBytes < 1024) {
        return `${sign}${absBytes} o`;
    } else if (absBytes < 1024 * 1024) {
        return `${sign}${(absBytes / 1024).toFixed(1)} Ko`;
    } else {
        return `${sign}${(absBytes / (1024 * 1024)).toFixed(1)} Mo`;
    }
}

function formatDuration(ms: number): string {
    if (ms < 1000) {
        return `${ms}ms`;
    } else {
        return `${(ms / 1000).toFixed(1)}s`;
    }
}

describe('Settings Formatting Helpers', () => {
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

    describe('formatSize', () => {
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

    describe('formatDuration', () => {
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
});

describe('Report Entry Formatting', () => {
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

    describe('Report status combinations', () => {
        it('should have correct structure for success report', () => {
            const entry: SyncReportEntry = {
                ...baseEntry,
                status: 'success',
                sent: [{ path: 'note1.md', size_delta: 100 }],
                received: [{ path: 'note2.md', size_delta: 200 }],
                bytes_up: 100,
                bytes_down: 200
            };

            expect(entry.status).toBe('success');
            expect(entry.sent).toHaveLength(1);
            expect(entry.received).toHaveLength(1);
            expect(entry.conflicts).toHaveLength(0);
            expect(entry.failed).toHaveLength(0);
        });

        it('should have correct structure for warning report with conflicts', () => {
            const entry: SyncReportEntry = {
                ...baseEntry,
                status: 'warning',
                conflicts: [{ path: 'conflict.md', conflict_file: 'conflict (conflit 2024-01-15).md' }]
            };

            expect(entry.status).toBe('warning');
            expect(entry.conflicts).toHaveLength(1);
            expect(entry.conflicts[0].conflict_file).toContain('conflit');
        });

        it('should have correct structure for warning report with failures', () => {
            const entry: SyncReportEntry = {
                ...baseEntry,
                status: 'warning',
                failed: [{ path: 'bad:file.md', error: 'Invalid characters', details: 'Caractères problématiques : :' }]
            };

            expect(entry.status).toBe('warning');
            expect(entry.failed).toHaveLength(1);
            expect(entry.failed[0].details).toBeDefined();
        });

        it('should have correct structure for error report', () => {
            const entry: SyncReportEntry = {
                ...baseEntry,
                status: 'error',
                error_type: 'network',
                error_message: 'Connection refused',
                stack_trace: 'Error: Connection refused\n    at ...'
            };

            expect(entry.status).toBe('error');
            expect(entry.error_type).toBe('network');
            expect(entry.error_message).toBeDefined();
        });

        it('should handle deleted files', () => {
            const entry: SyncReportEntry = {
                ...baseEntry,
                deleted: ['old-note.md', 'another-deleted.md']
            };

            expect(entry.deleted).toHaveLength(2);
            expect(entry.deleted).toContain('old-note.md');
        });
    });

    describe('Size delta calculations', () => {
        it('should track positive size delta for new content', () => {
            const entry: SyncReportEntry = {
                ...baseEntry,
                received: [{ path: 'note.md', size_delta: 500 }]
            };

            expect(entry.received[0].size_delta).toBe(500);
            expect(formatSize(entry.received[0].size_delta!)).toBe('+500 o');
        });

        it('should track negative size delta for reduced content', () => {
            const entry: SyncReportEntry = {
                ...baseEntry,
                received: [{ path: 'note.md', size_delta: -200 }]
            };

            expect(entry.received[0].size_delta).toBe(-200);
            expect(formatSize(entry.received[0].size_delta!)).toBe('-200 o');
        });
    });
});
