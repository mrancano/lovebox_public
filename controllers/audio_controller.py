import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path


_DEFAULT_PLAYERS = (
    ("aplay", ["-q"]),  # Moved to the top to prioritize ALSA for WAV playback
    ("ffplay", ["-nodisp", "-autoexit", "-loglevel", "error"]),
    ("ogg123", ["-q"]),
    ("mpg123", ["-q"]),
    ("paplay", []),
)


class AudioController:
    """Controller for playing audio files via a system audio player."""

    def __init__(self, player: str | None = None):
        self._player_spec = player or os.getenv("LOVEBOX_AUDIO_PLAYER")
        self._player_cmd: list[str] | None = None
        self._process: subprocess.Popen | None = None

    def _resolve_player(self):
        if self._player_cmd:
            return

        if self._player_spec:
            tokens = shlex.split(self._player_spec)
            executable = tokens[0]
            player_path = shutil.which(executable)
            if not player_path:
                raise FileNotFoundError(f"Audio player not found: {executable}")
            self._player_cmd = [player_path] + tokens[1:]
            return

        for player, args in _DEFAULT_PLAYERS:
            player_path = shutil.which(player)
            if player_path:
                self._player_cmd = [player_path] + args
                return

        raise FileNotFoundError(
            "No supported audio player found. Install aplay, ffplay, ogg123, mpg123, or set LOVEBOX_AUDIO_PLAYER."
        )

    def _convert_to_wav(self, file_path: Path) -> Path:
        """Converts the input file to WAV format using ffmpeg if it is not already a WAV."""
        if file_path.suffix.lower() == ".wav":
            return file_path

        if not shutil.which("ffmpeg"):
            raise FileNotFoundError("ffmpeg is required to convert audio to WAV but was not found.")

        # Create a temporary file for the WAV output
        fd, temp_wav_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd) 

        try:
            # Convert to WAV, overwriting the temp file, suppressing output
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(file_path), temp_wav_path],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError as e:
            os.remove(temp_wav_path)
            raise RuntimeError(f"Failed to convert {file_path} to WAV.") from e

        return Path(temp_wav_path)

    def play_audio(self, file_path: str):
        audio_file = Path(file_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file does not exist: {audio_file}")

        self._resolve_player()

        if self._process and self._process.poll() is None:
            raise RuntimeError("Audio playback already in progress.")

        # Ensure the file is a WAV
        wav_file = self._convert_to_wav(audio_file)

        try:
            self._process = subprocess.Popen(self._player_cmd + [str(wav_file)])
            return_code = self._process.wait()
            self._process = None

            if return_code != 0:
                raise RuntimeError(f"Audio playback failed with exit code {return_code}.")
        finally:
            # Clean up the temporary WAV file if one was created
            if wav_file != audio_file and wav_file.exists():
                wav_file.unlink()

    def stop(self):
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=5)
            self._process = None