#!/bin/bash
# =============================================================================
# Nettoyage des données de test SyncObsidian
# À exécuter sur le serveur pour supprimer les users/notes/attachments de test
# 
# Usage: ./cleanup_test_data.sh [--dry-run] [--all]
#   --dry-run : Affiche ce qui serait supprimé sans supprimer
#   --all     : Supprime TOUS les utilisateurs (pas seulement testuser_*)
# =============================================================================

set -e

# Chemins (ajuster si nécessaire)
DB_PATH="${DB_PATH:-./data/syncobsidian.db}"
STORAGE_PATH="${STORAGE_PATH:-./data/storage}"

# Si on est dans un environnement Docker, utiliser les chemins du volume
if [ -f "/app/data/syncobsidian.db" ]; then
    DB_PATH="/app/data/syncobsidian.db"
    STORAGE_PATH="/app/data/storage"
fi

# Options
DRY_RUN=false
DELETE_ALL=false

for arg in "$@"; do
    case $arg in
        --dry-run) DRY_RUN=true ;;
        --all) DELETE_ALL=true ;;
    esac
done

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo "=========================================="
echo "🧹 Nettoyage des données de test"
echo "   Base de données: $DB_PATH"
echo "   Stockage: $STORAGE_PATH"
if $DRY_RUN; then
    echo -e "   Mode: ${YELLOW}DRY-RUN (simulation)${NC}"
fi
if $DELETE_ALL; then
    echo -e "   ${RED}⚠️  SUPPRESSION DE TOUS LES UTILISATEURS${NC}"
fi
echo "=========================================="

# Vérifier que sqlite3 est disponible
if ! command -v sqlite3 &> /dev/null; then
    echo -e "${RED}❌ sqlite3 non trouvé. Installez-le avec: apt install sqlite3${NC}"
    exit 1
fi

# Vérifier que la base existe
if [ ! -f "$DB_PATH" ]; then
    echo -e "${RED}❌ Base de données non trouvée: $DB_PATH${NC}"
    exit 1
fi

# Construire la condition WHERE
if $DELETE_ALL; then
    WHERE_CLAUSE="1=1"
    echo -e "\n${RED}⚠️  ATTENTION: Tous les utilisateurs seront supprimés !${NC}"
    if ! $DRY_RUN; then
        read -p "Êtes-vous sûr ? (tapez 'oui' pour confirmer) " confirm
        if [ "$confirm" != "oui" ]; then
            echo "Annulé."
            exit 0
        fi
    fi
else
    WHERE_CLAUSE="username LIKE 'testuser_%'"
fi

# Lister les utilisateurs à supprimer
echo -e "\n📋 Utilisateurs à supprimer:"
USERS=$(sqlite3 "$DB_PATH" "SELECT id, username, email FROM users WHERE $WHERE_CLAUSE;")
if [ -z "$USERS" ]; then
    echo "   (aucun utilisateur trouvé)"
    exit 0
fi

echo "$USERS" | while IFS='|' read -r id username email; do
    echo "   🗑️  [$id] $username ($email)"
done

# Compter les notes et attachments
echo -e "\n📋 Données associées:"
USER_IDS=$(sqlite3 "$DB_PATH" "SELECT id FROM users WHERE $WHERE_CLAUSE;")
for uid in $USER_IDS; do
    username=$(sqlite3 "$DB_PATH" "SELECT username FROM users WHERE id=$uid;")
    notes_count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM notes WHERE user_id=$uid;")
    att_count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM attachments WHERE user_id=$uid;")
    echo "   👤 $username: $notes_count notes, $att_count attachments"
    
    # Vérifier le dossier de stockage
    if [ -d "$STORAGE_PATH/$uid" ]; then
        size=$(du -sh "$STORAGE_PATH/$uid" 2>/dev/null | cut -f1)
        echo "      📁 Dossier: $STORAGE_PATH/$uid ($size)"
    fi
done

# Exécuter la suppression
if $DRY_RUN; then
    echo -e "\n${YELLOW}🔍 Mode DRY-RUN: aucune suppression effectuée${NC}"
    echo "   Relancez sans --dry-run pour supprimer réellement."
else
    echo -e "\n🗑️  Suppression en cours..."
    
    for uid in $USER_IDS; do
        username=$(sqlite3 "$DB_PATH" "SELECT username FROM users WHERE id=$uid;")
        
        # Supprimer les fichiers
        if [ -d "$STORAGE_PATH/$uid" ]; then
            rm -rf "$STORAGE_PATH/$uid"
            echo -e "   ${GREEN}✅ Dossier supprimé: $STORAGE_PATH/$uid${NC}"
        fi
        
        # Supprimer en base (CASCADE supprime notes et attachments)
        sqlite3 "$DB_PATH" "DELETE FROM users WHERE id=$uid;"
        echo -e "   ${GREEN}✅ Utilisateur supprimé: $username (id=$uid)${NC}"
    done
    
    echo -e "\n${GREEN}✅ Nettoyage terminé !${NC}"
fi

# Afficher l'état final
echo -e "\n📊 État de la base après nettoyage:"
echo "   Utilisateurs: $(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM users;")"
echo "   Notes: $(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM notes;")"
echo "   Attachments: $(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM attachments;")"
