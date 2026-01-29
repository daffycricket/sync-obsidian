import { App, PluginSettingTab, Setting, Notice } from "obsidian";
import SyncObsidianPlugin from "./main";
import { ApiClient } from "./api-client";
import { SyncReportEntry, SyncedNotesResponse, CompareResponse } from "./types";

export class SyncObsidianSettingTab extends PluginSettingTab {
    plugin: SyncObsidianPlugin;

    constructor(app: App, plugin: SyncObsidianPlugin) {
        super(app, plugin);
        this.plugin = plugin;
    }

    display(): void {
        const { containerEl } = this;

        containerEl.empty();

        containerEl.createEl("h2", { text: "SyncObsidian - Configuration" });

        // Section Serveur
        containerEl.createEl("h3", { text: "Connexion au serveur" });

        new Setting(containerEl)
            .setName("URL du serveur")
            .setDesc("L'adresse de votre serveur SyncObsidian (ex: https://sync.example.com)")
            .addText((text) =>
                text
                    .setPlaceholder("https://sync.example.com")
                    .setValue(this.plugin.settings.serverUrl)
                    .onChange(async (value) => {
                        this.plugin.settings.serverUrl = value;
                        await this.plugin.saveSettings();
                    })
            );

        new Setting(containerEl)
            .setName("Nom d'utilisateur")
            .setDesc("Votre nom d'utilisateur")
            .addText((text) =>
                text
                    .setPlaceholder("username")
                    .setValue(this.plugin.settings.username)
                    .onChange(async (value) => {
                        this.plugin.settings.username = value;
                        await this.plugin.saveSettings();
                    })
            );

        new Setting(containerEl)
            .setName("Mot de passe")
            .setDesc("Votre mot de passe")
            .addText((text) => {
                text.inputEl.type = "password";
                text.setPlaceholder("••••••••")
                    .setValue(this.plugin.settings.password)
                    .onChange(async (value) => {
                        this.plugin.settings.password = value;
                        await this.plugin.saveSettings();
                    });
            });

        // Boutons de connexion
        new Setting(containerEl)
            .setName("Connexion")
            .setDesc(
                this.plugin.settings.accessToken
                    ? "✅ Connecté"
                    : "❌ Non connecté"
            )
            .addButton((button) =>
                button
                    .setButtonText("Se connecter")
                    .setCta()
                    .onClick(async () => {
                        await this.handleLogin();
                    })
            )
            .addButton((button) =>
                button.setButtonText("Tester la connexion").onClick(async () => {
                    await this.testConnection();
                })
            );

        // Section Synchronisation
        containerEl.createEl("h3", { text: "Synchronisation" });

        new Setting(containerEl)
            .setName("Synchronisation automatique")
            .setDesc(
                "Intervalle de synchronisation automatique (en minutes, 0 = désactivé)"
            )
            .addText((text) =>
                text
                    .setPlaceholder("5")
                    .setValue(String(this.plugin.settings.autoSyncInterval))
                    .onChange(async (value) => {
                        const interval = parseInt(value) || 0;
                        this.plugin.settings.autoSyncInterval = interval;
                        await this.plugin.saveSettings();
                        this.plugin.setupAutoSync();
                    })
            );

        new Setting(containerEl)
            .setName("Afficher la barre de statut")
            .setDesc("Afficher l'état de synchronisation dans la barre de statut")
            .addToggle((toggle) =>
                toggle
                    .setValue(this.plugin.settings.showStatusBar)
                    .onChange(async (value) => {
                        this.plugin.settings.showStatusBar = value;
                        await this.plugin.saveSettings();
                        this.plugin.updateStatusBar();
                    })
            );

        // Dernière synchronisation
        if (this.plugin.settings.lastSync) {
            const lastSyncDate = new Date(this.plugin.settings.lastSync);
            containerEl.createEl("p", {
                text: `Dernière synchronisation: ${lastSyncDate.toLocaleString()}`,
                cls: "setting-item-description",
            });
        }

        // Bouton de sync manuelle
        new Setting(containerEl)
            .setName("Synchronisation manuelle")
            .setDesc("Lancer une synchronisation maintenant")
            .addButton((button) =>
                button
                    .setButtonText("Synchroniser maintenant")
                    .setCta()
                    .onClick(async () => {
                        await this.plugin.syncService.sync();
                        await this.plugin.saveSettings();
                        this.display(); // Rafraîchir l'affichage
                    })
            );

        // Section Notes synchronisées
        containerEl.createEl("h3", { text: "Notes synchronisées" });

        // Bouton pour ouvrir sync-viewer dans le navigateur
        new Setting(containerEl)
            .setName("Visualiser les notes sur le serveur")
            .setDesc("Ouvrir la page de visualisation dans le navigateur")
            .addButton((button) =>
                button
                    .setButtonText("Ouvrir sync-viewer")
                    .onClick(async () => {
                        await this.openSyncViewer();
                    })
            );

        // Bouton pour comparer client/serveur
        new Setting(containerEl)
            .setName("Comparer avec le serveur")
            .setDesc("Analyser les différences entre vos notes locales et le serveur")
            .addButton((button) =>
                button
                    .setButtonText("Comparer")
                    .onClick(async () => {
                        await this.runCompare(containerEl);
                    })
            );

        // Container pour les résultats de comparaison
        const compareResultContainer = containerEl.createEl("div", {
            attr: { id: "compare-result-container" }
        });

        // Section Rapport de synchronisation
        containerEl.createEl("h3", { text: "Rapport de synchronisation" });

        // Mode d'historique
        new Setting(containerEl)
            .setName("Historique affiché")
            .setDesc("Choisir ce qui est affiché dans le rapport")
            .addDropdown((dropdown) =>
                dropdown
                    .addOption("last", "Dernière sync uniquement")
                    .addOption("history", "Historique (heures)")
                    .setValue(this.plugin.settings.reportMode)
                    .onChange(async (value: "last" | "history") => {
                        this.plugin.settings.reportMode = value;
                        await this.plugin.saveSettings();
                        this.display();
                    })
            );

        // Durée de l'historique (visible seulement en mode history)
        if (this.plugin.settings.reportMode === "history") {
            new Setting(containerEl)
                .setName("Durée de l'historique")
                .setDesc("Nombre d'heures d'historique à conserver (1-168)")
                .addText((text) =>
                    text
                        .setPlaceholder("24")
                        .setValue(String(this.plugin.settings.reportHistoryHours))
                        .onChange(async (value) => {
                            let hours = parseInt(value) || 24;
                            hours = Math.max(1, Math.min(168, hours));
                            this.plugin.settings.reportHistoryHours = hours;
                            await this.plugin.saveSettings();
                        })
                );
        }

        // Afficher les stack traces
        new Setting(containerEl)
            .setName("Afficher les stack traces")
            .setDesc("Afficher les détails techniques en cas d'erreur")
            .addToggle((toggle) =>
                toggle
                    .setValue(this.plugin.settings.reportShowStackTrace)
                    .onChange(async (value) => {
                        this.plugin.settings.reportShowStackTrace = value;
                        await this.plugin.saveSettings();
                        this.display();
                    })
            );

        // Bouton pour vider le rapport
        new Setting(containerEl)
            .setName("Vider le rapport")
            .setDesc("Supprimer tous les rapports de synchronisation (gagner de la place en local)")
            .addButton((button) =>
                button
                    .setButtonText("Vider")
                    .setWarning()
                    .onClick(async () => {
                        this.plugin.settings.syncHistory = [];
                        await this.plugin.saveSettings();
                        this.display();
                        new Notice("Rapport vidé");
                    })
            );

        // Zone du rapport
        const reportContainer = containerEl.createEl("div", {
            cls: "sync-report-container",
        });
        reportContainer.style.cssText = `
            background: var(--background-secondary);
            border-radius: 8px;
            padding: 16px;
            margin-top: 16px;
            max-height: 400px;
            overflow-y: auto;
            font-family: var(--font-monospace);
            font-size: 12px;
            white-space: pre-wrap;
            word-break: break-word;
            user-select: text;
            -webkit-user-select: text;
            -moz-user-select: text;
            -ms-user-select: text;
        `;

        // Générer le contenu du rapport
        const reportContent = this.generateReportContent();
        const reportPre = reportContainer.createEl("pre", {
            text: reportContent,
            cls: "sync-report-content",
        });
        // S'assurer que le texte est sélectionnable
        reportPre.style.cssText = `
            user-select: text;
            -webkit-user-select: text;
            -moz-user-select: text;
            -ms-user-select: text;
            margin: 0;
            padding: 0;
        `;
    }

