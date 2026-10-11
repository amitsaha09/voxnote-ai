"""Dual-channel audio capture for Windows.

Records simultaneously:
  - Microphone (you / the interviewer)      -> recordings/mic_<timestamp>.wav
  - System audio via WASAPI loopback (them) -> recordings/system_<timestamp>.wav

Two channels = free speaker separation: no ML diarization needed.
Files are normalized to 16kHz mono by utils/aduio_processor.convert_to_wav
when they enter the pipeline, so capture writes native WAV and stays dumb.

Install:  uv pip install sounddevice pyaudiowpatch soundfile numpy
Usage:    python -m core.capture devices   # list devices
          python -m core.capture           # record until ENTER
"""
import threading
import time
import wave
from datetime import datetime
from pathlib import Path

import numpy as np

RECORDINGS_DIR = Path("recordings")
RECORDINGS_DIR.mkdir(exist_ok=True)
MIC_RATE = 16000


def list_devices():
    """Print microphones and WASAPI loopback devices (for setup/debugging)."""
    import sounddevice as sd
    print("=== Microphones ===")
    default_in = sd.default.device[0] if sd.default.device else None
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0:
            mark = " [default]" if i == default_in else ""
            print(f"  [{i}] {d['name']}{mark}")

    print("\n=== System audio (WASAPI loopback) ===")
    import pyaudiowpatch as pyaudio
    p = pyaudio.PyAudio()
    try:
        wasapi = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_out = p.get_device_info_by_index(wasapi["defaultOutputDevice"])
        print(f"  Default output: {default_out['name']}")
        for dev in p.get_loopback_device_info_generator():
            mark = " [matches default output]" if default_out["name"] in dev["name"] else ""
            print(f"  [{dev['index']}] {dev['name']}{mark}")
    finally:
        p.terminate()


def _find_loopback_device(p):
    """WASAPI loopback device matching the default output (fallback: first found)."""
    wasapi = p.get_host_api_info_by_type(p.get_host_api_info_by_type.__self__.paWASAPI) \
        if False else p.get_host_api_info_by_type(__import__("pyaudiowpatch").paWASAPI)
    default_out = p.get_device_info_by_index(wasapi["defaultOutputDevice"])
    loopbacks = list(p.get_loopback_device_info_generator())
    if not loopbacks:
        raise RuntimeError("No WASAPI loopback device found.")
    for dev in loopbacks:
        if default_out["name"] in dev["name"]:
            return dev
    return loopbacks[0]


class DualRecorder:
    """Records mic + system audio at the same time into two WAV files."""

    def __init__(self, mic_device=None, out_dir=RECORDINGS_DIR):
        self.mic_device = mic_device  # None = default mic
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(exist_ok=True)
        self._stop = threading.Event()
        self._threads = []
        self.paths = {}

    def start(self):
        """Begin both streams in background threads. Non-blocking."""
        self._stop.clear()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.paths = {
            "mic": str(self.out_dir / f"mic_{stamp}.wav"),
            "system": str(self.out_dir / f"system_{stamp}.wav"),
        }
        self._threads = [
            threading.Thread(target=self._record_mic, args=(self.paths["mic"],), daemon=True),
            threading.Thread(target=self._record_system, args=(self.paths["system"],), daemon=True),
        ]
        for t in self._threads:
            t.start()
        print(f"Recording… mic → {Path(self.paths['mic']).name}, "
              f"system → {Path(self.paths['system']).name}")
        return self

    def stop(self):
        """Stop both streams, write the WAV files, return their paths."""
        self._stop.set()
        for t in self._threads:
            t.join()
        print("Stopped.")
        return self.paths

    def _record_mic(self, path):
        import sounddevice as sd
        import soundfile as sf
        frames = []

        def callback(indata, frame_count, time_info, status):
            if status:
                print(f"[mic] {status}", flush=True)
            frames.append(indata.copy())

        try:
            with sd.InputStream(samplerate=MIC_RATE, channels=1, dtype="int16",
                                device=self.mic_device, callback=callback):
                while not self._stop.is_set():
                    time.sleep(0.1)
        except Exception as e:  # noqa: BLE001
            print(f"[mic] error: {e}")
            return
        if frames:
            sf.write(path, np.concatenate(frames, axis=0), MIC_RATE)
            print(f"[mic] wrote {Path(path).name}")

    def _record_system(self, path):
        import pyaudiowpatch as pyaudio
        p = pyaudio.PyAudio()
        try:
            dev = _find_loopback_device(p)
            print(f"[system] loopback: {dev['name']}")
            stream = p.open(format=pyaudio.paInt16,
                            channels=int(dev["maxInputChannels"]),
                            rate=int(dev["defaultSampleRate"]),
                            input=True,
                            input_device_index=dev["index"],
                            frames_per_buffer=1024)
        except Exception as e:  # noqa: BLE001
            print(f"[system] error: {e}")
            p.terminate()
            return
        n_channels = int(dev["maxInputChannels"])
        rate = int(dev["defaultSampleRate"])
        raw = []
        try:
            # Poll: stream.read() blocks forever on silence, hanging stop().
            while not self._stop.is_set():
                if stream.get_read_available() >= 1024:
                    raw.append(stream.read(1024, exception_on_overflow=False))
                else:
                    time.sleep(0.05)
        finally:
            try:
                stream.stop_stream()
            except Exception:
                pass
            stream.close()
            p.terminate()
        if raw:
            audio = np.frombuffer(b"".join(raw), dtype=np.int16)
            if n_channels > 1:  # downmix stereo -> mono
                audio = audio.reshape(-1, n_channels).mean(axis=1).astype(np.int16)
            with wave.open(path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(rate)
                wf.writeframes(audio.tobytes())
            print(f"[system] wrote {Path(path).name}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "devices":
        list_devices()
    else:
        rec = DualRecorder().start()
        try:
            input("Recording… press ENTER to stop.\n")
        except KeyboardInterrupt:
            pass
        print(rec.stop())
