import { requestUrl, RequestUrlParam } from "obsidian";
import {
    Token,
    SyncRequest,
    SyncResponse,
    PushNotesRequest,
    PushNotesResponse,
    PullNotesRequest,
    PullNotesResponse,
    PushAttachmentsRequest,
    PushAttachmentsResponse,
    PullAttachmentsRequest,
    PullAttachmentsResponse,
    SyncedNotesResponse,
    SyncedNotesParams,
    CompareRequest,
    CompareResponse,
} from "./types";

export class ApiClient {
    private serverUrl: string;
    private accessToken: string | null;

    constructor(serverUrl: string, accessToken: string | null = null) {
        this.serverUrl = serverUrl.replace(/\/$/, ""); // Enlever le slash final
        this.accessToken = accessToken;
    }

    setAccessToken(token: string | null) {
        this.accessToken = token;
    }

    setServerUrl(url: string) {
        this.serverUrl = url.replace(/\/$/, "");
    }

    private async request<T>(
        endpoint: string,
        method: string = "GET",
        body?: any
    ): Promise<T> {
        const params: RequestUrlParam = {
            url: `${this.serverUrl}${endpoint}`,
            method: method,
            headers: {
                "Content-Type": "application/json",
            },
        };

        if (this.accessToken) {
            params.headers = {
                ...params.headers,
                Authorization: `Bearer ${this.accessToken}`,
            };
        }

        if (body) {
            params.body = JSON.stringify(body);
        }

        const response = await requestUrl(params);

        if (response.status >= 400) {
            throw new Error(
                `API Error: ${response.status} - ${response.text}`
            );
        }

        return response.json as T;
    }

    // Auth endpoints
    async login(username: string, password: string): Promise<Token> {
        return this.request<Token>("/auth/login", "POST", {
            username,
            password,
        });
    }

    async register(
        username: string,
        email: string,
        password: string
    ): Promise<any> {
        return this.request("/auth/register", "POST", {
            username,
            email,
            password,
        });
    }

    async checkHealth(): Promise<boolean> {
        try {
            await this.request("/health");
            return true;
        } catch {
            return false;
        }
    }

    // Sync endpoints
    async sync(request: SyncRequest): Promise<SyncResponse> {
        return this.request<SyncResponse>("/sync", "POST", request);
    }

    async pushNotes(request: PushNotesRequest): Promise<PushNotesResponse> {
        return this.request<PushNotesResponse>("/sync/push", "POST", request);
    }

    async pullNotes(request: PullNotesRequest): Promise<PullNotesResponse> {
        return this.request<PullNotesResponse>("/sync/pull", "POST", request);
    }

    // Attachments endpoints
    async pushAttachments(request: PushAttachmentsRequest): Promise<PushAttachmentsResponse> {
        return this.request<PushAttachmentsResponse>("/sync/attachments/push", "POST", request);
    }

    async pullAttachments(request: PullAttachmentsRequest): Promise<PullAttachmentsResponse> {
        return this.request<PullAttachmentsResponse>("/sync/attachments/pull", "POST", request);
    }

    // GET /sync/notes - Visualisation des notes synchronisées
    async getSyncedNotes(params: SyncedNotesParams = {}): Promise<SyncedNotesResponse> {
        const queryParams = new URLSearchParams();
        if (params.page) queryParams.set("page", String(params.page));
        if (params.page_size) queryParams.set("page_size", String(params.page_size));
        if (params.include_deleted) queryParams.set("include_deleted", "true");
        if (params.path_filter) queryParams.set("path_filter", params.path_filter);

        const query = queryParams.toString();
        const endpoint = query ? `/sync/notes?${query}` : "/sync/notes";

        return this.request<SyncedNotesResponse>(endpoint, "GET");
    }

    // POST /sync/compare - Comparaison client/serveur
    async compare(request: CompareRequest): Promise<CompareResponse> {
        return this.request<CompareResponse>("/sync/compare", "POST", request);
    }
}
