// Types pour l'API SyncObsidian

export interface SyncObsidianSettings {
    serverUrl: string;
    username: string;
    password: string;
    accessToken: string | null;
    autoSyncInterval: number; // en minutes, 0 = désactivé
    lastSync: string | null; // ISO timestamp
    showStatusBar: boolean;
}

export const DEFAULT_SETTINGS: SyncObsidianSettings = {
    serverUrl: "",
    username: "",
    password: "",
    accessToken: null,
    autoSyncInterval: 5,
    lastSync: null,
    showStatusBar: true,
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
