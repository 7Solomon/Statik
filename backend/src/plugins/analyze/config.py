from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any
import json
import re
from datetime import datetime

@dataclass
class SystemConfig:
    folder_name: str = "systems"
    root_dir: Path = field(default=Path("."), repr=False)

    def __post_init__(self):
        self.base_dir = self.root_dir / self.folder_name
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    @property
    def storage_dir(self) -> Path:
        return self.base_dir / "storage"

    def _slugify(self, text: str) -> str:
        """Helper to create safe filenames from system names."""
        slug = re.sub(r'[^a-z0-9_-]', '-', text.lower().strip())
        return slug or "unnamed-system"

    def save_system(self, name: str, system_data: Dict[str, Any]) -> str:
        """
        Saves a system to JSON.
        Returns the 'slug' (ID) used to save the file.
        """
        slug = self._slugify(name)
        file_path = self.storage_dir / f"{slug}.json"

        payload = {
            "meta": {
                "name": name,
                "slug": slug,
                "saved_at": datetime.now().isoformat()
            },
            "system": system_data
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            
        return slug

    def list_systems(self) -> List[Dict[str, Any]]:
        """
        Returns a list of all saved systems (metadata only).
        """
        results = []
        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "meta" in data:
                        results.append(data["meta"])
            except Exception as e:
                print(f"Skipping corrupt file {file_path}: {e}")
                
        return sorted(results, key=lambda x: x["saved_at"], reverse=True)

    def load_system(self, slug: str) -> Optional[Dict[str, Any]]:
        """
        Loads the full system data for a specific slug.
        """
        file_path = self.storage_dir / f"{slug}.json"
        if not file_path.exists():
            return None
            
        with open(file_path, "r", encoding="utf-8") as f:
            full_data = json.load(f)
            return full_data

    def delete_system(self, slug: str) -> bool:
        """
        Deletes the system file. Returns True if deleted, False if not found.
        """
        file_path = self.storage_dir / f"{slug}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False
