#!/bin/sh
# Rebuilds two-voices.wav: macOS voices Samantha and Daniel taking turns, 16 kHz mono.
# Synthetic on purpose, so the speaker-count test has a known answer and no private audio.
set -eu
cd "$(dirname "$0")"
tmp=$(mktemp -d)
i=0
for line in \
    "Samantha|Hi, thanks for making time today. I wanted to walk through the project plan." \
    "Daniel|Sure, happy to. I read the document yesterday and I have a few questions about the timeline." \
    "Samantha|Great. The first phase is discovery, and that runs until the end of the quarter." \
    "Daniel|That makes sense. Who else is involved in discovery, and how often do we meet?" \
    "Samantha|It is the two of us plus the analytics team, and we meet every Tuesday morning." \
    "Daniel|Perfect. I will send over my notes this afternoon so we can start next week."; do
    i=$((i + 1))
    say -v "${line%%|*}" -o "$tmp/$i.aiff" "${line#*|}"
    ffmpeg -nostdin -v error -i "$tmp/$i.aiff" -af apad=pad_dur=1 -ar 16000 -ac 1 "$tmp/$i.wav"
    echo "file '$tmp/$i.wav'" >>"$tmp/list"
done
ffmpeg -nostdin -v error -y -f concat -safe 0 -i "$tmp/list" -c:a pcm_s16le two-voices.wav
rm -rf "$tmp"
