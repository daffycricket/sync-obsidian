import { App, TFile, Notice, arrayBufferToBase64 } from "obsidian";
import { ApiClient } from "./api-client";
import {
    SyncObsidianSettings,
    NoteMetadata,
    NoteContent,
    AttachmentMetadata,
    AttachmentContent,
    SyncStatus,
    SyncReportEntry,
    SyncFileInfo,
    SyncConflictInfo,
    SyncFailedFile,
} from "./types";

// Limite de taille pour les attachments (25 Mo)
const MAX_ATTACHMENT_SIZE = 25 * 1024 * 1024;

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

    private async computeBinaryHash(content: ArrayBuffer): Promise<string> {
        // SHA256 pour les fichiers binaires
        const hashBuffer = await crypto.subtle.digest("SHA-256", content);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
    }

    private getMimeType(path: string): string | null {
        const ext = path.split(".").pop()?.toLowerCase();
        const mimeTypes: Record<string, string> = {
            // Images
            png: "image/png",
            jpg: "image/jpeg",
            jpeg: "image/jpeg",
            gif: "image/gif",
            webp: "image/webp",
            svg: "image/svg+xml",
            bmp: "image/bmp",
            ico: "image/x-icon",
            // Documents
            pdf: "application/pdf",
            doc: "application/msword",
            docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            xls: "application/vnd.ms-excel",
            xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ppt: "application/vnd.ms-powerpoint",
            pptx: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            // Audio/Video
            mp3: "audio/mpeg",
            wav: "audio/wav",
            mp4: "video/mp4",
            webm: "video/webm",
            // Archives
            zip: "application/zip",
            rar: "application/x-rar-compressed",
            "7z": "application/x-7z-compressed",
            tar: "application/x-tar",
            gz: "application/gzip",
            // Autres
            txt: "text/plain",
            json: "application/json",
            xml: "application/xml",
            csv: "text/csv",
        };
        return ext ? mimeTypes[ext] || "application/octet-stream" : null;
    }

    /**
     * Détecte les fichiers supprimés (présents dans knownPaths mais plus localement)
     */
    private detectDeletedFiles(currentPaths: Set<string>, knownPaths: string[]): string[] {
        if (!knownPaths || knownPaths.length === 0) {
            return [];
        }
        return knownPaths.filter(path => !currentPaths.has(path));
    }

    /**
     * Extrait les détails d'erreur pour un chemin de fichier
     * Détecte les caractères invalides selon les OS
     */
    private extractErrorDetails(error: Error, path: string): string | undefined {
        // Caractères problématiques cross-platform : \ / : * ? " < > |
        const invalidChars = /[:\\*?"<>|]/g;
        const matches = path.match(invalidChars);
        
        if (matches) {
            const uniqueChars = [...new Set(matches)].join(" ");
            return `Caractères problématiques : ${uniqueChars}`;
        }
        
        return undefined;
    }

    /**
     * Détermine le statut du rapport de synchronisation
     */
    private determineStatus(
        conflicts: SyncConflictInfo[],
        failed: SyncFailedFile[],
        errorType?: "server" | "local" | "network" | "auth"
    ): "success" | "warning" | "error" {
        if (errorType) {
            return "error";
        }
        if (conflicts.length > 0 || failed.length > 0) {
            return "warning";
        }
        return "success";
    }

    /**
     * Nettoie l'historique des rapports selon les settings
     */
    private cleanupHistory(): void {
        const now = Date.now();
        const maxAge = this.settings.reportHistoryHours * 60 * 60 * 1000;
        
        this.settings.syncHistory = this.settings.syncHistory.filter((entry) => {
            const entryTime = new Date(entry.timestamp).getTime();
            return now - entryTime <= maxAge;
        });
    }

    /**
     * Ajoute un rapport à l'historique
     */
    private addReportToHistory(report: SyncReportEntry): void {
        // Mode "last" : garder uniquement le dernier
        if (this.settings.reportMode === "last") {
            this.settings.syncHistory = [report];
        } else {
            // Mode "history" : ajouter et nettoyer
            this.settings.syncHistory.unshift(report);
            this.cleanupHistory();
        }
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

        const startTime = Date.now();
        
        // Initialiser le rapport
        const report: SyncReportEntry = {
            timestamp: new Date().toISOString(),
            status: "success",
            duration_ms: 0,
            sent: [],
            received: [],
            deleted: [],
            conflicts: [],
            failed: [],
            bytes_up: 0,
            bytes_down: 0,
        };

        try {
            // 1. Collecter les métadonnées des notes et attachments locaux
            const { notes: localNotes, failed: collectNotesFailed } = await this.collectLocalNotes();
            const { attachments: localAttachments, failed: collectAttFailed } = await this.collectLocalAttachments();
            report.failed.push(...collectNotesFailed, ...collectAttFailed);

            // 2. Envoyer au serveur pour comparaison
            const syncResponse = await this.apiClient.sync({
                last_sync: this.settings.lastSync,
                notes: localNotes,
                attachments: localAttachments,
            });

            // 3. Pousser les notes demandées par le serveur (incluant les suppressions)
            if (syncResponse.notes_to_push.length > 0) {
                const localNotesMap = new Map(localNotes.map((n) => [n.path, n]));
                const { sent, deleted, failed: pushFailed, bytesUp } = 
                    await this.pushNotes(syncResponse.notes_to_push, localNotes);
                
                report.sent.push(...sent);
                report.deleted.push(...deleted);
                report.failed.push(...pushFailed);
                report.bytes_up = bytesUp;
            }

            // 4. Récupérer les notes du serveur
            if (syncResponse.notes_to_pull.length > 0) {
                const { received, deleted, failed: pullFailed, bytesDown } = 
                    await this.pullNotes(syncResponse.notes_to_pull.map((n) => n.path));
                
                report.received.push(...received);
                // Ajouter les suppressions reçues (côté serveur)
                deleted.forEach(d => {
                    if (!report.deleted.includes(d)) {
                        report.deleted.push(d);
                    }
                });
                report.failed.push(...pullFailed);
                report.bytes_down = bytesDown;
            }

            // 5. Gérer les conflits
            if (syncResponse.conflicts.length > 0) {
                const { conflicts, failed: conflictFailed } =
                    await this.handleConflicts(syncResponse.conflicts);

                report.conflicts.push(...conflicts);
                report.failed.push(...conflictFailed);
            }

            // 6. Pousser les attachments demandés par le serveur
            if (syncResponse.attachments_to_push.length > 0) {
                const { sent, failed: pushAttFailed, bytesUp } =
                    await this.pushAttachments(syncResponse.attachments_to_push, localAttachments);

                report.sent.push(...sent);
                report.failed.push(...pushAttFailed);
                report.bytes_up += bytesUp;
            }

            // 7. Récupérer les attachments du serveur
            if (syncResponse.attachments_to_pull.length > 0) {
                const paths = syncResponse.attachments_to_pull.map((a) => a.path);
                const { received, failed: pullAttFailed, bytesDown } =
                    await this.pullAttachments(paths);

                report.received.push(...received);
                report.failed.push(...pullAttFailed);
                report.bytes_down += bytesDown;
            }

            // 8. Mettre à jour le timestamp de dernière sync
            this.settings.lastSync = syncResponse.server_time;

            // 9. Mettre à jour la liste des fichiers connus après sync réussi
            this.settings.knownFiles = this.app.vault
                .getMarkdownFiles()
                .map((f) => f.path);

            // Mettre à jour les attachments connus
            this.settings.knownAttachments = this.app.vault
                .getFiles()
                .filter((f) => !f.path.endsWith(".md"))
                .map((f) => f.path);

            // Finaliser le rapport
            report.duration_ms = Date.now() - startTime;
            report.status = this.determineStatus(report.conflicts, report.failed);
            
            // Ajouter le rapport à l'historique
            this.addReportToHistory(report);

            this.setStatus(report.status === "error" ? "error" : "success");
            
            // Construire le message de notification
            const totalDeleted = report.deleted.length;
            let message = `Synchronisation terminée! ${report.sent.length} envoyées, ${report.received.length} reçues`;
            if (totalDeleted > 0) {
                message += `, ${totalDeleted} supprimée${totalDeleted > 1 ? 's' : ''}`;
            }
            if (report.conflicts.length > 0) {
                message += `, ${report.conflicts.length} conflit${report.conflicts.length > 1 ? 's' : ''}`;
            }
            if (report.failed.length > 0) {
                message += `, ${report.failed.length} échec${report.failed.length > 1 ? 's' : ''}`;
            }
            new Notice(message);

            // Revenir à idle après 3 secondes
            setTimeout(() => this.setStatus("idle"), 3000);
        } catch (error) {
            console.error("Sync failed:", error);
            
            // Finaliser le rapport avec l'erreur
            report.duration_ms = Date.now() - startTime;
            report.status = "error";
            
            // Déterminer le type d'erreur
            if (error.message?.includes("401") || error.message?.includes("auth")) {
                report.error_type = "auth";
            } else if (error.message?.includes("fetch") || error.message?.includes("network") || error.message?.includes("ENOTFOUND")) {
                report.error_type = "network";
            } else if (error.message?.includes("500") || error.message?.includes("502") || error.message?.includes("503")) {
                report.error_type = "server";
            } else {
                report.error_type = "local";
            }
            
            report.error_message = error.message;
            report.stack_trace = error.stack;
            
            // Ajouter le rapport à l'historique
            this.addReportToHistory(report);
            
            this.setStatus("error");
            new Notice(`Erreur de synchronisation: ${error.message}`);

            // Revenir à idle après 5 secondes
            setTimeout(() => this.setStatus("idle"), 5000);
        }
    }

    private async collectLocalNotes(): Promise<{ notes: NoteMetadata[]; failed: SyncFailedFile[] }> {
        const notes: NoteMetadata[] = [];
        const failed: SyncFailedFile[] = [];
        const files = this.app.vault.getMarkdownFiles();
        const currentPaths = new Set<string>();

        for (const file of files) {
            try {
                const content = await this.app.vault.read(file);
                const hash = await this.computeHash(content);
                currentPaths.add(file.path);

                notes.push({
                    path: file.path,
                    content_hash: hash,
                    modified_at: new Date(file.stat.mtime).toISOString(),
                    is_deleted: false,
                });
            } catch (error) {
                // Fichier illisible - on le skip et on continue
                failed.push({
                    path: file.path,
                    error: error.message || "Erreur de lecture",
                    details: this.extractErrorDetails(error, file.path),
                });
                currentPaths.add(file.path); // Le marquer comme présent pour éviter de le considérer supprimé
            }
        }

        // Détecter les fichiers supprimés
        for (const deletedPath of this.detectDeletedFiles(currentPaths, this.settings.knownFiles)) {
            notes.push({
                path: deletedPath,
                content_hash: "",
                modified_at: new Date().toISOString(),
                is_deleted: true,
            });
        }

        return { notes, failed };
    }

    private async collectLocalAttachments(): Promise<{
        attachments: AttachmentMetadata[];
        failed: SyncFailedFile[];
    }> {
        const attachments: AttachmentMetadata[] = [];
        const failed: SyncFailedFile[] = [];
        const currentPaths = new Set<string>();

        // Récupérer tous les fichiers non-markdown
        const allFiles = this.app.vault.getFiles();
        const nonMdFiles = allFiles.filter((f) => !f.path.endsWith(".md"));

        for (const file of nonMdFiles) {
            try {
                // Vérifier la taille (25 Mo max)
                if (file.stat.size > MAX_ATTACHMENT_SIZE) {
                    failed.push({
                        path: file.path,
                        error: "Fichier trop volumineux (max 25 Mo)",
                    });
                    continue;
                }

                const content = await this.app.vault.readBinary(file);
                const hash = await this.computeBinaryHash(content);
                currentPaths.add(file.path);

                attachments.push({
                    path: file.path,
                    content_hash: hash,
                    size: file.stat.size,
                    mime_type: this.getMimeType(file.path),
                    modified_at: new Date(file.stat.mtime).toISOString(),
                    is_deleted: false,
                });
            } catch (error) {
                failed.push({
                    path: file.path,
                    error: error.message || "Erreur de lecture",
                    details: this.extractErrorDetails(error, file.path),
                });
                currentPaths.add(file.path);
            }
        }

        // Détecter les attachments supprimés
        for (const deletedPath of this.detectDeletedFiles(currentPaths, this.settings.knownAttachments)) {
            attachments.push({
                path: deletedPath,
                content_hash: "",
                size: 0,
                mime_type: null,
                modified_at: new Date().toISOString(),
                is_deleted: true,
            });
        }

        return { attachments, failed };
    }

    private async pushAttachments(
        paths: string[],
        localAttachments: AttachmentMetadata[]
    ): Promise<{ sent: SyncFileInfo[]; failed: SyncFailedFile[]; bytesUp: number }> {
        const attachmentsToSend: AttachmentContent[] = [];
        const sent: SyncFileInfo[] = [];
        const failed: SyncFailedFile[] = [];
        let bytesUp = 0;

        const localAttMap = new Map(localAttachments.map((a) => [a.path, a]));

        for (const path of paths) {
            try {
                const localAtt = localAttMap.get(path);

                if (localAtt && localAtt.is_deleted) {
                    // Attachment supprimé
                    attachmentsToSend.push({
                        path: path,
                        content_base64: "",
                        content_hash: "",
                        size: 0,
                        mime_type: null,
                        modified_at: localAtt.modified_at,
                        is_deleted: true,
                    });
                } else {
                    const file = this.app.vault.getAbstractFileByPath(path);
                    if (file instanceof TFile) {
                        const content = await this.app.vault.readBinary(file);
                        const base64 = arrayBufferToBase64(content);
                        const hash = await this.computeBinaryHash(content);

                        attachmentsToSend.push({
                            path: path,
                            content_base64: base64,
                            content_hash: hash,
                            size: file.stat.size,
                            mime_type: this.getMimeType(path),
                            modified_at: new Date(file.stat.mtime).toISOString(),
                            is_deleted: false,
                        });

                        bytesUp += file.stat.size;
                        sent.push({ path, size_delta: file.stat.size });
                    }
                }
            } catch (error) {
                failed.push({
                    path,
                    error: error.message || "Erreur d'envoi",
                    details: this.extractErrorDetails(error, path),
                });
            }
        }

        if (attachmentsToSend.length > 0) {
            await this.apiClient.pushAttachments({ attachments: attachmentsToSend });
        }

        return { sent, failed, bytesUp };
    }

    private async pullAttachments(
        paths: string[]
    ): Promise<{ received: SyncFileInfo[]; failed: SyncFailedFile[]; bytesDown: number }> {
        const received: SyncFileInfo[] = [];
        const failed: SyncFailedFile[] = [];
        let bytesDown = 0;

        if (paths.length === 0) {
            return { received, failed, bytesDown };
        }

        const response = await this.apiClient.pullAttachments({ paths });

        for (const att of response.attachments) {
            try {
                if (att.is_deleted) {
                    // Supprimer l'attachment local
                    const file = this.app.vault.getAbstractFileByPath(att.path);
                    if (file instanceof TFile) {
                        await this.app.vault.delete(file);
                    }
                } else {
                    bytesDown += att.size;

                    // Décoder le base64
                    const binaryString = atob(att.content_base64);
                    const bytes = new Uint8Array(binaryString.length);
                    for (let i = 0; i < binaryString.length; i++) {
                        bytes[i] = binaryString.charCodeAt(i);
                    }
                    const content = bytes.buffer;

                    // Créer le dossier parent si nécessaire
                    const folder = att.path.substring(0, att.path.lastIndexOf("/"));
                    if (folder && !this.app.vault.getAbstractFileByPath(folder)) {
                        await this.app.vault.createFolder(folder);
                    }

                    // Créer ou écraser le fichier
                    const existingFile = this.app.vault.getAbstractFileByPath(att.path);
                    if (existingFile instanceof TFile) {
                        await this.app.vault.modifyBinary(existingFile, content);
                    } else {
                        await this.app.vault.createBinary(att.path, content);
                    }

                    received.push({ path: att.path, size_delta: att.size });
                }
            } catch (error) {
                failed.push({
                    path: att.path,
                    error: error.message || "Erreur d'écriture",
                    details: this.extractErrorDetails(error, att.path),
                });
            }
        }

        return { received, failed, bytesDown };
    }

    private async pushNotes(
        paths: string[], 
        localNotes: NoteMetadata[]
    ): Promise<{ sent: SyncFileInfo[]; deleted: string[]; failed: SyncFailedFile[]; bytesUp: number }> {
        const notesToPush: NoteContent[] = [];
        const sent: SyncFileInfo[] = [];
        const deleted: string[] = [];
        const failed: SyncFailedFile[] = [];
        let bytesUp = 0;
        
        const localNotesMap = new Map(localNotes.map((n) => [n.path, n]));

        for (const path of paths) {
            try {
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
                    deleted.push(path);
                } else {
                    // Note existante
                    const file = this.app.vault.getAbstractFileByPath(path);
                    if (file instanceof TFile) {
                        const content = await this.app.vault.read(file);
                        const contentBytes = new TextEncoder().encode(content).length;
                        bytesUp += contentBytes;
                        
                        notesToPush.push({
                            path: path,
                            content: content,
                            content_hash: await this.computeHash(content),
                            modified_at: new Date(file.stat.mtime).toISOString(),
                            is_deleted: false,
                        });
                        sent.push({ path, size_delta: contentBytes });
                    }
                }
            } catch (error) {
                // Échec sur ce fichier - continuer avec les autres
                failed.push({
                    path: path,
                    error: error.message || "Erreur d'envoi",
                    details: this.extractErrorDetails(error, path),
                });
            }
        }

        if (notesToPush.length > 0) {
            await this.apiClient.pushNotes({ notes: notesToPush });
        }
        
        return { sent, deleted, failed, bytesUp };
    }

    private async pullNotes(
        paths: string[]
    ): Promise<{ received: SyncFileInfo[]; deleted: string[]; failed: SyncFailedFile[]; bytesDown: number }> {
        const received: SyncFileInfo[] = [];
        const deleted: string[] = [];
        const failed: SyncFailedFile[] = [];
        let bytesDown = 0;
        
        if (paths.length === 0) {
            return { received, deleted, failed, bytesDown };
        }

        const response = await this.apiClient.pullNotes({ paths });

        for (const note of response.notes) {
            try {
                if (note.is_deleted) {
                    // Supprimer le fichier local
                    const file = this.app.vault.getAbstractFileByPath(note.path);
                    if (file instanceof TFile) {
                        await this.app.vault.delete(file);
                    }
                    deleted.push(note.path);
                } else {
                    // Calculer la taille
                    const contentBytes = new TextEncoder().encode(note.content).length;
                    bytesDown += contentBytes;
                    
                    // Créer ou mettre à jour le fichier
                    const existingFile = this.app.vault.getAbstractFileByPath(note.path);
                    
                    if (existingFile instanceof TFile) {
                        // Calculer le delta de taille
                        const oldContent = await this.app.vault.read(existingFile);
                        const oldBytes = new TextEncoder().encode(oldContent).length;
                        const sizeDelta = contentBytes - oldBytes;
                        
                        await this.app.vault.modify(existingFile, note.content);
                        received.push({ path: note.path, size_delta: sizeDelta });
                    } else {
                        // S'assurer que le dossier parent existe
                        const folder = note.path.substring(0, note.path.lastIndexOf("/"));
                        if (folder && !this.app.vault.getAbstractFileByPath(folder)) {
                            await this.app.vault.createFolder(folder);
                        }
                        await this.app.vault.create(note.path, note.content);
                        received.push({ path: note.path, size_delta: contentBytes });
                    }
                }
            } catch (error) {
                // Échec sur ce fichier - continuer avec les autres
                failed.push({
                    path: note.path,
                    error: error.message || "Erreur d'écriture",
                    details: this.extractErrorDetails(error, note.path),
                });
            }
        }
        
        return { received, deleted, failed, bytesDown };
    }

    private async handleConflicts(
        conflictMetas: NoteMetadata[]
    ): Promise<{ conflicts: SyncConflictInfo[]; failed: SyncFailedFile[] }> {
        const conflicts: SyncConflictInfo[] = [];
        const failed: SyncFailedFile[] = [];
        
        for (const conflict of conflictMetas) {
            try {
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

                    conflicts.push({
                        path: conflict.path,
                        conflict_file: conflictPath,
                    });

                    new Notice(`Conflit détecté: ${conflict.path}`);
                }
            } catch (error) {
                // Échec sur ce conflit - continuer avec les autres
                failed.push({
                    path: conflict.path,
                    error: error.message || "Erreur de gestion du conflit",
                    details: this.extractErrorDetails(error, conflict.path),
                });
            }
        }
        
        return { conflicts, failed };
    }
}
