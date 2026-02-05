# Spécification : Système de Refresh Tokens

**Statut :** En attente d'implémentation
**Ticket :** s2 - Priorité P2 (MOYENNE)

---

## 1. Contexte et objectifs

### Problème

L'architecture actuelle utilise un token unique de **24 heures** (`config.py:13`). Si un token est volé (interception réseau, malware, fuite), l'attaquant dispose d'une fenêtre d'exploitation de 24h pour :
- Accéder aux notes de l'utilisateur
- Modifier/supprimer des données
- Se faire passer pour l'utilisateur

### Objectif du ticket s2

> Passer l'expiration des tokens de 24h à 1-2h pour limiter l'exposition en cas de vol.

### Problème UX de la solution brute

Réduire simplement l'expiration à 1-2h obligerait les utilisateurs à se reconnecter manuellement plusieurs fois par jour → **UX inacceptable**.

### Solution retenue

Implémenter un **système dual-token** (access token + refresh token) permettant :
- Access token court (15 min) → limite l'exposition
- Refresh token long (7 jours) → maintient la session sans reconnexion
- Renouvellement automatique côté client → UX transparente

---

## 2. Architecture actuelle

```
┌─────────────┐     POST /auth/login      ┌─────────────┐
│   Client    │ ───────────────────────►  │   Backend   │
│  (Plugin)   │ ◄─────────────────────────│   FastAPI   │
└─────────────┘   access_token (24h)      └─────────────┘
                                                 │
                                                 ▼
                                          ┌─────────────┐
                                          │   SQLite    │
                                          │   (users)   │
                                          └─────────────┘
```

### Fichiers concernés

| Fichier | Rôle actuel |
|---------|-------------|
| `backend/app/core/config.py` | `access_token_expire_minutes: 1440` (24h) |
| `backend/app/core/security.py` | `create_access_token()`, `decode_token()` |
| `backend/app/routers/auth.py` | `/login` retourne `{access_token, token_type}` |
| `backend/app/schemas.py` | `Token`, `TokenData` |

### Limitations

- **Token unique** : pas de séparation access/refresh
- **Pas de renouvellement** : expiration = reconnexion manuelle
- **Pas de révocation** : impossible d'invalider un token avant expiration (ticket s10)

---

## 3. Architecture cible

```
┌─────────────┐     POST /auth/login      ┌─────────────┐
│   Client    │ ───────────────────────►  │   Backend   │
│  (Plugin)   │ ◄─────────────────────────│   FastAPI   │
└─────────────┘   access_token (15min)    └─────────────┘
       │          refresh_token (7 jours)        │
       │                                         │
       │          POST /auth/refresh             │
       │ ───────────────────────────────────────►│
       │ ◄───────────────────────────────────────│
       │          new access_token (15min)       │
       └─────────────────────────────────────────┘
```

### Spécifications des tokens

| Token | Durée | Claims | Stockage client | Usage |
|-------|-------|--------|-----------------|-------|
| **Access Token** | 15 min | `sub`, `username`, `type: "access"`, `exp` | Mémoire | Authentification API |
| **Refresh Token** | 7 jours | `sub`, `jti` (UUID unique), `type: "refresh"`, `exp` | localStorage/settings | Renouvellement |

### Pourquoi ces durées ?

| Durée | Justification |
|-------|---------------|
| Access: 15 min | Compromis sécurité/performance. Limite l'exposition sans trop de refresh |
| Refresh: 7 jours | Session "longue" typique. L'utilisateur occasionnel se reconnecte 1x/semaine max |

---

## 4. Flux d'authentification

### 4.1 Login initial

```
Client                                    Server
   │                                         │
   │  POST /auth/login                       │
   │  {username, password}                   │
   │ ───────────────────────────────────────►│
   │                                         │ Vérifie credentials
   │                                         │ Génère access_token (15min)
   │                                         │ Génère refresh_token (7j)
   │  {                                      │
   │    access_token: "eyJ...",              │
   │    refresh_token: "eyJ...",             │
   │    token_type: "bearer",                │
   │    expires_in: 900                      │
   │  }                                      │
   │ ◄───────────────────────────────────────│
   │                                         │
```

