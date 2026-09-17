"""Explicit local/hosted behavior and bounded deployment resource settings."""
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    hosted: bool = False
    max_file_mib: int = 25
    max_workspace_mib: int = 50
    max_codons: int = 100000

    @property
    def max_file_bytes(self):
        return self.max_file_mib * 1024 * 1024

    @property
    def max_workspace_bytes(self):
        return self.max_workspace_mib * 1024 * 1024

    @property
    def max_request_bytes(self):
        # Account for Store JSON escaping plus base64 file transport.
        return (4 * self.max_workspace_mib + 2 * self.max_file_mib + 1) * 1024 * 1024

    @classmethod
    def from_env(cls):
        hosted = os.getenv("SHIFT_HAPPENS_HOSTED", os.getenv("RENDER", "false")).lower() in ("1", "true", "yes")
        def integer(name, default, maximum):
            value = int(os.getenv(name, str(default)))
            if not 1 <= value <= maximum:
                raise ValueError(f"{name} must be between 1 and {maximum}.")
            return value
        files = integer("SHIFT_HAPPENS_MAX_FILE_MIB", 5 if hosted else 25, 25)
        workspace = integer("SHIFT_HAPPENS_MAX_WORKSPACE_MIB", 10 if hosted else 50, 50)
        codons = integer("SHIFT_HAPPENS_MAX_CODONS", 10000 if hosted else 100000, 100000)
        if files > workspace:
            raise ValueError("The file limit cannot exceed the workspace limit.")
        return cls(hosted, files, workspace, codons)
