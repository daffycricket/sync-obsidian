// Types pour l'API SyncObsidian

// ============================================
// Rapport de synchronisation
// ============================================

export interface SyncFileInfo {
    path: string;
    size_delta?: number;  // en octets
}

export interface SyncConflictInfo {
    path: string;
    conflict_file: string;  // chemin du fichier conflit créé
}

export interface SyncFailedFile {
    path: string;
    error: string;          // message d'erreur court
    details?: string;       // détails (ex: caractères problématiques)
}

export interface SyncReportEntry {
    timestamp: string;           // ISO 8601
    status: "success" | "warning" | "error";
    duration_ms: number;
    
    // Succès / Warning partiel
    sent: SyncFileInfo[];
    received: SyncFileInfo[];
    deleted: string[];
    conflicts: SyncConflictInfo[];
    failed: SyncFailedFile[];     // Fichiers échoués (sync partielle)
    bytes_up: number;
    bytes_down: number;
    
    // Erreur complète
    error_type?: "server" | "local" | "network" | "auth";
    error_message?: string;
    error_file?: string;
    error_details?: string;
    stack_trace?: string;
}

// ============================================
// Settings du plugin
// ============================================

export interface SyncObsidianSettings {
    serverUrl: string;
    username: string;
    password: string;
    accessToken: string | null;
    autoSyncInterval: number; // en minutes, 0 = désactivé
    lastSync: string | null; // ISO timestamp
    showStatusBar: boolean;
    knownFiles: string[]; // Liste des fichiers connus après le dernier sync réussi
    
    // Rapport de synchronisation
    reportMode: "last" | "history";
    reportHistoryHours: number;
    reportShowStackTrace: boolean;
    syncHistory: SyncReportEntry[];
}

export const DEFAULT_SETTINGS: SyncObsidianSettings = {
    serverUrl: "",
    username: "",
    password: "",
    accessToken: null,
    autoSyncInterval: 5,
    lastSync: null,
    showStatusBar: true,
    knownFiles: [],
    
    // Rapport de synchronisation - défauts
    reportMode: "history",
    reportHistoryHours: 24,
    reportShowStackTrace: true,
    syncHistory: [],
};

// API Response types
export interface Token {
    access_token: string;
    token_type: string;
}

export interface NoteMetadata {
    path: string;
    content_hash: string;
    modified_at: string;
    is_deleted: boolean;
}

export interface NoteContent {
    path: string;
    content: string;
    content_hash: string;
    modified_at: string;
    is_deleted: boolean;
}

export interface SyncRequest {
    last_sync: string | null;
    notes: NoteMetadata[];
    attachments: any[];
}

export interface SyncResponse {
    server_time: string;
    notes_to_pull: NoteMetadata[];
    notes_to_push: string[];
    conflicts: NoteMetadata[];
    attachments_to_pull: any[];
    attachments_to_push: string[];
}

export interface PushNotesRequest {
    notes: NoteContent[];
}

export interface PushNotesResponse {
    success: string[];
    failed: string[];
}

export interface PullNotesRequest {
    paths: string[];
}

export interface PullNotesResponse {
    notes: NoteContent[];
}

export type SyncStatus = "idle" | "syncing" | "success" | "error";