    /**
     * Génère le contenu formaté du rapport
     */
    private generateReportContent(): string {
        const history = this.plugin.settings.syncHistory;
        
        if (!history || history.length === 0) {
            return "Aucune synchronisation enregistrée.";
        }

        const lines: string[] = [];

        for (const entry of history) {
            lines.push(this.formatReportEntry(entry));
            lines.push(""); // Ligne vide entre les entrées
        }

        return lines.join("\n");
    }

    /**
     * Formate une entrée de rapport
     */
    private formatReportEntry(entry: SyncReportEntry): string {
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
        
        const statusIcon = this.getStatusIcon(entry.status);
        const statusLabel = this.getStatusLabel(entry.status);
        
        lines.push("───────────────────────────────────────────────────────");
        lines.push(`📅 ${dateStr} ${timeStr}                     ${statusIcon} ${statusLabel}`);
        lines.push("───────────────────────────────────────────────────────");
        lines.push("");

        // En cas d'erreur complète
        if (entry.status === "error" && entry.error_type) {
            lines.push(`Type : Erreur ${this.getErrorTypeLabel(entry.error_type)}`);
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
            if (this.plugin.settings.reportShowStackTrace && entry.stack_trace) {
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
                        ? ` (${this.formatSize(file.size_delta)})`
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
                lines.push(`⏱️ Durée : ${this.formatDuration(entry.duration_ms)} | Aucun changement`);
            } else {
                lines.push(
                    `⏱️ Durée : ${this.formatDuration(entry.duration_ms)} | ` +
                    `📦 ↑${this.formatSize(entry.bytes_up)} ↓${this.formatSize(entry.bytes_down)}`
                );
            }
        }

        return lines.join("\n");
    }

