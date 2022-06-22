from dataclasses import dataclass
@dataclass
class DirEntry:
    path: str
    is_dir: bool