### 4.2 Appel API normal

```
Client                                    Server
   │                                         │
   │  GET /sync/notes                        │
   │  Authorization: Bearer <access_token>   │
   │ ───────────────────────────────────────►│
   │                                         │ Vérifie access_token
   │  200 OK                                 │ Token valide → réponse
   │  {notes: [...]}                         │
   │ ◄───────────────────────────────────────│
   │                                         │
```

### 4.3 Access token expiré → Refresh automatique

```
Client                                    Server
   │                                         │
   │  GET /sync/notes                        │
   │  Authorization: Bearer <access_token>   │
   │ ───────────────────────────────────────►│
   │                                         │ Access token expiré
   │  401 Unauthorized                       │
   │ ◄───────────────────────────────────────│
   │                                         │
   │  POST /auth/refresh                     │
   │  {refresh_token: "eyJ..."}              │
   │ ───────────────────────────────────────►│
   │                                         │ Vérifie refresh_token
   │  {                                      │ Génère nouveau access_token
   │    access_token: "eyJ...(new)",         │
   │    expires_in: 900                      │
   │  }                                      │
   │ ◄───────────────────────────────────────│
   │                                         │
   │  GET /sync/notes (retry)                │
   │  Authorization: Bearer <new_access>     │
   │ ───────────────────────────────────────►│
   │                                         │
   │  200 OK                                 │
   │ ◄───────────────────────────────────────│
```

### 4.4 Refresh token expiré → Reconnexion

```
Client                                    Server
   │                                         │
   │  POST /auth/refresh                     │
   │  {refresh_token: "eyJ...(expired)"}     │
   │ ───────────────────────────────────────►│
   │                                         │ Refresh token expiré
   │  401 Unauthorized                       │
   │  {detail: "Refresh token expired"}      │
   │ ◄───────────────────────────────────────│
   │                                         │
   │  → Afficher écran de connexion          │
   │                                         │
```

---

## 5. Modifications Backend

### 5.1 Configuration (`config.py`)

**Avant :**
```python
access_token_expire_minutes: int = 1440  # 24 heures
```

**Après :**
```python
# JWT - Access Token
access_token_expire_minutes: int = 15  # 15 minutes

# JWT - Refresh Token
refresh_token_expire_days: int = 7  # 7 jours
```

---

### 5.2 Schemas (`schemas.py`)

**Ajouts :**
```python
class TokenResponse(BaseModel):
    """Réponse de login avec les deux tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Secondes avant expiration de l'access token


class RefreshRequest(BaseModel):
    """Requête de renouvellement de token."""
    refresh_token: str


class RefreshResponse(BaseModel):
    """Réponse de refresh - nouveau access token uniquement."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
```

**Modification de TokenData :**
```python
class TokenData(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None
    token_type: Optional[str] = None  # "access" ou "refresh"
    jti: Optional[str] = None  # Unique ID pour refresh tokens
```

---

### 5.3 Sécurité (`security.py`)

**Ajouts :**
```python
import uuid

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Créer un access token JWT."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({
        "exp": expire,
        "type": "access"  # Nouveau: identifier le type de token
    })
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(user_id: int) -> str:
    """Créer un refresh token JWT avec un identifiant unique."""
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    to_encode = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": str(uuid.uuid4()),  # Unique ID pour révocation future
        "exp": expire
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_refresh_token(token: str) -> Optional[TokenData]:
    """Décoder et valider un refresh token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        # Vérifier que c'est bien un refresh token
        if payload.get("type") != "refresh":
            return None

        user_id_str = payload.get("sub")
        if user_id_str is None:
            return None

        return TokenData(
            user_id=int(user_id_str),
            token_type="refresh",
            jti=payload.get("jti")
        )
    except JWTError:
        return None
```

**Modification de decode_token :**
```python
def decode_token(token: str) -> Optional[TokenData]:
    """Décoder et valider un access token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        # Vérifier que c'est bien un access token (ou ancien token sans type)
        token_type = payload.get("type")
        if token_type is not None and token_type != "access":
            return None  # Rejeter les refresh tokens utilisés comme access

        user_id_str = payload.get("sub")
        username: str = payload.get("username")
        if user_id_str is None:
            return None
        return TokenData(user_id=int(user_id_str), username=username, token_type="access")
    except JWTError:
        return None
```