    private getStatusIcon(status: "success" | "warning" | "error"): string {
        switch (status) {
            case "success": return "✅";
            case "warning": return "⚠️";
            case "error": return "❌";
        }
    }

    private getStatusLabel(status: "success" | "warning" | "error"): string {
        switch (status) {
            case "success": return "OK";
            case "warning": return "WARNING";
            case "error": return "ERREUR";
        }
    }

    private getErrorTypeLabel(type: "server" | "local" | "network" | "auth"): string {
        switch (type) {
            case "server": return "serveur";
            case "local": return "locale";
            case "network": return "réseau";
            case "auth": return "authentification";
        }
    }

    private formatSize(bytes: number): string {
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

    private formatDuration(ms: number): string {
        if (ms < 1000) {
            return `${ms}ms`;
        } else {
            return `${(ms / 1000).toFixed(1)}s`;
        }
    }

    private async handleLogin(): Promise<void> {
        const { serverUrl, username, password } = this.plugin.settings;

        if (!serverUrl || !username || !password) {
            new Notice("Veuillez remplir tous les champs");
            return;
        }

        const apiClient = new ApiClient(serverUrl);

        try {
            const token = await apiClient.login(username, password);
            this.plugin.settings.accessToken = token.access_token;
            await this.plugin.saveSettings();
            this.plugin.syncService.updateSettings(this.plugin.settings);
            new Notice("Connexion réussie!");
            this.display(); // Rafraîchir l'affichage
        } catch (error) {
            new Notice(`Échec de la connexion: ${error.message}`);
        }
    }

    private async testConnection(): Promise<void> {
        const { serverUrl } = this.plugin.settings;

        if (!serverUrl) {
            new Notice("Veuillez entrer l'URL du serveur");
            return;
        }

        const apiClient = new ApiClient(serverUrl);

        try {
            const isHealthy = await apiClient.checkHealth();
            if (isHealthy) {
                new Notice("✅ Serveur accessible!");
            } else {
                new Notice("❌ Serveur non accessible");
            }
        } catch (error) {
            new Notice(`❌ Erreur: ${error.message}`);
        }
    }

    private async openSyncViewer(): Promise<void> {
        const { serverUrl, accessToken } = this.plugin.settings;

        if (!serverUrl || !accessToken) {
            new Notice("Veuillez vous connecter d'abord");
            return;
        }

        const url = `${serverUrl}/sync-viewer?token=${accessToken}`;
        window.open(url, "_blank");
    }

    private async runCompare(containerEl: HTMLElement): Promise<void> {
        const { serverUrl, accessToken } = this.plugin.settings;

        if (!serverUrl || !accessToken) {
            new Notice("Veuillez vous connecter d'abord");
            return;
        }

        const apiClient = new ApiClient(serverUrl, accessToken);

        // Récupérer le container de résultat
        const resultContainer = containerEl.querySelector("#compare-result-container");
        if (!resultContainer) return;

        resultContainer.empty();
        resultContainer.createEl("p", { text: "Analyse en cours...", cls: "mod-muted" });

        try {
            // Collecter les notes locales
            const localNotes = await this.collectLocalNotes();

            // Appeler l'API de comparaison
            const result = await apiClient.compare({ notes: localNotes });

            // Afficher les résultats
            this.displayCompareResults(resultContainer as HTMLElement, result);
            new Notice(`Comparaison terminée: ${result.summary.identical} identiques, ${result.summary.to_push} à envoyer, ${result.summary.to_pull} à recevoir`);
        } catch (error) {
            resultContainer.empty();
            resultContainer.createEl("p", {
                text: `Erreur: ${error.message}`,
                cls: "mod-warning"
            });
            new Notice(`Erreur de comparaison: ${error.message}`);
        }
    }

    private async collectLocalNotes(): Promise<Array<{path: string, content_hash: string, modified_at: string}>> {
        const notes: Array<{path: string, content_hash: string, modified_at: string}> = [];
        const files = this.app.vault.getMarkdownFiles();

        for (const file of files) {
            const content = await this.app.vault.read(file);
            const hash = await this.hashContent(content);
            notes.push({
                path: file.path,
                content_hash: hash,
                modified_at: new Date(file.stat.mtime).toISOString()
            });
        }

        return notes;
    }

    private async hashContent(content: string): Promise<string> {
        const encoder = new TextEncoder();
        const data = encoder.encode(content);
        const hashBuffer = await crypto.subtle.digest("SHA-256", data);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
    }

    private displayCompareResults(container: HTMLElement, result: CompareResponse): void {
        container.empty();

        // Style du container
        container.style.cssText = `
            background: var(--background-secondary);
            border-radius: 8px;
            padding: 16px;
            margin-top: 12px;
        `;

        // Résumé
        const summary = result.summary;
        container.createEl("h4", { text: "Résultat de la comparaison" });

        const statsDiv = container.createEl("div", { cls: "compare-stats" });
        statsDiv.style.cssText = "display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 16px;";

        this.createStatCard(statsDiv, "📊 Client", String(summary.total_client));
        this.createStatCard(statsDiv, "☁️ Serveur", String(summary.total_server));
        this.createStatCard(statsDiv, "✅ Identiques", String(summary.identical));
        this.createStatCard(statsDiv, "↑ À envoyer", String(summary.to_push));
        this.createStatCard(statsDiv, "↓ À recevoir", String(summary.to_pull));
        this.createStatCard(statsDiv, "⚠️ Conflits", String(summary.conflicts));

        // Détails si nécessaire
        if (result.to_push.length > 0) {
            this.createFileList(container, "↑ À envoyer au serveur", result.to_push.map(n => `${n.path} (${n.reason})`));
        }

        if (result.to_pull.length > 0) {
            this.createFileList(container, "↓ À récupérer du serveur", result.to_pull.map(n => `${n.path} (${n.reason})`));
        }

        if (result.conflicts.length > 0) {
            this.createFileList(container, "⚠️ Conflits", result.conflicts.map(n => n.path));
        }

        if (result.deleted_on_server.length > 0) {
            this.createFileList(container, "🗑️ Supprimées sur serveur", result.deleted_on_server.map(n => n.path));
        }
    }

    private createStatCard(parent: HTMLElement, label: string, value: string): void {
        const card = parent.createEl("div");
        card.style.cssText = `
            background: var(--background-primary);
            padding: 8px 12px;
            border-radius: 6px;
            text-align: center;
        `;
        card.createEl("div", { text: value, cls: "stat-value" }).style.cssText = "font-size: 20px; font-weight: bold;";
        card.createEl("div", { text: label, cls: "stat-label" }).style.cssText = "font-size: 12px; color: var(--text-muted);";
    }

    private createFileList(parent: HTMLElement, title: string, files: string[]): void {
        const section = parent.createEl("details");
        section.style.cssText = "margin-top: 12px;";

        const summaryEl = section.createEl("summary");
        summaryEl.style.cssText = "cursor: pointer; font-weight: 500;";
        summaryEl.setText(`${title} (${files.length})`);

        const list = section.createEl("ul");
        list.style.cssText = "margin: 8px 0; padding-left: 20px; font-size: 12px;";

        for (const file of files.slice(0, 20)) {
            list.createEl("li", { text: file });
        }

        if (files.length > 20) {
            list.createEl("li", { text: `... et ${files.length - 20} autres`, cls: "mod-muted" });
        }
    }
}
