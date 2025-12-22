from typing import List

from pydantic import BaseModel, ConfigDict, Field


class FileOperationInput(BaseModel):
    file_path: str = Field(..., description="Path to the file")
    destination: str = Field(..., description="Destination directory")

    model_config = ConfigDict(extra="forbid")


class FileMetadata(BaseModel):
    file_path: str = Field(..., description="Path to the file")
    file_size: int = Field(..., description="Size of the file in bytes")
    file_extension: str = Field(..., description="Extension of the file")

    model_config = ConfigDict(extra="forbid")


class FileListResult(BaseModel):
    files: List[str] = Field(..., description="List of file paths")

    model_config = ConfigDict(extra="forbid")
