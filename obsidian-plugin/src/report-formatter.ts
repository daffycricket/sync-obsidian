/**
 * Fonctions de formatage pour le rapport de synchronisation.
 * Extraites de settings.ts pour une meilleure séparation des responsabilités.
 */

import { SyncReportEntry } from './types';

/**
 * Retourne l'icône correspondant au statut
 */
export function getStatusIcon(status: "success" | "warning" | "error"): string {
    switch (status) {
        case "success": return "✅";
        case "warning": return "⚠️";
        case "error": return "❌";
    }
}

/**
 * Retourne le libellé correspondant au statut
 */
export function getStatusLabel(status: "success" | "warning" | "error"): string {
    switch (status) {
        case "success": return "OK";
        case "warning": return "WARNING";
        case "error": return "ERREUR";
    }
}

/**
 * Retourne le libellé français du type d'erreur
 */
export function getErrorTypeLabel(type: "server" | "local" | "network" | "auth"): string {
    switch (type) {
        case "server": return "serveur";
        case "local": return "locale";
        case "network": return "réseau";
        case "auth": return "authentification";
    }
}

/**
 * Formate une taille en octets de manière lisible
 */
export function formatSize(bytes: number): string {
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

/**
 * Formate une durée en millisecondes de manière lisible
 */
export function formatDuration(ms: number): string {
    if (ms < 1000) {
        return `${ms}ms`;
    } else {
        return `${(ms / 1000).toFixed(1)}s`;
    }
}

/**
 * Formate une entrée de rapport de synchronisation
 */
export function formatReportEntry(entry: SyncReportEntry, showStackTrace: boolean = false): string {
    const lines: string[] = [];

    // En-tête avec date et statut
    const date = new Date(entry.timestamp);
    const dateStr = date.toLocaleDateString("fr-FR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
    });
    const timeStr = date.toLocaleTimeString("fr-FR", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
    });

    const statusIcon = getStatusIcon(entry.status);
    const statusLabel = getStatusLabel(entry.status);

    lines.push("───────────────────────────────────────────────────────");
    lines.push(`📅 ${dateStr} ${timeStr}                     ${statusIcon} ${statusLabel}`);
    lines.push("───────────────────────────────────────────────────────");
    lines.push("");

    // En cas d'erreur complète
    if (entry.status === "error" && entry.error_type) {
        lines.push(`Type : Erreur ${getErrorTypeLabel(entry.error_type)}`);
        lines.push("");
        if (entry.error_message) {
            lines.push(`Message : ${entry.error_message}`);
            lines.push("");
        }
        if (entry.error_file) {
            lines.push(`Fichier concerné : ${entry.error_file}`);
            lines.push("");
        }
        if (entry.error_details) {
            lines.push(`Détails : ${entry.error_details}`);
            lines.push("");
        }
        if (showStackTrace && entry.stack_trace) {
            lines.push("Stack trace :");
            lines.push(entry.stack_trace);
            lines.push("");
        }
    } else {
        // Sync partielle ?
        if (entry.failed.length > 0) {
            const total = entry.sent.length + entry.received.length + entry.failed.length;
            const success = entry.sent.length + entry.received.length;
            lines.push(`Sync partielle : ${success}/${total} fichiers synchronisés`);
            lines.push("");
        }

        // Fichiers envoyés
        lines.push(`↑ Envoyées (${entry.sent.length}) :`);
        if (entry.sent.length === 0) {
            lines.push("  (aucune)");
        } else {
            for (const file of entry.sent) {
                lines.push(`  • ${file.path}`);
            }
        }
        lines.push("");

        // Fichiers reçus
        lines.push(`↓ Reçues (${entry.received.length}) :`);
        if (entry.received.length === 0) {
            lines.push("  (aucune)");
        } else {
            for (const file of entry.received) {
                const sizeInfo = file.size_delta !== undefined
                    ? ` (${formatSize(file.size_delta)})`
                    : "";
                lines.push(`  • ${file.path}${sizeInfo}`);
            }
        }
        lines.push("");

        // Fichiers supprimés
        lines.push(`🗑 Supprimées (${entry.deleted.length})`);
        if (entry.deleted.length > 0) {
            for (const path of entry.deleted) {
                lines.push(`  • ${path}`);
            }
        }
        lines.push("");

        // Conflits
        lines.push(`⚠️ Conflits (${entry.conflicts.length})`);
        if (entry.conflicts.length > 0) {
            for (const conflict of entry.conflicts) {
                lines.push(`  • ${conflict.path}`);
                lines.push(`    → Fichier créé : ${conflict.conflict_file}`);
            }
        }
        lines.push("");

        // Échecs
        if (entry.failed.length > 0) {
            lines.push(`❌ Échecs (${entry.failed.length}) :`);
            for (const fail of entry.failed) {
                lines.push(`  • ${fail.path}`);
                lines.push(`    Erreur : ${fail.error}`);
                if (fail.details) {
                    lines.push(`    ${fail.details}`);
                }
            }
            lines.push("");
        }

        // Résumé
        if (entry.sent.length === 0 && entry.received.length === 0 &&
            entry.deleted.length === 0 && entry.conflicts.length === 0) {
            lines.push(`⏱️ Durée : ${formatDuration(entry.duration_ms)} | Aucun changement`);
        } else {
            lines.push(
                `⏱️ Durée : ${formatDuration(entry.duration_ms)} | ` +
                `📦 ↑${formatSize(entry.bytes_up)} ↓${formatSize(entry.bytes_down)}`
            );
        }
    }

    return lines.join("\n");
}

/**
 * Génère le contenu complet du rapport à partir de l'historique
 */
export function generateReportContent(history: SyncReportEntry[], showStackTrace: boolean = false): string {
    if (!history || history.length === 0) {
        return "Aucune synchronisation enregistrée.";
    }

    const lines: string[] = [];

    for (const entry of history) {
        lines.push(formatReportEntry(entry, showStackTrace));
        lines.push(""); // Ligne vide entre les entrées
    }

    return lines.join("\n");
}
