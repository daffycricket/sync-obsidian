#!/bin/bash
# Script pour lancer les tests d'intégration

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}  Tests d'intégration SyncObsidian${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# Vérifier si le venv existe
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Création du virtual environment...${NC}"
    python3 -m venv venv
fi

# Activer le venv
source venv/bin/activate

# Installer les dépendances de test
echo -e "${YELLOW}Installation des dépendances de test...${NC}"
pip install -q -r requirements-test.txt

# Nettoyer les données de test précédentes
rm -rf test_data 2>/dev/null || true

# Lancer les tests
echo ""
echo -e "${YELLOW}Lancement des tests...${NC}"
echo ""

if [ "$1" == "-v" ] || [ "$1" == "--verbose" ]; then
    pytest -v --tb=long "$@"
elif [ "$1" == "-x" ] || [ "$1" == "--exitfirst" ]; then
    pytest -x "$@"
elif [ -n "$1" ]; then
    # Si un argument est passé, l'utiliser comme pattern
    pytest -v -k "$1"
else
    pytest
fi

EXIT_CODE=$?

# Nettoyer
rm -rf test_data 2>/dev/null || true

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  ✅ Tous les tests sont passés !${NC}"
    echo -e "${GREEN}========================================${NC}"
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}  ❌ Certains tests ont échoué${NC}"
    echo -e "${RED}========================================${NC}"
fi

exit $EXIT_CODE
