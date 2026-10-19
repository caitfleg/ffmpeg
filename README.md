# dayrec

A tiny CLI that records audio in the background all day to plain WAV files, and turns it into a transcript on your own machine. No GUI, no daemon framework, no cloud, one POSIX shell script on top of `ffmpeg`.

```sh
dayrec start        # start recording in the background
dayrec status       # running? current file, disk used
dayrec stop         # stop; WAV headers are finalized cleanly
dayrec devices      # list mics (and, on Linux, "monitor" sources = what you hear)
dayrec transcribe   # transcribe today (or a file / day folder) with whisper.cpp
dayrec prune        # delete day folders older than DAYREC_KEEP_DAYS (30)
```

Output: one folder per day, one WAV per hour, aligned to the clock:

```
~/Recordings/dayrec/2026-09-25/09-00-00.wav
~/Recordings/dayrec/2026-09-25/10-00-00.wav
```

## Install

Requires `ffmpeg` (Linux: PulseAudio/PipeWire or ALSA; macOS: avfoundation).

```sh
cp dayrec ~/.local/bin/
dayrec start
```

Start automatically:

- **Linux (systemd):** `cp contrib/dayrec.service ~/.config/systemd/user/ && systemctl --user enable --now dayrec`. The service doesn't see your shell's variables, so put settings in the unit as `Environment=` lines (e.g. `Environment=DAYREC_SOURCE=both`).
- **Elsewhere, with cron:** `@reboot $HOME/.local/bin/dayrec start` in `crontab -e`. On a Linux desktop use the systemd unit instead: at boot there is no audio session yet for cron to record from.

On macOS, grant microphone access to your terminal (or `ffmpeg`) the first time.

## Recording calls (both sides)

By default only the microphone is recorded, so with headphones on the other side of a call is lost. `DAYREC_SOURCE=both` records your mic on the **left** channel and everything you hear on the **right**:

```sh
DAYREC_SOURCE=both dayrec start
```

