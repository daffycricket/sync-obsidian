import { Plugin, Notice } from "obsidian";
import { SyncObsidianSettings, DEFAULT_SETTINGS, SyncStatus } from "./types";
import { SyncService } from "./sync-service";
import { SyncObsidianSettingTab } from "./settings";

export default class SyncObsidianPlugin extends Plugin {
    settings: SyncObsidianSettings;
    syncService: SyncService;
    statusBarItem: HTMLElement | null = null;
    autoSyncIntervalId: number | null = null;

    async onload() {
        await this.loadSettings();

        // Initialiser le service de sync
        this.syncService = new SyncService(
            this.app,
            this.settings,
            (status) => this.onSyncStatusChange(status)
        );

        // Ajouter la barre de statut
        this.statusBarItem = this.addStatusBarItem();
        this.updateStatusBar();

        // Ajouter les commandes
        this.addCommand({
            id: "sync-now",
            name: "Synchroniser maintenant",
            callback: async () => {
                await this.syncService.sync();
                await this.saveSettings();
            },
        });

        // Ajouter l'onglet de paramètres
        this.addSettingTab(new SyncObsidianSettingTab(this.app, this));

        // Configurer la sync automatique
        this.setupAutoSync();

        // Ajouter un bouton dans la barre latérale (ribbon)
        this.addRibbonIcon("refresh-cw", "Synchroniser", async () => {
            await this.syncService.sync();
            await this.saveSettings();
        });

        console.log("SyncObsidian plugin loaded");
    }

    onunload() {
        if (this.autoSyncIntervalId) {
            window.clearInterval(this.autoSyncIntervalId);
        }
        console.log("SyncObsidian plugin unloaded");
    }

    async loadSettings() {
        this.settings = Object.assign(
            {},
            DEFAULT_SETTINGS,
            await this.loadData()
        );
    }

    async saveSettings() {
        await this.saveData(this.settings);
        if (this.syncService) {
            this.syncService.updateSettings(this.settings);
        }
    }

    setupAutoSync() {
        // Nettoyer l'ancien intervalle
        if (this.autoSyncIntervalId) {
            window.clearInterval(this.autoSyncIntervalId);
            this.autoSyncIntervalId = null;
        }

        // Configurer le nouveau si activé
        if (this.settings.autoSyncInterval > 0) {
            const intervalMs = this.settings.autoSyncInterval * 60 * 1000;
            this.autoSyncIntervalId = window.setInterval(async () => {
                if (this.settings.accessToken) {
                    console.log("Auto-sync triggered");
                    await this.syncService.sync();
                    await this.saveSettings();
                }
            }, intervalMs);

            console.log(
                `Auto-sync configured: every ${this.settings.autoSyncInterval} minutes`
            );
        }
    }

    updateStatusBar() {
        if (!this.statusBarItem) return;

        if (!this.settings.showStatusBar) {
            this.statusBarItem.setText("");
            return;
        }

        const status = this.syncService?.getStatus() || "idle";
        this.statusBarItem.setText(this.getStatusText(status));
    }

    private getStatusText(status: SyncStatus): string {
        switch (status) {
            case "syncing":
                return "🔄 Sync...";
            case "success":
                return "✅ Sync OK";
            case "error":
                return "❌ Sync Error";
            default:
                return "☁️ SyncObsidian";
        }
    }

    private onSyncStatusChange(status: SyncStatus) {
        this.updateStatusBar();
    }
}
