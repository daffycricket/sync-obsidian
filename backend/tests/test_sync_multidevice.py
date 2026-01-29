"""
Tests d'intégration pour la synchronisation multi-device.
Ces tests vérifient que les notes sont correctement synchronisées entre plusieurs appareils.
"""
import pytest
from httpx import AsyncClient
from .conftest import auth_headers


class TestMultiDeviceSync:
    """Tests de synchronisation entre plusieurs devices."""

    @pytest.mark.asyncio
    async def test_sync_unknown_notes_should_always_be_proposed(self, authenticated_client):
        """
        BUG: Les notes que le client n'a JAMAIS eues doivent TOUJOURS être proposées,
        indépendamment de last_sync.

        Scénario:
        1. Device A push des notes sur le serveur à T1
        2. Device B sync avec last_sync=T2 (postérieur à T1) sans mentionner ces notes
        3. Les notes doivent être proposées à B car il ne les a pas (même si non modifiées depuis T2)

        Ce test reproduit le bug où les notes créées par un autre device ne sont jamais
        proposées si elles n'ont pas été modifiées depuis le last_sync du client.
        """
        client, token = authenticated_client

        # T1: "Device A" crée des notes sur le serveur
        note_time = "2026-01-10T10:00:00"
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "device-a-note1.md",
                        "content": "# Note créée par Device A",
                        "content_hash": "hash1",
                        "modified_at": note_time,
                        "is_deleted": False
                    },
                    {
                        "path": "device-a-note2.md",
                        "content": "# Autre note de Device A",
                        "content_hash": "hash2",
                        "modified_at": note_time,
                        "is_deleted": False
                    }
                ]
            }
        )

        # T2: "Device B" sync avec un last_sync POSTÉRIEUR à la création des notes
        # et ne mentionne PAS ces notes (il ne les a jamais eues)
        later_sync_time = "2026-01-11T15:00:00"  # Postérieur à note_time

        response = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": later_sync_time,  # last_sync postérieur à la création
                "notes": [],  # Device B ne mentionne pas les notes (il ne les a pas)
                "attachments": []
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Les notes DOIVENT être proposées au pull car Device B ne les a pas
        # Même si elles n'ont pas été modifiées depuis last_sync
        pulled_paths = [n["path"] for n in data["notes_to_pull"]]

        assert "device-a-note1.md" in pulled_paths, \
            "Notes inconnues du client doivent être proposées même si non modifiées depuis last_sync"
        assert "device-a-note2.md" in pulled_paths, \
            "Notes inconnues du client doivent être proposées même si non modifiées depuis last_sync"

    @pytest.mark.asyncio
    async def test_sync_partial_failure_recovery(self, authenticated_client):
        """
        Scénario de récupération après un sync partiel.

        1. Serveur a 5 notes
        2. Device B sync avec last_sync=None, récupère les 5 notes dans notes_to_pull
        3. Device B ne télécharge que 3 notes (simule un échec partiel)
        4. Device B sync à nouveau avec son last_sync mis à jour
        5. Les 2 notes manquantes doivent être proposées à nouveau
        """
        client, token = authenticated_client

        # Serveur a 5 notes
        notes_time = "2026-01-10T10:00:00"
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {"path": f"note{i}.md", "content": f"# Note {i}", "content_hash": f"h{i}",
                     "modified_at": notes_time, "is_deleted": False}
                    for i in range(1, 6)
                ]
            }
        )

        # Premier sync - récupérer le server_time
        first_sync = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={"last_sync": None, "notes": [], "attachments": []}
        )
        server_time = first_sync.json()["server_time"]

        # Device B a réussi à récupérer seulement 3 notes sur 5
        # Au prochain sync, il mentionne uniquement ces 3 notes
        response = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": server_time,  # last_sync mis à jour
                "notes": [
                    # Device B a seulement note1, note2, note3
                    {"path": "note1.md", "content_hash": "h1", "modified_at": notes_time, "is_deleted": False},
                    {"path": "note2.md", "content_hash": "h2", "modified_at": notes_time, "is_deleted": False},
                    {"path": "note3.md", "content_hash": "h3", "modified_at": notes_time, "is_deleted": False},
                ],
                "attachments": []
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Les notes 4 et 5 doivent être proposées car Device B ne les a pas
        pulled_paths = [n["path"] for n in data["notes_to_pull"]]

        assert "note4.md" in pulled_paths, \
            "Note manquante doit être proposée même après mise à jour de last_sync"
        assert "note5.md" in pulled_paths, \
            "Note manquante doit être proposée même après mise à jour de last_sync"

        # Les notes 1, 2, 3 ne doivent PAS être proposées (déjà présentes, même hash)
        assert "note1.md" not in pulled_paths
        assert "note2.md" not in pulled_paths
        assert "note3.md" not in pulled_paths

    @pytest.mark.asyncio
    async def test_sync_new_device_gets_all_notes(self, authenticated_client):
        """
        Un nouveau device (last_sync=None) doit recevoir toutes les notes.
        C'est le comportement attendu et déjà fonctionnel - ce test sert de référence.
        """
        client, token = authenticated_client

        # Créer des notes sur le serveur
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {"path": "existing1.md", "content": "# Note 1", "content_hash": "h1",
                     "modified_at": "2026-01-10T10:00:00", "is_deleted": False},
                    {"path": "existing2.md", "content": "# Note 2", "content_hash": "h2",
                     "modified_at": "2026-01-10T10:00:00", "is_deleted": False}
                ]
            }
        )

        # Nouveau device sync avec last_sync=None
        response = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": None,  # Nouveau device
                "notes": [],
                "attachments": []
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Toutes les notes doivent être proposées
        pulled_paths = [n["path"] for n in data["notes_to_pull"]]
        assert "existing1.md" in pulled_paths
        assert "existing2.md" in pulled_paths
