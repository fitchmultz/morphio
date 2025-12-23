"""
Main CLI application for morphio-core.

Commands:
- transcribe: Transcribe audio files using local Whisper
- validate-url: Validate URLs for SSRF protection
- info: Show system information and available backends
"""

from enum import Enum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="morphio",
    help="morphio-core CLI utilities for audio transcription and URL validation.",
    no_args_is_help=True,
)
console = Console()


class WhisperBackend(str, Enum):
    """Available Whisper transcription backends."""

    auto = "auto"
    mlx = "mlx"
    faster_whisper = "faster-whisper"


@app.command()
def transcribe(
    audio_file: Annotated[Path, typer.Argument(help="Path to audio file")],
    model: Annotated[str, typer.Option(help="Whisper model size")] = "base",
    language: Annotated[str | None, typer.Option(help="Language code (e.g., en)")] = None,
    word_timestamps: Annotated[bool, typer.Option(help="Include word-level timestamps")] = False,
    output: Annotated[
        Path | None, typer.Option("-o", "--output", help="Output file (JSON)")
    ] = None,
    backend: Annotated[
        WhisperBackend, typer.Option(help="Whisper backend", case_sensitive=False)
    ] = WhisperBackend.auto,
) -> None:
    """Transcribe an audio file using local Whisper."""
    from morphio_core.audio import TranscriptionConfig, transcribe_audio
    from morphio_core.exceptions import TranscriptionError

    if not audio_file.is_file():
        if not audio_file.exists():
            console.print(f"[red]Error:[/red] File not found: {audio_file}")
        else:
            console.print(f"[red]Error:[/red] Path is not a file: {audio_file}")
        raise typer.Exit(1)

    config = TranscriptionConfig(
        model=model,
        language=language,
        word_timestamps=word_timestamps,
        backend=backend.value,
    )

    console.print(f"Transcribing [cyan]{audio_file}[/cyan]...")
    console.print(f"Model: {model}, Backend: {backend.value}")

    try:
        result = transcribe_audio(audio_file, config=config)
    except TranscriptionError as e:
        console.print(f"[red]Transcription failed:[/red] {e}")
        raise typer.Exit(1) from e

    console.print("\n[green]Transcription complete![/green]")
    console.print(f"Backend: {result.backend_used} ({result.device_used})")
    console.print(f"Language: {result.language or 'auto-detected'}")
    console.print(f"Duration: {result.duration:.1f}s" if result.duration else "")
    console.print()

    if output:
        import json

        output_data = {
            "text": result.text,
            "language": result.language,
            "duration": result.duration,
            "backend": result.backend_used,
            "device": result.device_used,
            "segments": [
                {
                    "id": s.id,
                    "text": s.text,
                    "start": s.start_time,
                    "end": s.end_time,
                }
                for s in result.segments
            ],
        }
        if word_timestamps and result.words:
            output_data["words"] = [
                {
                    "word": w.word,
                    "start": w.start_time,
                    "end": w.end_time,
                    "confidence": w.confidence,
                }
                for w in result.words
            ]
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(output_data, indent=2))
        console.print(f"Output saved to: {output}")
    else:
        console.print("[bold]Transcript:[/bold]")
        console.print(result.text)


@app.command("validate-url")
def validate_url(
    url: Annotated[str, typer.Argument(help="URL to validate")],
    allow_private: Annotated[bool, typer.Option(help="Allow private IP addresses")] = False,
) -> None:
    """Validate a URL for SSRF protection."""
    from morphio_core.security import SSRFBlockedError, URLValidator, URLValidatorConfig

    config = URLValidatorConfig(allow_private_ips=allow_private)
    validator = URLValidator(config)

    try:
        validator.validate(url)
        console.print(f"[green]URL is valid:[/green] {url}")
    except SSRFBlockedError as e:
        console.print(f"[red]URL blocked:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def info() -> None:
    """Show system information and available backends."""
    from morphio_core.audio.transcription import (
        has_faster_whisper,
        has_mlx_whisper,
        has_nvidia_gpu,
        is_apple_silicon,
    )

    table = Table(title="morphio-core System Info")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")

    # Platform info
    import platform
    import sys

    table.add_row(
        "Python", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    table.add_row("Platform", f"{platform.system()} {platform.machine()}")
    table.add_row("Apple Silicon", "[green]Yes[/green]" if is_apple_silicon() else "[dim]No[/dim]")
    table.add_row("NVIDIA GPU", "[green]Yes[/green]" if has_nvidia_gpu() else "[dim]No[/dim]")

    # Whisper backends
    table.add_section()
    table.add_row(
        "MLX Whisper",
        "[green]Installed[/green]" if has_mlx_whisper() else "[dim]Not installed[/dim]",
    )
    table.add_row(
        "Faster Whisper",
        "[green]Installed[/green]" if has_faster_whisper() else "[dim]Not installed[/dim]",
    )

    # Optional dependencies
    table.add_section()

    def check_import(module: str) -> str:
        import importlib.util

        return (
            "[green]Installed[/green]"
            if importlib.util.find_spec(module)
            else "[dim]Not installed[/dim]"
        )

    table.add_row("OpenAI SDK", check_import("openai"))
    table.add_row("Anthropic SDK", check_import("anthropic"))
    table.add_row("Google GenAI", check_import("google.genai"))
    table.add_row("yt-dlp", check_import("yt_dlp"))

    # FFmpeg
    import shutil

    table.add_section()
    table.add_row(
        "FFmpeg",
        "[green]Installed[/green]" if shutil.which("ffmpeg") else "[dim]Not installed[/dim]",
    )
    table.add_row(
        "ffprobe",
        "[green]Installed[/green]" if shutil.which("ffprobe") else "[dim]Not installed[/dim]",
    )

    console.print(table)


if __name__ == "__main__":
    app()
