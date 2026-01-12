import { App, TFile, Notice } from "obsidian";
import { ApiClient } from "./api-client";
import {
    SyncObsidianSettings,
    NoteMetadata,
    NoteContent,
    SyncStatus,
} from "./types";

export class SyncService {
    private app: App;
    private apiClient: ApiClient;
    private settings: SyncObsidianSettings;
    private status: SyncStatus = "idle";
    private onStatusChange: (status: SyncStatus) => void;

    constructor(
        app: App,
        settings: SyncObsidianSettings,
        onStatusChange: (status: SyncStatus) => void
    ) {
        this.app = app;
        this.settings = settings;
        this.apiClient = new ApiClient(
            settings.serverUrl,
            settings.accessToken
        );
        this.onStatusChange = onStatusChange;
    }

    updateSettings(settings: SyncObsidianSettings) {
        this.settings = settings;
        this.apiClient.setServerUrl(settings.serverUrl);
        this.apiClient.setAccessToken(settings.accessToken);
    }

    getStatus(): SyncStatus {
        return this.status;
    }

    private setStatus(status: SyncStatus) {
        this.status = status;
        this.onStatusChange(status);
    }

    private async computeHash(content: string): Promise<string> {
        // Utiliser SHA256 via Web Crypto API (compatible avec le serveur Python)
        const encoder = new TextEncoder();
        const data = encoder.encode(content);
        const hashBuffer = await crypto.subtle.digest("SHA-256", data);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
    }

    async login(username: string, password: string): Promise<boolean> {
        try {
            const token = await this.apiClient.login(username, password);
            this.settings.accessToken = token.access_token;
            this.apiClient.setAccessToken(token.access_token);
            return true;
        } catch (error) {
            console.error("Login failed:", error);
            return false;
        }
    }

    async sync(): Promise<void> {
        if (this.status === "syncing") {
            new Notice("Synchronisation déjà en cours...");
            return;
        }

        if (!this.settings.accessToken) {
            new Notice("Veuillez vous connecter d'abord");
            return;
        }

        this.setStatus("syncing");
        new Notice("Synchronisation en cours...");

        try {
            // 1. Collecter les métadonnées des notes locales (incluant les suppressions)
            const localNotes = await this.collectLocalNotes();

            // 2. Envoyer au serveur pour comparaison
            const syncResponse = await this.apiClient.sync({
                last_sync: this.settings.lastSync,
                notes: localNotes,
                attachments: [],
            });

            // 3. Pousser les notes demandées par le serveur (incluant les suppressions)
            let deletedCount = 0;
            if (syncResponse.notes_to_push.length > 0) {
                // Compter les suppressions envoyées
                const localNotesMap = new Map(localNotes.map((n) => [n.path, n]));
                deletedCount = syncResponse.notes_to_push.filter(
                    (path) => localNotesMap.get(path)?.is_deleted
                ).length;
                await this.pushNotes(syncResponse.notes_to_push, localNotes);
            }

            // 4. Récupérer les notes du serveur
            let receivedDeletedCount = 0;
            if (syncResponse.notes_to_pull.length > 0) {
                // Compter les suppressions reçues
                receivedDeletedCount = syncResponse.notes_to_pull.filter(
                    (n) => n.is_deleted
                ).length;
                await this.pullNotes(
                    syncResponse.notes_to_pull.map((n) => n.path)
                );
            }

            // 5. Gérer les conflits
            if (syncResponse.conflicts.length > 0) {
                await this.handleConflicts(syncResponse.conflicts);
            }

            // 6. Mettre à jour le timestamp de dernière sync
            this.settings.lastSync = syncResponse.server_time;

            // 7. Mettre à jour la liste des fichiers connus après sync réussi
            this.settings.knownFiles = this.app.vault
                .getMarkdownFiles()
                .map((f) => f.path);

            this.setStatus("success");
            
            // Construire le message de notification
            const totalDeleted = deletedCount + receivedDeletedCount;
            let message = `Synchronisation terminée! ${syncResponse.notes_to_push.length} envoyées, ${syncResponse.notes_to_pull.length} reçues`;
            if (totalDeleted > 0) {
                message += `, ${totalDeleted} supprimée${totalDeleted > 1 ? 's' : ''}`;
            }
            new Notice(message);

            // Revenir à idle après 3 secondes
            setTimeout(() => this.setStatus("idle"), 3000);
        } catch (error) {
            console.error("Sync failed:", error);
            this.setStatus("error");
            new Notice(`Erreur de synchronisation: ${error.message}`);

            // Revenir à idle après 5 secondes
            setTimeout(() => this.setStatus("idle"), 5000);
        }
    }