---

### 5.4 Router Auth (`auth.py`)

**Modification de /login :**
```python
from ..schemas import UserCreate, UserLogin, TokenResponse, UserResponse, RefreshRequest, RefreshResponse

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authentifier un utilisateur et retourner access + refresh tokens."""
    user = await authenticate_user(db, credentials.username, credentials.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Créer les deux tokens
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username}
    )
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60  # En secondes
    )
```

**Ajout de /refresh :**
```python
@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """Renouveler un access token à partir d'un refresh token valide."""
    token_data = decode_refresh_token(request.refresh_token)

    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Vérifier que l'utilisateur existe toujours et est actif
    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur non trouvé"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur désactivé"
        )

    # Créer un nouveau access token
    new_access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username}
    )

    return RefreshResponse(
        access_token=new_access_token,
        expires_in=settings.access_token_expire_minutes * 60
    )
```

---

## 6. Modifications Client (Plugin Obsidian)

### 6.1 Stockage des tokens (`settings.ts`)

```typescript
interface SyncObsidianSettings {
    serverUrl: string;
    username: string;
    password: string;  // À supprimer après migration vers tokens
    accessToken: string;
    refreshToken: string;
    tokenExpiresAt: number;  // Timestamp d'expiration
}
```

### 6.2 Intercepteur de requêtes (`api.ts`)

```typescript
class ApiClient {
    private async request(endpoint: string, options: RequestInit): Promise<Response> {
        // Ajouter le token d'accès
        const headers = {
            ...options.headers,
            'Authorization': `Bearer ${this.settings.accessToken}`
        };

        let response = await fetch(`${this.settings.serverUrl}${endpoint}`, {
            ...options,
            headers
        });

        // Si 401 et qu'on a un refresh token, tenter le refresh
        if (response.status === 401 && this.settings.refreshToken) {
            const refreshed = await this.refreshAccessToken();
            if (refreshed) {
                // Retry avec le nouveau token
                headers['Authorization'] = `Bearer ${this.settings.accessToken}`;
                response = await fetch(`${this.settings.serverUrl}${endpoint}`, {
                    ...options,
                    headers
                });
            }
        }

        return response;
    }

    private async refreshAccessToken(): Promise<boolean> {
        try {
            const response = await fetch(`${this.settings.serverUrl}/auth/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: this.settings.refreshToken })
            });

            if (response.ok) {
                const data = await response.json();
                this.settings.accessToken = data.access_token;
                this.settings.tokenExpiresAt = Date.now() + (data.expires_in * 1000);
                await this.saveSettings();
                return true;
            }

            // Refresh token invalide → déconnexion
            await this.logout();
            return false;
        } catch (error) {
            return false;
        }
    }
}
```

---

## 7. Rate Limiting

Le endpoint `/auth/refresh` doit être protégé par rate limiting (déjà en place via Caddy).

**Recommandation :** Ajouter une règle spécifique dans le Caddyfile :

```caddyfile
# /auth/refresh - 10 requêtes/minute (refresh normal)
@refresh {
    path /auth/refresh
}
rate_limit @refresh {
    zone refresh {
        key    {remote_host}
        events 10
        window 1m
    }
}
```

---

## 8. Tests de validation

### 8.1 Tests unitaires Backend

```python
# tests/test_auth_refresh.py

import pytest
from datetime import timedelta
from freezegun import freeze_time

