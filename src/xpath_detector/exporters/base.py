"""Abstract exporter base class."""
from abc import ABC, abstractmethod
from pathlib import Path

from xpath_detector.models import Session


class Exporter(ABC):
    name: str = ""
    extension: str = ""

    @abstractmethod
    def export(self, session: Session, output_dir: Path) -> Path:
        """Genere les fichiers d'export et retourne le chemin du fichier/dossier principal."""
        raise NotImplementedError
