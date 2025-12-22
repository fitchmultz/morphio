import json
import os
import platform
import time
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import torch

# Filter out specific warnings
warnings.filterwarnings("ignore", category=UserWarning, module="whisper")
warnings.filterwarnings("ignore", category=FutureWarning, module="whisper")

# Patch torch.load to always use weights_only=True
original_torch_load = torch.load
setattr(
    torch, "load", lambda *args, **kwargs: original_torch_load(*args, **kwargs, weights_only=True)
)


class WhisperBenchmark:
    def __init__(self, audio_path: str, model_name: str = "tiny"):
        self.audio_path = audio_path
        self.model_name = model_name
        self.results: List[Dict] = []
        self.system_info = self._get_system_info()

    def _get_system_info(self) -> Dict:
        """Get detailed system information"""
        return {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "cuda_available": (torch.cuda.is_available() if hasattr(torch, "cuda") else False),
            "cuda_device": (
                torch.cuda.get_device_name(0)
                if hasattr(torch, "cuda") and torch.cuda.is_available()
                else None
            ),
            "mps_available": hasattr(torch.backends, "mps") and torch.backends.mps.is_available(),
        }

    def _time_execution(self, func) -> Tuple[str, float, bool]:
        """Execute function and measure time"""
        try:
            print("  ⏳ Loading model and processing...", end="", flush=True)
            start = time.perf_counter()
            result = func()
            duration = time.perf_counter() - start
            print(f"\r  ✓ Completed in {duration:.2f}s" + " " * 20)
            return result, duration, True
        except Exception as e:
            print(f"\r  ✗ Failed: {str(e)}" + " " * 20)
            return str(e), 0.0, False

    def test_openai_whisper_cpu(self) -> None:
        """Test standard OpenAI Whisper on CPU"""
        print("\nTesting OpenAI Whisper (CPU):")

        def run():
            import whisper

            model = whisper.load_model(self.model_name).cpu()
            return model.transcribe(self.audio_path)["text"]

        result, duration, success = self._time_execution(run)
        self.results.append(
            {
                "name": "OpenAI Whisper (CPU)",
                "duration": duration,
                "success": success,
                "transcription_preview": (
                    result[:100] if success else f"Error with OpenAI Whisper: {result}"
                ),
            }
        )

    def test_openai_whisper_cuda(self) -> None:
        """Test standard OpenAI Whisper on CUDA"""
        if not self.system_info["cuda_available"]:
            return
        print("\nTesting OpenAI Whisper (CUDA):")

        def run():
            import whisper

            model = whisper.load_model(self.model_name).cuda()
            return model.transcribe(self.audio_path)["text"]

        result, duration, success = self._time_execution(run)
        self.results.append(
            {
                "name": "OpenAI Whisper (CUDA)",
                "duration": duration,
                "success": success,
                "transcription_preview": (
                    result[:100] if success else f"Error with OpenAI Whisper CUDA: {result}"
                ),
            }
        )

    def test_lightning_whisper_mlx(self) -> None:
        """Test Lightning Whisper MLX (Apple Silicon)"""
        if not self.system_info["platform"].startswith("macOS"):
            return
        print("\nTesting Lightning Whisper MLX:")

        def run():
            try:
                from lightning_whisper_mlx import LightningWhisperMLX  # type: ignore[import-not-found]
            except ImportError as e:
                raise RuntimeError("lightning_whisper_mlx not installed") from e

            model = LightningWhisperMLX(model=self.model_name)
            return model.transcribe(self.audio_path)["text"]

        result, duration, success = self._time_execution(run)
        self.results.append(
            {
                "name": "Lightning Whisper MLX",
                "duration": duration,
                "success": success,
                "transcription_preview": (
                    result[:100] if success else f"Error with Lightning Whisper MLX: {result}"
                ),
            }
        )

    def test_mlx_whisper(self) -> None:
        """Test MLX Whisper (Apple Silicon)"""
        if not self.system_info["platform"].startswith("macOS"):
            return
        print("\nTesting MLX Whisper:")

        def run():
            import mlx_whisper

            # Use transcribe directly with the model name
            result = mlx_whisper.transcribe(
                self.audio_path,
                path_or_hf_repo=f"mlx-community/whisper-{self.model_name}-mlx",
            )
            return result["text"]

        result, duration, success = self._time_execution(run)
        self.results.append(
            {
                "name": "MLX Whisper",
                "duration": duration,
                "success": success,
                "transcription_preview": (
                    result[:100] if success else f"Error with MLX Whisper: {result}"
                ),
            }
        )

    def verify_dependencies(self) -> Dict[str, Dict[str, bool]]:
        """Verify that required packages are installed correctly and check model cache"""
        dependencies = {
            "openai-whisper": {"installed": False, "model_cached": False},
            "lightning-whisper-mlx": {"installed": False, "model_cached": False},
            "mlx-whisper": {"installed": False, "model_cached": False},
        }

        # Check OpenAI Whisper
        try:
            pass

            dependencies["openai-whisper"]["installed"] = True
            cache_dir = os.path.expanduser("~/.cache/whisper")
            model_path = os.path.join(cache_dir, f"{self.model_name}.pt")
            dependencies["openai-whisper"]["model_cached"] = os.path.exists(model_path)
        except ImportError:
            pass

        # Check Lightning Whisper MLX
        try:
            pass

            dependencies["lightning-whisper-mlx"]["installed"] = True
            # Lightning Whisper MLX downloads to a temp directory first
            # We'll consider it not cached since we can't reliably check
            dependencies["lightning-whisper-mlx"]["model_cached"] = False
        except ImportError:
            pass

        # Check MLX Whisper
        try:
            pass

            dependencies["mlx-whisper"]["installed"] = True
            cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
            model_name = f"models--mlx-community--whisper-{self.model_name}-mlx"
            model_path = os.path.join(cache_dir, model_name)
            # Check if model directory exists and has blobs (actual model files)
            has_blobs = (
                (
                    os.path.exists(os.path.join(model_path, "blobs"))
                    and len(os.listdir(os.path.join(model_path, "blobs"))) > 0
                )
                if os.path.exists(model_path)
                else False
            )
            dependencies["mlx-whisper"]["model_cached"] = has_blobs
        except ImportError:
            pass

        return dependencies

    def run_benchmarks(self) -> None:
        """Run all applicable benchmarks"""
        print(f"\n🚀 Running Whisper benchmarks for '{self.model_name}' model...")
        print(f"💻 System: {self.system_info['platform']}")

        # Verify dependencies first
        deps = self.verify_dependencies()
        print("\n📦 Dependency Status:")
        for dep, status in deps.items():
            cached_status = "📥" if status["model_cached"] else "⬇️"
            print(f"  {'✓' if status['installed'] else '✗'} {dep} {cached_status}")

        if not any(d["installed"] for d in deps.values()):
            print("\n❌ No Whisper implementations available. Please install required packages.")
            return

        print("\n🏃 Starting benchmarks...")
        print("Note: ⬇️ indicates model will be downloaded, 📥 indicates model is cached")

        # Run tests based on available hardware and dependencies
        if deps["openai-whisper"]["installed"]:
            self.test_openai_whisper_cpu()
            self.test_openai_whisper_cuda()

        if deps["lightning-whisper-mlx"]["installed"] and self.system_info["platform"].startswith(
            "macOS"
        ):
            self.test_lightning_whisper_mlx()

        if deps["mlx-whisper"]["installed"] and self.system_info["platform"].startswith("macOS"):
            self.test_mlx_whisper()

    def save_results(self) -> None:
        """Save benchmark results to JSON"""
        results = {
            "system_info": self.system_info,
            "test_timestamp": datetime.now().isoformat(),
            "audio_path": self.audio_path,
            "model_name": self.model_name,
            "results": self.results,
        }

        output_dir = Path("benchmark_results")
        output_dir.mkdir(exist_ok=True)
        output_file = (
            output_dir / f"whisper_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"\n💾 Results saved to {output_file}")
        self._print_summary()

    def _print_summary(self) -> None:
        """Print human-readable summary of results"""
        print("\n📊 Benchmark Summary:")
        print("-" * 50)
        for result in self.results:
            status = "✓" if result["success"] else "✗"
            duration = f"{result['duration']:.2f}s" if result["success"] else "Failed"
            print(f"{status} {result['name']}: {duration}")

    def _debug_cache_locations(self) -> None:
        """Debug helper to print cache locations and contents"""
        print("\n🔍 Checking cache locations:")

        # Check OpenAI Whisper cache
        whisper_cache = os.path.expanduser("~/.cache/whisper")
        print(f"\nOpenAI Whisper cache ({whisper_cache}):")
        if os.path.exists(whisper_cache):
            files = os.listdir(whisper_cache)
            print(f"  Contents: {files}")
            print(f"  Looking for: {self.model_name}.pt")
        else:
            print("  Directory does not exist")

        # Check MLX Whisper cache
        hf_cache = os.path.expanduser("~/.cache/huggingface/hub")
        model_name = f"models--mlx-community--whisper-{self.model_name}-mlx"
        model_path = os.path.join(hf_cache, model_name)
        print(f"\nMLX Whisper cache ({model_path}):")
        if os.path.exists(model_path):
            print("  Directory structure:")
            for root, dirs, files in os.walk(model_path):
                level = root.replace(model_path, "").count(os.sep)
                indent = "  " * (level + 1)
                print(f"{indent}{os.path.basename(root)}/")
                for f in files:
                    print(f"{indent}  {f}")
        else:
            print("  Model directory does not exist")


def main():
    # Configuration
    audio_path = "../test_files/test_video.mp3"
    model_name = "tiny"

    # Run benchmarks
    benchmark = WhisperBenchmark(audio_path, model_name)
    benchmark.run_benchmarks()
    benchmark.save_results()


if __name__ == "__main__":
    main()