class TestRefreshTokens:

    async def test_login_returns_both_tokens(self, client, test_user):
        """POST /login retourne access_token ET refresh_token."""
        response = await client.post("/auth/login", json={
            "username": test_user.username,
            "password": "testpassword"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "expires_in" in data
        assert data["token_type"] == "bearer"

    async def test_access_token_expires_in_15_minutes(self, client, test_user):
        """Access token expire après 15 minutes."""
        # Login
        response = await client.post("/auth/login", json={
            "username": test_user.username,
            "password": "testpassword"
        })
        access_token = response.json()["access_token"]

        # Appel immédiat → OK
        response = await client.get("/auth/me", headers={
            "Authorization": f"Bearer {access_token}"
        })
        assert response.status_code == 200

        # Après 16 minutes → 401
        with freeze_time(timedelta(minutes=16)):
            response = await client.get("/auth/me", headers={
                "Authorization": f"Bearer {access_token}"
            })
            assert response.status_code == 401

    async def test_refresh_endpoint_returns_new_access_token(self, client, test_user):
        """POST /refresh avec refresh_token valide → nouveau access_token."""
        # Login
        login_response = await client.post("/auth/login", json={
            "username": test_user.username,
            "password": "testpassword"
        })
        refresh_token = login_response.json()["refresh_token"]

        # Refresh
        response = await client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "expires_in" in data
        assert "refresh_token" not in data  # On ne renvoie pas un nouveau refresh

    async def test_refresh_with_expired_token_returns_401(self, client, test_user):
        """POST /refresh avec refresh_token expiré → 401."""
        login_response = await client.post("/auth/login", json={
            "username": test_user.username,
            "password": "testpassword"
        })
        refresh_token = login_response.json()["refresh_token"]

        # Après 8 jours
        with freeze_time(timedelta(days=8)):
            response = await client.post("/auth/refresh", json={
                "refresh_token": refresh_token
            })
            assert response.status_code == 401

    async def test_refresh_with_invalid_token_returns_401(self, client):
        """POST /refresh avec token invalide → 401."""
        response = await client.post("/auth/refresh", json={
            "refresh_token": "invalid.token.here"
        })
        assert response.status_code == 401

    async def test_access_token_cannot_refresh(self, client, test_user):
        """POST /refresh avec access_token → 401 (wrong token type)."""
        login_response = await client.post("/auth/login", json={
            "username": test_user.username,
            "password": "testpassword"
        })
        access_token = login_response.json()["access_token"]

        # Tenter d'utiliser l'access token pour refresh
        response = await client.post("/auth/refresh", json={
            "refresh_token": access_token  # Wrong token type!
        })
        assert response.status_code == 401

    async def test_refresh_preserves_user_context(self, client, test_user):
        """Le nouveau access_token identifie le même utilisateur."""
        # Login
        login_response = await client.post("/auth/login", json={
            "username": test_user.username,
            "password": "testpassword"
        })
        refresh_token = login_response.json()["refresh_token"]

        # Refresh
        refresh_response = await client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })
        new_access_token = refresh_response.json()["access_token"]

        # Vérifier que /me retourne le même utilisateur
        response = await client.get("/auth/me", headers={
            "Authorization": f"Bearer {new_access_token}"
        })
        assert response.status_code == 200
        assert response.json()["username"] == test_user.username

    async def test_refresh_fails_for_inactive_user(self, client, test_user, db):
        """Refresh échoue si l'utilisateur a été désactivé."""
        # Login
        login_response = await client.post("/auth/login", json={
            "username": test_user.username,
            "password": "testpassword"
        })
        refresh_token = login_response.json()["refresh_token"]

        # Désactiver l'utilisateur
        test_user.is_active = False
        await db.commit()

        # Refresh → 401
        response = await client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert response.status_code == 401
```

### 8.2 Tests d'intégration

```python
class TestRefreshFlow:

    async def test_full_auth_cycle(self, client, test_user):
        """Login → API call → token expire → refresh → API call OK."""
        # 1. Login
        login_response = await client.post("/auth/login", json={
            "username": test_user.username,
            "password": "testpassword"
        })
        tokens = login_response.json()

        # 2. Appel API avec access token
        response = await client.get("/sync/notes", headers={
            "Authorization": f"Bearer {tokens['access_token']}"
        })
        assert response.status_code == 200

        # 3. Simuler expiration de l'access token
        with freeze_time(timedelta(minutes=20)):
            # Access token expiré
            response = await client.get("/sync/notes", headers={
                "Authorization": f"Bearer {tokens['access_token']}"
            })
            assert response.status_code == 401

            # 4. Refresh
            refresh_response = await client.post("/auth/refresh", json={
                "refresh_token": tokens['refresh_token']
            })
            assert refresh_response.status_code == 200
            new_token = refresh_response.json()["access_token"]

            # 5. Nouvel appel API avec nouveau token
            response = await client.get("/sync/notes", headers={
                "Authorization": f"Bearer {new_token}"
            })
            assert response.status_code == 200
