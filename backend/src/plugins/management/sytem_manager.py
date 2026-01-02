import json
import re
import unicodedata
import os
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemManager:
    """Handles reading/writing system JSON files in system_templates"""
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir.resolve() # Use absolute path
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"SystemManager initialized at: {self.storage_dir}")
        except PermissionError:
            logger.error(f"PERMISSION DENIED: Cannot create directory {self.storage_dir}")

    def _create_slug(self, name: str) -> str:
        """Sanitize name to create a safe, ASCII-only filename (handles umlauts)"""
        if not name:
            return "untitled"
            
        # Normalize unicode characters (e.g. 'Müller' -> 'Muller', 'Träger' -> 'Trager')
        name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('utf-8')
        
        # Lowercase, replace spaces with dashes, remove non-alphanumeric
        slug = name.lower().strip().replace(' ', '-')
        slug = re.sub(r'[^a-z0-9\-]', '', slug)
        
        # Fallback if slug becomes empty
        return slug if slug else "system"

    def save_system(self, name: str, system_data: dict) -> str:
        slug = self._create_slug(name)
        file_path = self.storage_dir / f"{slug}.json"
        
        # Metadata wrapper
        file_content = {
            "meta": {
                "name": name,
                "slug": slug,
                "saved_at": datetime.now().isoformat()
            },
            "system": system_data
        }

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(file_content, f, indent=2)
            logger.info(f"Saved system '{name}' to {file_path}")
            return slug
        except IOError as e:
            logger.error(f"Failed to save system {slug}: {e}")
            raise

    def list_systems(self) -> list:
        systems = []
        if not self.storage_dir.exists():
            logger.warning(f"Storage dir {self.storage_dir} does not exist during listing.")
            return []

        # glob looks for all .json files
        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    meta = data.get("meta", {})
                    # If meta is missing slug, fallback to filename
                    if not meta.get("slug"):
                        meta["slug"] = file_path.stem
                    systems.append(meta)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Skipping broken file {file_path}: {e}")
                continue 
        
        # Sort by most recently saved (descending)
        return sorted(systems, key=lambda x: x.get('saved_at', ''), reverse=True)

    def load_system(self, slug: str) -> dict:
        """Loads a system by slug. Tries exact match first, then case-insensitive lookup."""
        target_filename = f"{slug}.json"
        file_path = self.storage_dir / target_filename

        # Try exact match
        if file_path.exists():
            return self._read_file(file_path)

        # Try case-insensitive fallback
        logger.info(f"Exact match for '{target_filename}' not found. Searching case-insensitive...")
        for existing_file in self.storage_dir.glob("*.json"):
            if existing_file.name.lower() == target_filename.lower():
                logger.info(f"Found case-insensitive match: {existing_file.name}")
                return self._read_file(existing_file)

        logger.warning(f"System '{slug}' not found in {self.storage_dir}")
        return None

    def _read_file(self, path: Path) -> dict:
        """Helper to safely read and parse the file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("system")
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            return None

    def delete_system(self, slug: str) -> bool:
        file_path = self.storage_dir / f"{slug}.json"
        if not file_path.exists():
            return False
        try:
            file_path.unlink()
            logger.info(f"Deleted system: {slug}")
            return True
        except IOError as e:
            logger.error(f"Failed to delete {slug}: {e}")
            return False
