import json
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
import re

class SystemManager:
    """Handles reading/writing system JSON files in system_templates"""
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _create_slug(self, name: str) -> str:
        """Sanitize name to create a safe filename"""
        # Lowercase, replace spaces with dashes, remove non-alphanumeric
        slug = name.lower().strip().replace(' ', '-')
        slug = re.sub(r'[^a-z0-9\-]', '', slug)
        return slug

    def save_system(self, name: str, system_data: dict) -> str:
        slug = self._create_slug(name)
        file_path = self.storage_dir / f"{slug}.json"
        
        # We wrap the data with metadata
        file_content = {
            "meta": {
                "name": name,
                "slug": slug,
                "saved_at": datetime.now().isoformat()
            },
            "system": system_data
        }

        with open(file_path, 'w') as f:
            json.dump(file_content, f, indent=2)
            
        return slug

    def list_systems(self) -> list:
        systems = []
        # glob looks for all .json files
        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    # Safely get metadata, fallback if file structure is old
                    meta = data.get("meta", {})
                    if meta:
                        systems.append(meta)
            except (json.JSONDecodeError, IOError):
                continue # Skip broken files
        
        # Sort by most recently saved
        return sorted(systems, key=lambda x: x.get('saved_at', ''), reverse=True)

    def load_system(self, slug: str) -> dict:
        file_path = self.storage_dir / f"{slug}.json"
        if not file_path.exists():
            return None
            
        with open(file_path, 'r') as f:
            data = json.load(f)
            # Return just the system data (or the whole object if you prefer)
            return data.get("system")

    def delete_system(self, slug: str) -> bool:
        file_path = self.storage_dir / f"{slug}.json"
        if not file_path.exists():
            return False
        file_path.unlink() # Delete file
        return True
