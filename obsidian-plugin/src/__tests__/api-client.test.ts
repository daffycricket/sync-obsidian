import { ApiClient } from '../api-client';
import { requestUrl } from 'obsidian';

// Mock requestUrl
const mockRequestUrl = requestUrl as jest.MockedFunction<typeof requestUrl>;

// Helper to create mock response with required fields
const mockResponse = (status: number, json: any, text: string = '{}') => ({
    status,
    text,
    json,
    headers: {},
    arrayBuffer: new ArrayBuffer(0)
});

describe('ApiClient', () => {
    let client: ApiClient;
    const serverUrl = 'https://api.example.com';

    beforeEach(() => {
        client = new ApiClient(serverUrl);
        mockRequestUrl.mockReset();
    });

    describe('constructor', () => {
        it('should remove trailing slash from server URL', () => {
            const clientWithSlash = new ApiClient('https://api.example.com/');
            // On vérifie indirectement via un appel
            mockRequestUrl.mockResolvedValueOnce(mockResponse(200, { status: 'ok' }, 'ok'));
            clientWithSlash.checkHealth();
            expect(mockRequestUrl).toHaveBeenCalledWith(
                expect.objectContaining({
                    url: 'https://api.example.com/health'
                })
            );
        });
    });

    describe('setAccessToken', () => {
        it('should set token used in subsequent requests', async () => {
            client.setAccessToken('test-token');
            mockRequestUrl.mockResolvedValueOnce(mockResponse(200, { notes: [] }));

            await client.getSyncedNotes();

            expect(mockRequestUrl).toHaveBeenCalledWith(
                expect.objectContaining({
                    headers: expect.objectContaining({
                        Authorization: 'Bearer test-token'
                    })
                })
            );
        });
    });

    describe('setServerUrl', () => {
        it('should update server URL and remove trailing slash', async () => {
            client.setServerUrl('https://new-api.example.com/');
            mockRequestUrl.mockResolvedValueOnce(mockResponse(200, { status: 'ok' }, 'ok'));

            await client.checkHealth();

            expect(mockRequestUrl).toHaveBeenCalledWith(
                expect.objectContaining({
                    url: 'https://new-api.example.com/health'
                })
            );
        });
    });

    describe('request (private, tested via public methods)', () => {
        it('should add Content-Type header', async () => {
            mockRequestUrl.mockResolvedValueOnce(mockResponse(200, {}));

            await client.checkHealth();

            expect(mockRequestUrl).toHaveBeenCalledWith(
                expect.objectContaining({
                    headers: expect.objectContaining({
                        'Content-Type': 'application/json'
                    })
                })
            );
        });

        it('should add Authorization header when token is set', async () => {
            client.setAccessToken('my-token');
            mockRequestUrl.mockResolvedValueOnce(mockResponse(200, {}));

            await client.checkHealth();

            expect(mockRequestUrl).toHaveBeenCalledWith(
                expect.objectContaining({
                    headers: expect.objectContaining({
                        Authorization: 'Bearer my-token'
                    })
                })
            );
        });

        it('should not add Authorization header when no token', async () => {
            mockRequestUrl.mockResolvedValueOnce(mockResponse(200, {}));

            await client.checkHealth();

            const callArg = mockRequestUrl.mock.calls[0][0];
            if (typeof callArg !== 'string') {
                expect(callArg.headers?.Authorization).toBeUndefined();
            }
        });

        it('should throw error on 401 status', async () => {
            mockRequestUrl.mockResolvedValueOnce(mockResponse(401, { detail: 'Not authenticated' }, 'Unauthorized'));

            await expect(client.getSyncedNotes()).rejects.toThrow('API Error: 401');
        });

        it('should throw error on 403 status', async () => {
            mockRequestUrl.mockResolvedValueOnce(mockResponse(403, { detail: 'Forbidden' }, 'Forbidden'));

            await expect(client.getSyncedNotes()).rejects.toThrow('API Error: 403');
        });

        it('should throw error on 500 status', async () => {
            mockRequestUrl.mockResolvedValueOnce(mockResponse(500, { detail: 'Server error' }, 'Internal Server Error'));

            await expect(client.getSyncedNotes()).rejects.toThrow('API Error: 500');
        });

        it('should propagate network errors', async () => {
            mockRequestUrl.mockRejectedValueOnce(new Error('Network error'));

            await expect(client.checkHealth()).resolves.toBe(false);
        });
    });

    describe('login', () => {
        it('should return token on successful login', async () => {
            mockRequestUrl.mockResolvedValueOnce(mockResponse(200, { access_token: 'new-token', token_type: 'bearer' }));

            const result = await client.login('user', 'pass');

            expect(result).toEqual({ access_token: 'new-token', token_type: 'bearer' });
            expect(mockRequestUrl).toHaveBeenCalledWith(
                expect.objectContaining({
                    url: `${serverUrl}/auth/login`,
                    method: 'POST',
                    body: JSON.stringify({ username: 'user', password: 'pass' })
                })
            );
        });

        it('should throw on invalid credentials', async () => {
            mockRequestUrl.mockResolvedValueOnce(mockResponse(401, { detail: 'Invalid credentials' }, 'Invalid credentials'));

            await expect(client.login('user', 'wrong')).rejects.toThrow('API Error: 401');
        });
    });

    describe('register', () => {
        it('should send registration request', async () => {
            mockRequestUrl.mockResolvedValueOnce(mockResponse(200, { id: 1, username: 'newuser' }));

            const result = await client.register('newuser', 'email@test.com', 'password');

            expect(mockRequestUrl).toHaveBeenCalledWith(
                expect.objectContaining({
                    url: `${serverUrl}/auth/register`,
                    method: 'POST',
                    body: JSON.stringify({
                        username: 'newuser',
                        email: 'email@test.com',
                        password: 'password'
                    })
                })
            );
        });

        it('should throw on duplicate username', async () => {
            mockRequestUrl.mockResolvedValueOnce(mockResponse(400, { detail: 'Username already exists' }, 'Username already exists'));

            await expect(client.register('existing', 'email@test.com', 'pass'))
                .rejects.toThrow('API Error: 400');
        });
    });

    describe('checkHealth', () => {
        it('should return true when server is healthy', async () => {
            mockRequestUrl.mockResolvedValueOnce(mockResponse(200, { status: 'ok' }, 'ok'));

            const result = await client.checkHealth();

            expect(result).toBe(true);
            expect(mockRequestUrl).toHaveBeenCalledWith(
                expect.objectContaining({
                    url: `${serverUrl}/health`,
                    method: 'GET'
                })
            );
        });

        it('should return false when server is down', async () => {
            mockRequestUrl.mockRejectedValueOnce(new Error('Connection refused'));

            const result = await client.checkHealth();

            expect(result).toBe(false);
        });

        it('should return false on server error', async () => {
            mockRequestUrl.mockResolvedValueOnce(mockResponse(500, {}, 'Error'));

            const result = await client.checkHealth();

            expect(result).toBe(false);
        });
    });

    describe('sync', () => {
        it('should send sync request with correct payload', async () => {
            const syncRequest = {
                last_sync: '2024-01-01T00:00:00Z',
                notes: [{ path: 'test.md', content_hash: 'abc', modified_at: '2024-01-01T00:00:00Z', is_deleted: false }],
                attachments: []
            };
            mockRequestUrl.mockResolvedValueOnce(mockResponse(200, {
                server_time: '2024-01-01T00:00:00Z',
                notes_to_pull: [],
                notes_to_push: [],
                conflicts: [],
                attachments_to_pull: [],
                attachments_to_push: []
            }));

            await client.sync(syncRequest);

            expect(mockRequestUrl).toHaveBeenCalledWith(
                expect.objectContaining({
                    url: `${serverUrl}/sync`,
                    method: 'POST',
                    body: JSON.stringify(syncRequest)
                })
            );
        });
    });

    describe('pushNotes', () => {
        it('should send notes to push', async () => {
            const request = {
                notes: [{
                    path: 'test.md',
                    content: '# Test',
                    content_hash: 'abc',
                    modified_at: '2024-01-01T00:00:00Z',
                    is_deleted: false
                }]
            };
            mockRequestUrl.mockResolvedValueOnce(mockResponse(200, { success: ['test.md'], failed: [] }));

            const result = await client.pushNotes(request);

            expect(result).toEqual({ success: ['test.md'], failed: [] });
            expect(mockRequestUrl).toHaveBeenCalledWith(
                expect.objectContaining({
                    url: `${serverUrl}/sync/push`,
                    method: 'POST'
                })
            );
        });
    });

    describe('pullNotes', () => {
        it('should request notes by paths', async () => {
            const request = { paths: ['note1.md', 'note2.md'] };
            mockRequestUrl.mockResolvedValueOnce(mockResponse(200, {
                notes: [
                    { path: 'note1.md', content: '# Note 1', content_hash: 'a', modified_at: '2024-01-01T00:00:00Z', is_deleted: false },
                    { path: 'note2.md', content: '# Note 2', content_hash: 'b', modified_at: '2024-01-01T00:00:00Z', is_deleted: false }
                ]
            }));

            const result = await client.pullNotes(request);

            expect(result.notes).toHaveLength(2);
            expect(mockRequestUrl).toHaveBeenCalledWith(
                expect.objectContaining({
                    url: `${serverUrl}/sync/pull`,
                    method: 'POST',
                    body: JSON.stringify(request)
                })
            );
        });
    });

    describe('pushAttachments', () => {
        it('should send attachments to push', async () => {
            const request = {
                attachments: [{
                    path: 'image.png',
                    content_base64: 'base64data',
                    content_hash: 'abc',
                    size: 1024,
                    mime_type: 'image/png',
                    modified_at: '2024-01-01T00:00:00Z',
                    is_deleted: false
                }]
            };
            mockRequestUrl.mockResolvedValueOnce(mockResponse(200, { success: ['image.png'], failed: [] }));

            const result = await client.pushAttachments(request);

            expect(result).toEqual({ success: ['image.png'], failed: [] });
            expect(mockRequestUrl).toHaveBeenCalledWith(
                expect.objectContaining({
                    url: `${serverUrl}/sync/attachments/push`,
                    method: 'POST'
                })
            );
        });
    });

    describe('pullAttachments', () => {
        it('should request attachments by paths', async () => {
            const request = { paths: ['image.png'] };
            mockRequestUrl.mockResolvedValueOnce(mockResponse(200, {
                attachments: [{
                    path: 'image.png',
                    content_base64: 'base64data',
                    content_hash: 'abc',
                    size: 1024,
                    mime_type: 'image/png',
                    modified_at: '2024-01-01T00:00:00Z',
                    is_deleted: false
                }]
            }));

            const result = await client.pullAttachments(request);

            expect(result.attachments).toHaveLength(1);
            expect(mockRequestUrl).toHaveBeenCalledWith(
                expect.objectContaining({
                    url: `${serverUrl}/sync/attachments/pull`,
                    method: 'POST'
                })
            );
        });
    });

    describe('getSyncedNotes', () => {
        it('should fetch synced notes without params', async () => {
            mockRequestUrl.mockResolvedValueOnce(mockResponse(200, {
                total_count: 10,
                page: 1,
                page_size: 50,
                total_pages: 1,
                notes: [],
                attachments: []
            }));

            await client.getSyncedNotes();

            expect(mockRequestUrl).toHaveBeenCalledWith(
                expect.objectContaining({
                    url: `${serverUrl}/sync/notes`,
                    method: 'GET'
                })
            );
        });

        it('should add query params when provided', async () => {
            mockRequestUrl.mockResolvedValueOnce(mockResponse(200, { total_count: 0, page: 2, page_size: 10, total_pages: 0, notes: [], attachments: [] }));

            await client.getSyncedNotes({
                page: 2,
                page_size: 10,
                include_deleted: true,
                path_filter: 'folder/'
            });

            expect(mockRequestUrl).toHaveBeenCalledWith(
                expect.objectContaining({
                    url: expect.stringContaining('page=2')
                })
            );
            expect(mockRequestUrl).toHaveBeenCalledWith(
                expect.objectContaining({
                    url: expect.stringContaining('page_size=10')
                })
            );
            expect(mockRequestUrl).toHaveBeenCalledWith(
                expect.objectContaining({
                    url: expect.stringContaining('include_deleted=true')
                })
            );
            expect(mockRequestUrl).toHaveBeenCalledWith(
                expect.objectContaining({
                    url: expect.stringContaining('path_filter=folder')
                })
            );
        });
    });

    describe('compare', () => {
        it('should send compare request', async () => {
            const request = {
                notes: [{ path: 'test.md', content_hash: 'abc', modified_at: '2024-01-01T00:00:00Z' }]
            };
            mockRequestUrl.mockResolvedValueOnce(mockResponse(200, {
                server_time: '2024-01-01T00:00:00Z',
                summary: { total_client: 1, total_server: 1, to_push: 0, to_pull: 0, conflicts: 0, identical: 1, deleted_on_server: 0 },
                to_push: [],
                to_pull: [],
                conflicts: [],
                deleted_on_server: []
            }));

            const result = await client.compare(request);

            expect(result.summary.identical).toBe(1);
            expect(mockRequestUrl).toHaveBeenCalledWith(
                expect.objectContaining({
                    url: `${serverUrl}/sync/compare`,
                    method: 'POST'
                })
            );
        });
    });
});
