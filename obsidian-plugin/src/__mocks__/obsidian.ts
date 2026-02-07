// Mock de l'API Obsidian pour les tests

export interface RequestUrlParam {
    url: string;
    method?: string;
    headers?: Record<string, string>;
    body?: string;
}

export interface RequestUrlResponse {
    status: number;
    text: string;
    json: any;
}

// Mock de requestUrl - sera remplacé par jest.fn() dans les tests
export const requestUrl = jest.fn();

// Mock de Notice
export class Notice {
    constructor(message: string, timeout?: number) {}
}

// Mock de Plugin
export class Plugin {
    app: App;
    manifest: any;

    constructor() {
        this.app = new App();
    }

    loadData(): Promise<any> {
        return Promise.resolve({});
    }

    saveData(data: any): Promise<void> {
        return Promise.resolve();
    }

    addRibbonIcon(icon: string, title: string, callback: () => void): HTMLElement {
        return document.createElement('div');
    }

    addStatusBarItem(): HTMLElement {
        return document.createElement('div');
    }

    addCommand(command: any): void {}

    addSettingTab(tab: PluginSettingTab): void {}

    registerInterval(id: number): number {
        return id;
    }
}

// Mock de PluginSettingTab
export class PluginSettingTab {
    app: App;
    containerEl: HTMLElement;

    constructor(app: App, plugin: Plugin) {
        this.app = app;
        this.containerEl = document.createElement('div');
    }

    display(): void {}
    hide(): void {}
}

// Mock de Setting
export class Setting {
    static instances: Setting[] = [];
    settingEl: HTMLElement;
    _name: string = '';
    _textComponents: TextComponent[] = [];
    _extraButtonComponents: ExtraButtonComponent[] = [];

    constructor(containerEl: HTMLElement) {
        this.settingEl = document.createElement('div');
        Setting.instances.push(this);
    }

    setName(name: string): this { this._name = name; return this; }
    setDesc(desc: string): this { return this; }
    addText(cb: (text: TextComponent) => void): this {
        const text = new TextComponent();
        this._textComponents.push(text);
        cb(text);
        return this;
    }
    addToggle(cb: (toggle: ToggleComponent) => void): this {
        cb(new ToggleComponent());
        return this;
    }
    addButton(cb: (button: ButtonComponent) => void): this {
        cb(new ButtonComponent());
        return this;
    }
    addDropdown(cb: (dropdown: DropdownComponent) => void): this {
        cb(new DropdownComponent());
        return this;
    }
    addExtraButton(cb: (button: ExtraButtonComponent) => void): this {
        const button = new ExtraButtonComponent();
        this._extraButtonComponents.push(button);
        cb(button);
        return this;
    }
    setClass(cls: string): this { return this; }
}

// Mock des composants
export class TextComponent {
    setValue(value: string): this { return this; }
    setPlaceholder(placeholder: string): this { return this; }
    onChange(cb: (value: string) => void): this { return this; }
    inputEl: HTMLInputElement = document.createElement('input');
}

export class ToggleComponent {
    setValue(value: boolean): this { return this; }
    onChange(cb: (value: boolean) => void): this { return this; }
}

export class ButtonComponent {
    setButtonText(text: string): this { return this; }
    setCta(): this { return this; }
    setWarning(): this { return this; }
    onClick(cb: () => void): this { return this; }
    setDisabled(disabled: boolean): this { return this; }
    buttonEl: HTMLButtonElement = document.createElement('button');
}

export class DropdownComponent {
    addOption(value: string, display: string): this { return this; }
    setValue(value: string): this { return this; }
    onChange(cb: (value: string) => void): this { return this; }
}

export class ExtraButtonComponent {
    extraSettingsEl: HTMLElement = document.createElement('div');
    _icon: string = '';
    _tooltip: string = '';
    _clickHandler: (() => void) | null = null;

    setIcon(icon: string): this { this._icon = icon; return this; }
    setTooltip(tooltip: string): this { this._tooltip = tooltip; return this; }
    onClick(cb: () => void): this { this._clickHandler = cb; return this; }
}

// Mock de TFile et TFolder
export class TFile {
    path: string;
    name: string;
    extension: string;
    stat: { mtime: number; size: number };
    parent: TFolder | null;

    constructor(path: string) {
        this.path = path;
        this.name = path.split('/').pop() || '';
        this.extension = this.name.split('.').pop() || '';
        this.stat = { mtime: Date.now(), size: 100 };
        this.parent = null;
    }
}

export class TFolder {
    path: string;
    name: string;
    children: (TFile | TFolder)[];
    parent: TFolder | null;

    constructor(path: string) {
        this.path = path;
        this.name = path.split('/').pop() || '';
        this.children = [];
        this.parent = null;
    }
}

export abstract class TAbstractFile {
    path: string = '';
    name: string = '';
    parent: TFolder | null = null;
}

// Mock de Vault
export class Vault {
    private files: Map<string, string> = new Map();

    getMarkdownFiles(): TFile[] {
        return [];
    }

    getFiles(): TFile[] {
        return [];
    }

    async read(file: TFile): Promise<string> {
        return this.files.get(file.path) || '';
    }

    async readBinary(file: TFile): Promise<ArrayBuffer> {
        const content = this.files.get(file.path) || '';
        const encoder = new TextEncoder();
        return encoder.encode(content).buffer;
    }

    async modify(file: TFile, content: string): Promise<void> {
        this.files.set(file.path, content);
    }

    async modifyBinary(file: TFile, content: ArrayBuffer): Promise<void> {
        const decoder = new TextDecoder();
        this.files.set(file.path, decoder.decode(content));
    }

    async create(path: string, content: string): Promise<TFile> {
        this.files.set(path, content);
        return new TFile(path);
    }

    async createBinary(path: string, content: ArrayBuffer): Promise<TFile> {
        const decoder = new TextDecoder();
        this.files.set(path, decoder.decode(content));
        return new TFile(path);
    }

    async delete(file: TFile): Promise<void> {
        this.files.delete(file.path);
    }

    async createFolder(path: string): Promise<void> {}

    getAbstractFileByPath(path: string): TAbstractFile | null {
        return null;
    }

    adapter = {
        exists: async (path: string): Promise<boolean> => false
    };
}

// Mock de App
export class App {
    vault: Vault;

    constructor() {
        this.vault = new Vault();
    }
}

// Mock de normalizePath
export function normalizePath(path: string): string {
    return path.replace(/\\/g, '/').replace(/\/+/g, '/');
}

// Mock de arrayBufferToBase64
export function arrayBufferToBase64(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

// Extensions Obsidian pour HTMLElement (createEl, empty)
if (typeof HTMLElement !== 'undefined') {
    if (!(HTMLElement.prototype as any).createEl) {
        (HTMLElement.prototype as any).createEl = function(tag: string, options?: any): HTMLElement {
            const el = document.createElement(tag);
            if (options?.text) el.textContent = options.text;
            if (options?.cls) el.className = options.cls;
            if (options?.attr) {
                for (const [key, value] of Object.entries(options.attr)) {
                    el.setAttribute(key, String(value));
                }
            }
            this.appendChild(el);
            return el;
        };
    }
    if (!(HTMLElement.prototype as any).empty) {
        (HTMLElement.prototype as any).empty = function(): void {
            while (this.firstChild) {
                this.removeChild(this.firstChild);
            }
        };
    }
}
