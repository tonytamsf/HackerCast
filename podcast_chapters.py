import json
from pathlib import Path
from typing import List, Dict, Any

def create_chapter_file(chapters: List[Dict[str, Any]], output_path: Path) -> Path:
    """
    Creates a podcast chapter JSON file.

    Args:
        chapters: A list of chapter dictionaries, each with "startTime" and "title".
        output_path: The directory where the chapter file will be saved.

    Returns:
        The path to the created chapter file.
    """
    chapter_data = {
        "version": "1.2.0",
        "chapters": chapters,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chapter_data, f, indent=2)

    return output_path