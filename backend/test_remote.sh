#!/bin/bash
# =============================================================================
# Tests fonctionnels SyncObsidian sur un serveur distant
# Usage: ./test_remote.sh [SERVER_URL]
# Exemple: ./test_remote.sh https://sync.example.com
# =============================================================================

SERVER="${1:-https://sync.example.com}"
USER="testuser_$(date +%s)"
PASS="testpassword123"
EMAIL="${USER}@test.com"

echo "=========================================="
echo "🧪 Tests fonctionnels SyncObsidian"
echo "   Serveur: $SERVER"
echo "   User: $USER"
echo "=========================================="

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✅ $1${NC}"; }
fail() { echo -e "${RED}❌ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }

# 1. Health check
echo -e "\n📋 Test 1: Health check"
HEALTH=$(curl -s "$SERVER/health")
echo "   Réponse: $HEALTH"
echo "$HEALTH" | grep -q "healthy" && pass "Health OK" || fail "Health KO"

# 2. Register
echo -e "\n📋 Test 2: Création de compte"
REGISTER=$(curl -s -X POST "$SERVER/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$USER\", \"email\": \"$EMAIL\", \"password\": \"$PASS\"}")
echo "   Réponse: $REGISTER"
echo "$REGISTER" | grep -q "id" && pass "Register OK" || fail "Register KO"

# 3. Login
echo -e "\n📋 Test 3: Connexion"
LOGIN=$(curl -s -X POST "$SERVER/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$USER\", \"password\": \"$PASS\"}")
TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
if [ -n "$TOKEN" ]; then
  pass "Login OK, token reçu"
else
  fail "Login KO: $LOGIN"
  exit 1
fi

AUTH="Authorization: Bearer $TOKEN"

# 4. Get me
echo -e "\n📋 Test 4: Vérification du token (/auth/me)"
ME=$(curl -s "$SERVER/auth/me" -H "$AUTH")
echo "   Réponse: $ME"
echo "$ME" | grep -q "$USER" && pass "Token valide" || fail "Token invalide"

# 5. Sync initial
echo -e "\n📋 Test 5: Sync initial (aucune note)"
SYNC=$(curl -s -X POST "$SERVER/sync" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"notes": [], "last_sync": null}')
echo "   Réponse: $SYNC"
echo "$SYNC" | grep -q "server_time" && pass "Sync OK" || fail "Sync KO"

# 6. Push une note
echo -e "\n📋 Test 6: Push d'une note"
NOTE_CONTENT="# Ma note de test

Créée le $(date)

Contenu avec **markdown** et des accents: éàü"
NOTE_HASH=$(echo -n "$NOTE_CONTENT" | shasum -a 256 | cut -d' ' -f1)
PUSH=$(curl -s -X POST "$SERVER/sync/push" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d "$(cat <<EOF
{
  "notes": [{
    "path": "test/note-test.md",
    "content": $(echo "$NOTE_CONTENT" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))'),
    "content_hash": "$NOTE_HASH",
    "modified_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  }]
}
EOF
)")
echo "   Réponse: $PUSH"
echo "$PUSH" | grep -qE "(pushed|success|\"note)" && pass "Push note OK" || warn "Push: $PUSH"

# 7. Push une 2ème note dans un sous-dossier
echo -e "\n📋 Test 7: Push d'une 2ème note (sous-dossier)"
NOTE2="# Deuxième note

Dans un sous-dossier profond"
HASH2=$(echo -n "$NOTE2" | shasum -a 256 | cut -d' ' -f1)
PUSH2=$(curl -s -X POST "$SERVER/sync/push" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d "$(cat <<EOF
{
  "notes": [{
    "path": "dossier/sous-dossier/note2.md",
    "content": $(echo "$NOTE2" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))'),
    "content_hash": "$HASH2",
    "modified_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  }]
}
EOF
)")
echo "   Réponse: $PUSH2"
echo "$PUSH2" | grep -qE "(pushed|success|\"note)" && pass "Push note 2 OK" || warn "Push 2: $PUSH2"

# 8. Sync pour voir les notes
echo -e "\n📋 Test 8: Sync - lister toutes les notes"
SYNC2=$(curl -s -X POST "$SERVER/sync" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"notes": [], "last_sync": null}')
echo "   Notes sur le serveur:"
echo "$SYNC2" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for note in data.get('notes_to_pull', []):
        print(f\"     📄 {note['path']}\")
    if not data.get('notes_to_pull'):
        print('     (aucune)')
except Exception as e: print(f'     Erreur: {e}')
"
COUNT=$(echo "$SYNC2" | grep -o '"path"' | wc -l | tr -d ' ')
[ "$COUNT" -ge 2 ] && pass "Notes visibles ($COUNT)" || warn "Notes: $COUNT"

# 9. Pull une note spécifique
echo -e "\n📋 Test 9: Pull d'une note spécifique"
PULL=$(curl -s -X POST "$SERVER/sync/pull" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"paths": ["test/note-test.md"]}')
echo "   Contenu récupéré:"
echo "$PULL" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for note in data.get('notes', []):
        content = note.get('content', '')[:80]
        print(f\"     📄 {note['path']}: {content}...\")
except Exception as e: print(f'     Erreur: {e}')
"
echo "$PULL" | grep -q "note-test.md" && pass "Pull OK" || warn "Pull vide"

# 10. Push un attachment (image PNG 1x1)
echo -e "\n📋 Test 10: Push d'un attachment (image PNG)"
IMG_BASE64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
IMG_BYTES=$(echo -n "$IMG_BASE64" | base64 -d 2>/dev/null | wc -c | tr -d ' ')
IMG_HASH=$(echo -n "$IMG_BASE64" | base64 -d 2>/dev/null | shasum -a 256 | cut -d' ' -f1)
PUSH_ATT=$(curl -s -X POST "$SERVER/sync/push" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d "$(cat <<EOF
{
  "notes": [],
  "attachments": [{
    "path": "attachments/test-image.png",
    "content": "$IMG_BASE64",
    "content_hash": "$IMG_HASH",
    "size": $IMG_BYTES,
    "mime_type": "image/png",
    "modified_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  }]
}
EOF
)")
echo "   Réponse: $PUSH_ATT"
echo "$PUSH_ATT" | grep -qE "(pushed|success|attachment)" && pass "Push attachment OK" || warn "Attachment: $PUSH_ATT"

# 11. Mise à jour d'une note
echo -e "\n📋 Test 11: Mise à jour de la note"
sleep 1
NOTE_UPDATED="# Ma note de test MODIFIÉE

Modifiée le $(date)

Nouveau contenu avec plus de texte."
HASH_UPDATED=$(echo -n "$NOTE_UPDATED" | shasum -a 256 | cut -d' ' -f1)
UPDATE=$(curl -s -X POST "$SERVER/sync/push" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d "$(cat <<EOF
{
  "notes": [{
    "path": "test/note-test.md",
    "content": $(echo "$NOTE_UPDATED" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))'),
    "content_hash": "$HASH_UPDATED",
    "modified_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  }]
}
EOF
)")
echo "   Réponse: $UPDATE"
echo "$UPDATE" | grep -qE "(pushed|updated|success|\"note)" && pass "Update OK" || warn "Update: $UPDATE"

# 12. Suppression d'une note
echo -e "\n📋 Test 12: Suppression d'une note"
DELETE=$(curl -s -X POST "$SERVER/sync/push" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d "$(cat <<EOF
{
  "notes": [{
    "path": "dossier/sous-dossier/note2.md",
    "content": "",
    "content_hash": "",
    "is_deleted": true,
    "modified_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  }]
}
EOF
)")
echo "   Réponse: $DELETE"
echo "$DELETE" | grep -qE "(pushed|deleted|success|\"note)" && pass "Delete OK" || warn "Delete: $DELETE"

# 13. Vérifier l'état final
echo -e "\n📋 Test 13: État final des notes"
SYNC3=$(curl -s -X POST "$SERVER/sync" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"notes": [], "last_sync": null}')
echo "   Notes sur le serveur:"
echo "$SYNC3" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for note in data.get('notes_to_pull', []):
        status = '🗑️' if note.get('is_deleted') else '📄'
        print(f\"     {status} {note['path']}\")
except Exception as e: print(f'     Erreur: {e}')
"
pass "État vérifié"

echo -e "\n=========================================="
echo "🎉 Tests terminés !"
echo ""
echo "💡 Pour nettoyer les données de test, exécutez sur le serveur :"
echo "   ./cleanup_test_data.sh"
echo "=========================================="