- **Linux (PulseAudio / PipeWire):** works out of the box. "What you hear" comes from the monitor of your current output device; if you switch output (say, to headphones), dayrec notices within 10 seconds and follows it, starting a new file.
- **macOS:** the OS cannot capture its own output. Install a free loopback driver such as [BlackHole](https://existential.audio/blackhole/), create a Multi-Output Device in Audio MIDI Setup (your headphones + BlackHole) and select it as system output, then:
  `DAYREC_SOURCE=both DAYREC_SYSTEM_DEVICE=":BlackHole 2ch" dayrec start`
- `DAYREC_SOURCE=system` records only what you hear.

Keeping the two sides on separate channels is what lets the transcript say who said what. Stereo doubles the disk use (about 5.4 GB/day at the defaults).

Check your local laws before recording calls; some jurisdictions require everyone on the call to consent.

## Transcribing

`dayrec transcribe` runs [whisper.cpp](https://github.com/ggml-org/whisper.cpp) locally, so nothing leaves your machine. Setup once:

```sh
brew install whisper-cpp           # macOS; on Linux build whisper.cpp and put whisper-cli in PATH
mkdir -p ~/.cache/whisper
curl -L -o ~/.cache/whisper/ggml-large-v3-turbo.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin
curl -L -o ~/.cache/whisper/ggml-silero-v6.2.0.bin \
  https://huggingface.co/ggml-org/whisper-vad/resolve/main/ggml-silero-v6.2.0.bin
```

For speaker labels on mono recordings (one mic hearing everyone in the room or on the speakers), also install [uv](https://docs.astral.sh/uv/), put `dayrec-diarize` next to `dayrec`, and fetch the two diarization models:

```sh
cp dayrec-diarize ~/.local/bin/
mkdir -p ~/.cache/dayrec
curl -L https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2 \
  | tar xj -C ~/.cache/dayrec
curl -L -o ~/.cache/dayrec/3dspeaker_speech_eres2net_sv_en_voxceleb_16k.onnx \
  https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/3dspeaker_speech_eres2net_sv_en_voxceleb_16k.onnx
```

The first run has `uv` fetch `sherpa-onnx` into its cache; after that everything runs offline. Tests for the speaker-merging logic: `uv run --with sherpa-onnx --with numpy python -m unittest discover tests`.

Then:

```sh
dayrec transcribe                                   # everything recorded today
dayrec transcribe ~/Recordings/dayrec/2026-09-24    # a whole day
dayrec transcribe some/file.wav                     # one file
```

Each `HH-MM-SS.wav` gets an `HH-MM-SS.txt` next to it. Files already transcribed are skipped (delete a `.txt` to redo it), and so is the file still being recorded, so you can run it from cron every evening.

Mono recordings are split into speakers by voice, and runs of speech by the same person are joined into one line:

```
[00:00:00] Speaker 1: So what is the path forward here?
[00:00:11] Speaker 2: The opportunity is for you to lead the discovery work.
```

Numbers go by who speaks first and are per file: Speaker 1 in `13-00-00.txt` need not be Speaker 1 in `14-00-00.txt`. The number of speakers is guessed, and in a big meeting one person is sometimes split into two numbers. If a 1:1 call comes out with extra speakers, pin it with `DAYREC_SPEAKERS=2 dayrec transcribe ...`. Diarization is the slow part: roughly 5 to 8 minutes per hour of audio. Without `uv` you get the same transcript without labels.

For `both` recordings each channel is transcribed on its own and merged by time:

```
[00:00:00] Me: Hi, can you hear me?
[00:00:02] Them: Loud and clear.
[00:00:05] Me: Yes, I said "done" by Friday.
```

Model choice: `large-v3-turbo` is used when present and is much more accurate than `base.en`, which is the fallback (set `DAYREC_WHISPER_MODEL` to pick another). On an M-series Mac, an hour of audio takes about 4 minutes with turbo. With the Silero VAD model in place silence is skipped, which also stops whisper from hallucinating phrases like "Thank you." in long quiet stretches.

## Settings

Environment variables, all optional:

| Variable | Default | Notes |
|---|---|---|
| `DAYREC_DIR` | `~/Recordings/dayrec` | output folder |
| `DAYREC_SOURCE` | `mic` | `mic`, `system` (what you hear) or `both` (stereo: L = mic, R = system) |
| `DAYREC_SYSTEM_DEVICE` | default output's monitor | required on macOS (e.g. `":BlackHole 2ch"`) |
| `DAYREC_RATE` | `16000` | Hz; 16 kHz is plenty for speech |
| `DAYREC_CHUNK` | `3600` | seconds per file |
| `DAYREC_DEVICE` | system default | see `dayrec devices` |
| `DAYREC_FORMAT` | auto | `pulse`, `alsa`, `avfoundation` |
| `DAYREC_KEEP_DAYS` | `30` | used by `prune` |
| `DAYREC_WHISPER_MODEL` | `~/.cache/whisper/ggml-large-v3-turbo.bin`, else `ggml-base.en.bin` | whisper.cpp ggml model |
| `DAYREC_VAD_MODEL` | `~/.cache/whisper/ggml-silero-v6.2.0.bin` | skips silence; ignored if missing |
| `DAYREC_LANG` | `en` | transcription language |
| `DAYREC_SPEAKERS` | guess | speakers per file, for mono recordings |
| `DAYREC_SPEAKER_THRESHOLD` | `1.0` | when guessing: higher means fewer speakers |
| `DAYREC_DIARIZE_DIR` | `~/.cache/dayrec` | diarization models |

## Resources

It's one `ffmpeg` process writing raw PCM (no encoding), run at `nice 10`. CPU use is well under 1%. Disk: 16 kHz mono 16-bit is about 115 MB/hour, 2.7 GB/day. Hourly chunks keep every file far below the 4 GB WAV limit and mean a crash or power loss costs at most the current hour's header.

`prune` doesn't run on its own. To keep the disk from filling up, schedule it, e.g. `0 3 * * * $HOME/.local/bin/dayrec prune` in `crontab -e`.

If the mic disappears (unplugged, busy), dayrec logs it to `$DAYREC_DIR/.dayrec.log` and retries every 10 seconds.