```

### 8.3 Tests de non-régression

| Test | Description |
|------|-------------|
| `test_old_tokens_without_type_still_work` | Période de transition : anciens tokens (24h) acceptés |
| `test_register_unchanged` | L'inscription ne change pas |
| `test_protected_endpoints_require_auth` | Les endpoints protégés requièrent toujours un token |

### 8.4 Tests manuels Client

| Scénario | Étapes | Résultat attendu |
|----------|--------|------------------|
| Refresh automatique | 1. Login 2. Attendre 16+ min 3. Sync | Sync réussit (refresh silencieux) |
| Session longue | Utiliser pendant 7 jours | Reconnexion demandée au 8ème jour |
| Désactivation compte | 1. Login 2. Admin désactive le compte 3. Sync | Erreur + déconnexion |

---

## 9. Plan de déploiement

### Phase 1 : Backend (sans breaking change)

1. Déployer les modifications backend avec **rétrocompatibilité** :
   - `/login` retourne les deux tokens
   - Les anciens tokens (sans `type`) restent acceptés
   - `/refresh` endpoint disponible

2. Tester en production avec un client de test

### Phase 2 : Client

1. Mettre à jour le plugin Obsidian
2. Publier une nouvelle version avec changelog explicite
3. Communiquer aux utilisateurs la nécessité de mettre à jour

### Phase 3 : Fin de transition

1. Après X semaines, désactiver la rétrocompatibilité
2. Forcer l'expiration des anciens tokens 24h

---

## 10. Métriques de succès

| Métrique | Avant | Après | Amélioration |
|----------|-------|-------|--------------|
| Fenêtre d'exploitation token volé | 24h | 15 min | **-96%** |
| Reconnexions manuelles/jour (utilisateur actif) | 0 | 0 | Neutre |
| Reconnexions manuelles/semaine (utilisateur occasionnel) | 0 | 1 | Acceptable |

---

## 11. Évolutions futures (hors scope)

| Ticket | Description | Lien avec s2 |
|--------|-------------|--------------|
| **s10** | Blacklist de tokens (révocation) | Permettrait d'invalider un refresh token compromis |
| - | Rotation des refresh tokens | Chaque refresh génère un nouveau refresh token |
| - | Détection d'anomalies | Alerter si refresh depuis IP/device inhabituel |

---

## 12. Risques et mitigations

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Vol du refresh token | Faible | Élevé | Implémenter s10 (révocation), rotation |
| Client non mis à jour | Moyenne | Moyen | Période de transition, communication |
| Bug dans le refresh | Faible | Élevé | Tests exhaustifs, rollback possible |
| Surcharge refresh endpoint | Faible | Faible | Rate limiting déjà en place |

---

## 13. Checklist d'implémentation

### Backend
- [ ] Modifier `config.py` : ajouter `refresh_token_expire_days`
- [ ] Modifier `schemas.py` : `TokenResponse`, `RefreshRequest`, `RefreshResponse`
- [ ] Modifier `security.py` : `create_refresh_token()`, `decode_refresh_token()`
- [ ] Modifier `auth.py` : `/login` retourne les deux tokens
- [ ] Ajouter `auth.py` : endpoint `/refresh`
- [ ] Ajouter tests `test_auth_refresh.py`
- [ ] Mettre à jour rate limiting Caddy pour `/auth/refresh`

### Client
- [ ] Modifier `settings.ts` : stocker `refreshToken`
- [ ] Modifier `api.ts` : intercepteur 401 → refresh automatique
- [ ] Tester le flux complet manuellement

### Documentation
- [ ] Mettre à jour le README avec le nouveau flux
- [ ] Documenter l'API `/auth/refresh` dans OpenAPI

---

## 14. Références

- [RFC 6749 - OAuth 2.0](https://datatracker.ietf.org/doc/html/rfc6749) (inspiration pour le pattern access/refresh)
- [JWT Best Practices](https://auth0.com/blog/jwt-security-best-practices/)
- [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)

---

*Spécification créée le 5 février 2026*
