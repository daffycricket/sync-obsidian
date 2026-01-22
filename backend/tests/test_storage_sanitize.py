"""
Tests unitaires pour la fonction sanitize_path.
"""
import pytest
from app.storage import sanitize_path


class TestSanitizePath:
    """Tests unitaires de la fonction sanitize_path."""
    
    def test_valid_simple_path(self):
        """Chemin simple valide."""
        assert sanitize_path("note.md") == "note.md"
    
    def test_valid_nested_path(self):
        """Chemin imbriqué valide."""
        assert sanitize_path("dossier/note.md") == "dossier/note.md"
        assert sanitize_path("dossier/sous-dossier/note.md") == "dossier/sous-dossier/note.md"
    
    def test_valid_path_with_spaces(self):
        """Chemin avec espaces."""
        assert sanitize_path("note avec espaces.md") == "note avec espaces.md"
    
    def test_valid_path_with_special_chars(self):
        """Chemin avec caractères spéciaux."""
        assert sanitize_path("note-avec-tirets.md") == "note-avec-tirets.md"
        assert sanitize_path("note_avec_underscores.md") == "note_avec_underscores.md"
        assert sanitize_path("Noté Accentuée.md") == "Noté Accentuée.md"
    
    def test_path_traversal_single_dot_dot(self):
        """Chemin avec .. doit être rejeté."""
        with pytest.raises(ValueError, match="ne sont pas autorisés"):
            sanitize_path("../note.md")
    
    def test_path_traversal_multiple_dot_dot(self):
        """Chemin avec plusieurs .. doit être rejeté."""
        with pytest.raises(ValueError, match="ne sont pas autorisés"):
            sanitize_path("../../../etc/passwd")
    
    def test_path_traversal_mixed(self):
        """Chemin avec .. mélangé doit être rejeté."""
        with pytest.raises(ValueError, match="ne sont pas autorisés"):
            sanitize_path("notes/../../etc/passwd")
    
    def test_absolute_path_unix(self):
        """Chemin absolu Unix doit être rejeté."""
        # Un chemin qui commence par / est rejeté avant même de vérifier s'il est absolu
        with pytest.raises(ValueError):
            sanitize_path("/etc/passwd")
    
    def test_absolute_path_windows(self):
        """Chemin absolu Windows doit être rejeté."""
        # Sur macOS/Linux, os.path.isabs ne détecte pas les chemins Windows
        # Mais notre vérification du ':' devrait le capturer
        with pytest.raises(ValueError, match="absolus ne sont pas autorisés"):
            sanitize_path("C:\\Windows\\System32")
    
    def test_path_starting_with_slash(self):
        """Chemin commençant par / doit être rejeté."""
        with pytest.raises(ValueError):
            sanitize_path("/relative/path.md")
    
    def test_path_starting_with_backslash(self):
        """Chemin commençant par \\ doit être rejeté."""
        with pytest.raises(ValueError, match="ne peut pas commencer par"):
            sanitize_path("\\relative\\path.md")
    
    def test_empty_path(self):
        """Chemin vide doit être rejeté."""
        with pytest.raises(ValueError, match="ne peut pas être vide"):
            sanitize_path("")
    
    def test_whitespace_only_path(self):
        """Chemin avec seulement des espaces doit être rejeté."""
        with pytest.raises(ValueError, match="ne peut pas être vide"):
            sanitize_path("   ")
    
    def test_path_within_depth_limit(self):
        """Chemin avec exactement 30 niveaux doit être accepté."""
        # 29 dossiers + 1 fichier = 30 parties au total
        path = "/".join([f"folder{i}" for i in range(29)]) + "/note.md"
        result = sanitize_path(path)
        assert result == path
    
    def test_path_exceeding_depth_limit(self):
        """Chemin avec plus de 30 niveaux doit être rejeté."""
        path = "/".join([f"folder{i}" for i in range(31)]) + "/note.md"
        with pytest.raises(ValueError, match="trop profond"):
            sanitize_path(path)
    
    def test_normalized_path_removes_dot(self):
        """Le chemin avec . doit être normalisé."""
        assert sanitize_path("./note.md") == "note.md"
        assert sanitize_path("dossier/./note.md") == "dossier/note.md"
    
    def test_normalized_path_removes_redundant_separators(self):
        """Les séparateurs redondants doivent être normalisés."""
        assert sanitize_path("dossier//note.md") == "dossier/note.md"
    
    def test_path_with_dot_in_filename(self):
        """Un point dans le nom de fichier est valide."""
        assert sanitize_path("file.name.md") == "file.name.md"
        assert sanitize_path("dossier/file.name.md") == "dossier/file.name.md"
