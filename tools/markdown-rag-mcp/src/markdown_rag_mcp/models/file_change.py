from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class FileChangeInfo(BaseModel):
    """Information about a detected file change."""

    file_path: Path = Field(..., description="Path to the changed file")
    change_type: str = Field(..., description="Type of change: 'created', 'modified', 'deleted'")
    old_hash: str | None = Field(None, description="Previous content hash")
    new_hash: str | None = Field(None, description="New content hash")
    old_modified_time: datetime | None = Field(None, description="Previous modification time")
    new_modified_time: datetime | None = Field(None, description="New modification time")

    def __str__(self) -> str:
        return f"FileChangeInfo({self.change_type}: {self.file_path})"

    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)
