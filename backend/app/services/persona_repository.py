from pathlib import Path
import yaml


class PersonaRepository:
    def __init__(self, data_root: Path | None = None) -> None:
        self.data_root = data_root or (
            Path(__file__).resolve().parents[3] / "data" / "emperors"
        )

    def list_emperors(self) -> list[dict]:
        results: list[dict] = []
        if not self.data_root.exists():
            return results

        for folder in sorted(self.data_root.iterdir()):
            if not folder.is_dir():
                continue
            manifest = self._load_yaml(folder / "manifest.yaml")
            if manifest:
                results.append(manifest)
        return results

    def get_manifest(self, emperor_id: str) -> dict | None:
        return self._load_yaml(
            self.data_root / emperor_id / "manifest.yaml"
        )

    def get_persona_package(self, emperor_id: str) -> dict | None:
        folder = self.data_root / emperor_id
        if not folder.exists():
            return None

        package: dict = {}
        for file in sorted(folder.glob("*.yaml")):
            package[file.stem] = self._load_yaml(file)
        return package

    @staticmethod
    def _load_yaml(path: Path) -> dict | None:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)