    private async collectLocalNotes(): Promise<NoteMetadata[]> {
        const notes: NoteMetadata[] = [];
        const files = this.app.vault.getMarkdownFiles();
        const currentPaths = new Set<string>();

        for (const file of files) {
            const content = await this.app.vault.read(file);
            const hash = await this.computeHash(content);
            currentPaths.add(file.path);

            notes.push({
                path: file.path,
                content_hash: hash,
                modified_at: new Date(file.stat.mtime).toISOString(),
                is_deleted: false,
            });
        }

        // Détecter les fichiers supprimés (présents dans knownFiles mais plus localement)
        // Ne détecter les suppressions que si knownFiles n'est pas vide (évite faux positifs au premier sync)
        if (this.settings.knownFiles && this.settings.knownFiles.length > 0) {
            for (const knownPath of this.settings.knownFiles) {
                if (!currentPaths.has(knownPath)) {
                    // Fichier supprimé localement
                    notes.push({
                        path: knownPath,
                        content_hash: "",
                        modified_at: new Date().toISOString(),
                        is_deleted: true,
                    });
                }
            }
        }

        return notes;
    }

    private async pushNotes(paths: string[], localNotes: NoteMetadata[]): Promise<void> {
        const notesToPush: NoteContent[] = [];
        const localNotesMap = new Map(localNotes.map((n) => [n.path, n]));

        for (const path of paths) {
            const localNote = localNotesMap.get(path);
            
            if (localNote && localNote.is_deleted) {
                // Note supprimée localement
                notesToPush.push({
                    path: path,
                    content: "",
                    content_hash: "",
                    modified_at: localNote.modified_at,
                    is_deleted: true,
                });
            } else {
                // Note existante
                const file = this.app.vault.getAbstractFileByPath(path);
                if (file instanceof TFile) {
                    const content = await this.app.vault.read(file);
                    notesToPush.push({
                        path: path,
                        content: content,
                        content_hash: await this.computeHash(content),
                        modified_at: new Date(file.stat.mtime).toISOString(),
                        is_deleted: false,
                    });
                }
            }
        }

        if (notesToPush.length > 0) {
            await this.apiClient.pushNotes({ notes: notesToPush });
        }
    }

    private async pullNotes(paths: string[]): Promise<void> {
        if (paths.length === 0) return;

        const response = await this.apiClient.pullNotes({ paths });

        for (const note of response.notes) {
            if (note.is_deleted) {
                // Supprimer le fichier local
                const file = this.app.vault.getAbstractFileByPath(note.path);
                if (file instanceof TFile) {
                    await this.app.vault.delete(file);
                }
            } else {
                // Créer ou mettre à jour le fichier
                const existingFile = this.app.vault.getAbstractFileByPath(
                    note.path
                );
                if (existingFile instanceof TFile) {
                    await this.app.vault.modify(existingFile, note.content);
                } else {
                    // S'assurer que le dossier parent existe
                    const folder = note.path.substring(
                        0,
                        note.path.lastIndexOf("/")
                    );
                    if (
                        folder &&
                        !this.app.vault.getAbstractFileByPath(folder)
                    ) {
                        await this.app.vault.createFolder(folder);
                    }
                    await this.app.vault.create(note.path, note.content);
                }
            }
        }
    }

    private async handleConflicts(conflicts: NoteMetadata[]): Promise<void> {
        for (const conflict of conflicts) {
            // Récupérer la version serveur
            const response = await this.apiClient.pullNotes({
                paths: [conflict.path],
            });

            if (response.notes.length > 0) {
                const serverNote = response.notes[0];

                // Créer un fichier de conflit
                const date = new Date().toISOString().split("T")[0];
                const conflictPath = conflict.path.replace(
                    ".md",
                    ` (conflit ${date}).md`
                );

                // Sauvegarder la version serveur comme fichier de conflit
                await this.app.vault.create(conflictPath, serverNote.content);

                new Notice(`Conflit détecté: ${conflict.path}`);
            }
        }
    }
}
