import { App, PluginSettingTab, Setting, Notice } from "obsidian";
import SyncObsidianPlugin from "./main";
import { ApiClient } from "./api-client";

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
                        this.display(); // Rafraîchir l'affichage
                    })
            );
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
}
