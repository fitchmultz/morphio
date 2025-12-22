import asyncio
import hashlib
import logging
import os
from pathlib import Path
from typing import Set

import aiofiles
from fastapi import UploadFile

from ..config import settings
from ..schemas.file_schema import FileListResult, FileMetadata, FileOperationInput
from ..utils.error_handlers import ApplicationException, handle_application_exception
from ..utils.helpers import sanitize_filename

logger = logging.getLogger(__name__)


async def save_upload_file(upload_file: UploadFile, destination: str) -> str:
    """
    Asynchronously save an uploaded file to the specified destination.

    :param upload_file: The uploaded file object
    :param destination: The directory to save the file in
    :return: The path of the saved file
    :raises ApplicationException: If there's an error saving the file
    """
    try:
        # UploadFile.filename may be None; sanitize expects str
        raw_name = upload_file.filename or "upload"
        filename = sanitize_filename(raw_name)
        file_location = get_unique_filename(destination, filename)

        async with aiofiles.open(file_location, "wb") as buffer:
            while content := await upload_file.read(settings.FILE_CHUNK_SIZE):
                await buffer.write(content)

        logger.info(f"File saved successfully: {file_location}")
        return file_location
    except Exception as e:
        logger.error(f"Error saving uploaded file: {str(e)}")
        raise handle_application_exception(e)


async def delete_file(file_path: str) -> bool:
    """
    Delete a file asynchronously.
    """
    try:
        if not file_path or not os.path.exists(file_path):
            return False
        await asyncio.to_thread(os.remove, file_path)
        return True
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {str(e)}")
        return False


async def is_allowed_file(filename: str, allowed_extensions: Set[str]) -> bool:
    """
    Check if a file has an allowed extension.

    :param filename: The name of the file to check
    :param allowed_extensions: A set of allowed file extensions (without the dot)
    :return: True if the file has an allowed extension, False otherwise
    """
    return (
        "." in filename
        and (await get_file_extension(filename)).lstrip(".").lower() in allowed_extensions
    )


async def get_file_metadata(file_path: str) -> FileMetadata:
    """
    Get metadata of a file.

    :param file_path: The path of the file
    :return: FileMetadata object containing file information
    :raises ApplicationException: If the file doesn't exist or there's an error getting the metadata
    """
    if not await file_exists(file_path):
        raise ApplicationException(f"File not found: {file_path}")

    try:
        file_size = await asyncio.to_thread(os.path.getsize, file_path)
        file_extension = await get_file_extension(file_path)
        return FileMetadata(file_path=file_path, file_size=file_size, file_extension=file_extension)
    except OSError as e:
        logger.error(f"Error getting file metadata for {file_path}: {str(e)}")
        raise handle_application_exception(e)


async def ensure_directory_exists(directory: str) -> None:
    """
    Ensure that the specified directory exists, creating it if necessary.

    :param directory: The directory path to check/create
    """
    await asyncio.to_thread(os.makedirs, directory, exist_ok=True)


async def get_file_extension(filename: str) -> str:
    """
    Get the file extension from a filename.

    :param filename: The name of the file
    :return: The file extension (including the dot)
    """
    return os.path.splitext(filename)[1].lower()


async def file_exists(file_path: str) -> bool:
    """
    Check if a file exists.

    :param file_path: The path of the file to check
    :return: True if the file exists, False otherwise
    """
    return await asyncio.to_thread(os.path.exists, file_path)


async def list_files(directory: str, pattern: str = "*") -> FileListResult:
    """
    List files in a directory that match a given pattern.

    :param directory: The directory to search in
    :param pattern: The pattern to match files against (default is "*" for all files)
    :return: A FileListResult object containing a list of file paths that match the pattern
    """
    import glob

    path_pattern = os.path.join(directory, pattern)
    files: list[str] = await asyncio.to_thread(lambda: glob.glob(path_pattern))
    return FileListResult(files=files)


async def move_file(file_input: FileOperationInput) -> None:
    """
    Move a file from one location to another.

    :param file_input: FileOperationInput object containing source and destination
    :raises ApplicationException: If there's an error moving the file
    """
    try:
        await asyncio.to_thread(os.rename, file_input.file_path, file_input.destination)
        logger.info(
            f"File moved successfully from {file_input.file_path} to {file_input.destination}"
        )
    except OSError as e:
        logger.error(
            f"Error moving file from {file_input.file_path} to {file_input.destination}: {str(e)}"
        )
        raise handle_application_exception(e)


async def compute_file_hash(file_path: str) -> str:
    """
    Compute MD5 hash of a file asynchronously.
    """
    try:
        file_path = str(file_path)  # Ensure file_path is a string
        hash_md5 = hashlib.md5()
        async with aiofiles.open(file_path, "rb") as f:
            chunk_size = 4096
            while True:
                chunk = await f.read(chunk_size)
                if not chunk:
                    break
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"Error computing file hash for {file_path}: {str(e)}")
        raise


def compute_hash(content: str) -> str:
    """
    Compute MD5 hash of a string.
    """
    return hashlib.md5(content.encode()).hexdigest()


def get_unique_filename(directory: str, filename: str) -> str:
    """
    Generate a unique filename in the given directory.
    """
    base_path = Path(directory)
    name, ext = os.path.splitext(filename)
    counter = 1
    new_path = base_path / filename

    while os.path.exists(new_path):
        new_filename = f"{name}_{counter}{ext}"
        new_path = base_path / new_filename
        counter += 1

    return str(new_path)


# Add other file utility functions as needed
