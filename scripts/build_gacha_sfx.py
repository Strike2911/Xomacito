from __future__ import annotations

import math
import struct
import wave
from dataclasses import dataclass
from pathlib import Path


SAMPLE_RATE = 44_100
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "assets" / "sfx"


@dataclass(frozen=True)
class Tone:
    start: float
    duration: float
    frequency: float
    volume: float
    sweep: float = 0.0
    waveform: str = "sine"
    attack: float = 0.02
    release: float = 0.18


def _oscillator(phase: float, waveform: str) -> float:
    if waveform == "triangle":
        return 2.0 / math.pi * math.asin(math.sin(phase))
    if waveform == "soft-square":
        # A rounded pulse with very little upper-harmonic energy avoids the old buzz.
        return (
            math.sin(phase) * 0.86
            + math.sin(phase * 2.0) * 0.10
            + math.sin(phase * 3.0) * 0.04
        )
    if waveform == "chime":
        return (
            math.sin(phase) * 0.80
            + math.sin(phase * 2.01) * 0.15
            + math.sin(phase * 3.97) * 0.05
        )
    return math.sin(phase)


def _envelope(local_time: float, tone: Tone) -> float:
    attack = min(1.0, local_time / max(0.001, tone.attack))
    remaining = tone.duration - local_time
    release = min(1.0, remaining / max(0.001, tone.release))
    return max(0.0, min(attack, release)) ** 1.35


def render(filename: str, duration: float, tones: list[Tone], *, sparkle: float = 0.0) -> None:
    raw_samples: list[float] = []
    filtered = 0.0
    # One-pole low-pass: it preserves the musical impact while taming brittle highs.
    cutoff_hz = 6_800.0
    low_pass_alpha = 1.0 - math.exp(-2.0 * math.pi * cutoff_hz / SAMPLE_RATE)
    for frame in range(int(duration * SAMPLE_RATE)):
        current = frame / SAMPLE_RATE
        mixed = 0.0
        for tone in tones:
            local = current - tone.start
            if local < 0 or local >= tone.duration:
                continue
            frequency = tone.frequency + tone.sweep * (local / tone.duration)
            phase = 2.0 * math.pi * frequency * local
            mixed += _oscillator(phase, tone.waveform) * tone.volume * _envelope(local, tone)
        if sparkle and 0.12 < current < duration - 0.08:
            burst = max(0.0, math.sin(current * math.pi * (15 + int(current * 7))))
            shimmer = (
                math.sin(2.0 * math.pi * 2_850.0 * current) * 0.72
                + math.sin(2.0 * math.pi * 4_120.0 * current) * 0.28
            )
            mixed += shimmer * sparkle * burst**7

        # Short global fades prevent clicks and a gentle low-pass avoids sharp edges.
        edge_fade = min(1.0, current / 0.012, (duration - current) / 0.035)
        filtered += low_pass_alpha * (mixed - filtered)
        raw_samples.append(filtered * max(0.0, edge_fade))

    peak = max((abs(sample) for sample in raw_samples), default=1.0)
    # 62% peak leaves generous headroom for Windows mixers and small speakers.
    gain = 0.62 / max(0.001, peak)
    samples = [
        int(max(-0.62, min(0.62, sample * gain)) * 32767)
        for sample in raw_samples
    ]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUTPUT_DIR / filename), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))


def chord(start: float, duration: float, notes: list[float], volume: float) -> list[Tone]:
    return [
        Tone(
            start, duration, note, volume / max(1, len(notes)),
            waveform="chime", attack=0.012, release=duration * 0.62,
        )
        for note in notes
    ]


def main() -> None:
    render("gacha-reveal-1.wav", 0.55, [
        Tone(0.02, 0.34, 523.25, 0.42, sweep=38, waveform="triangle"),
        Tone(0.15, 0.30, 783.99, 0.25),
    ], sparkle=0.018)
    render("gacha-reveal-2.wav", 0.72, [
        Tone(0.02, 0.38, 523.25, 0.34, waveform="triangle"),
        Tone(0.20, 0.40, 659.25, 0.32, waveform="triangle"),
        Tone(0.34, 0.32, 987.77, 0.22),
    ], sparkle=0.025)
    render("gacha-reveal-3.wav", 0.95, [
        Tone(0.00, 0.58, 392.00, 0.30, sweep=96, waveform="triangle"),
        Tone(0.20, 0.55, 587.33, 0.28, sweep=82),
        *chord(0.44, 0.46, [783.99, 987.77, 1174.66], 0.62),
    ], sparkle=0.035)
    render("gacha-reveal-4.wav", 1.20, [
        Tone(0.00, 0.74, 261.63, 0.26, sweep=500, waveform="soft-square"),
        Tone(0.17, 0.50, 659.25, 0.24),
        Tone(0.34, 0.52, 830.61, 0.26),
        *chord(0.58, 0.54, [1046.50, 1318.51, 1567.98], 0.72),
    ], sparkle=0.048)
    render("gacha-reveal-5.wav", 1.58, [
        Tone(0.00, 1.00, 196.00, 0.25, sweep=720, waveform="soft-square"),
        Tone(0.22, 0.70, 783.99, 0.24),
        Tone(0.42, 0.72, 987.77, 0.26),
        *chord(0.68, 0.82, [1174.66, 1567.98, 1975.53], 0.86),
    ], sparkle=0.062)
    render("gacha-reveal-6-arcane.wav", 2.35, [
        Tone(0.00, 1.55, 110.00, 0.22, sweep=660, waveform="soft-square"),
        Tone(0.18, 1.10, 329.63, 0.24, sweep=990),
        Tone(0.46, 0.82, 987.77, 0.24),
        *chord(0.94, 1.26, [523.25, 783.99, 1046.50, 1567.98], 1.10),
        Tone(1.28, 0.86, 2093.00, 0.22, sweep=620),
    ], sparkle=0.074)
    render("gacha-reveal-6-playera.wav", 2.28, [
        Tone(0.00, 0.55, 174.61, 0.32, sweep=180, waveform="triangle"),
        Tone(0.18, 0.42, 523.25, 0.34, waveform="triangle"),
        Tone(0.42, 0.44, 659.25, 0.36, waveform="triangle"),
        Tone(0.66, 0.46, 783.99, 0.38, waveform="triangle"),
        Tone(0.90, 0.48, 1046.50, 0.36, waveform="triangle"),
        *chord(1.16, 0.98, [659.25, 987.77, 1318.51, 2093.00], 1.08),
    ], sparkle=0.082)
    render("gacha-reveal-6-zarking.wav", 2.32, [
        Tone(0.00, 0.82, 88.00, 0.30, sweep=1180, waveform="soft-square"),
        Tone(0.18, 0.42, 880.00, 0.23, sweep=1760, waveform="soft-square"),
        Tone(0.54, 0.26, 1760.00, 0.20, sweep=-660, waveform="soft-square"),
        Tone(0.78, 0.56, 440.00, 0.30, sweep=1320, waveform="triangle"),
        *chord(1.16, 1.02, [740.00, 1108.73, 1480.00, 2217.46], 1.12),
    ], sparkle=0.066)
    render("gacha-reveal-6-blackbull.wav", 2.48, [
        Tone(0.00, 1.18, 73.42, 0.30, sweep=210, waveform="soft-square"),
        Tone(0.18, 0.88, 146.83, 0.27, sweep=440, waveform="triangle"),
        Tone(0.58, 0.72, 369.99, 0.24, sweep=380, waveform="chime"),
        *chord(1.02, 1.30, [293.66, 440.00, 739.99, 1174.66], 1.12),
        Tone(1.42, 0.86, 1760.00, 0.20, sweep=520, waveform="chime"),
    ], sparkle=0.052)
    render("gacha-reveal-6-strike.wav", 3.18, [
        Tone(0.00, 1.75, 65.41, 0.30, sweep=420, waveform="soft-square"),
        Tone(0.26, 1.30, 196.00, 0.25, sweep=980, waveform="triangle"),
        Tone(0.72, 0.92, 783.99, 0.22, sweep=880, waveform="chime"),
        *chord(1.28, 1.72, [392.00, 587.33, 783.99, 1174.66, 1567.98], 1.22),
        Tone(1.92, 1.08, 2093.00, 0.20, sweep=720, waveform="chime"),
    ], sparkle=0.078)
    render("gacha-equip-6-arcane.wav", 1.82, [
        Tone(0.00, 1.18, 130.81, 0.26, sweep=720, waveform="soft-square"),
        *chord(0.48, 1.20, [523.25, 783.99, 1046.50], 0.88),
    ], sparkle=0.058)
    render("gacha-equip-6-playera.wav", 1.74, [
        Tone(0.00, 0.42, 392.00, 0.36, waveform="triangle"),
        Tone(0.24, 0.46, 659.25, 0.36, waveform="triangle"),
        Tone(0.48, 0.50, 987.77, 0.36, waveform="triangle"),
        *chord(0.82, 0.82, [783.99, 1174.66, 1567.98], 0.92),
    ], sparkle=0.075)
    render("gacha-equip-6-zarking.wav", 1.78, [
        Tone(0.00, 0.66, 92.50, 0.30, sweep=1380, waveform="soft-square"),
        Tone(0.36, 0.50, 1108.73, 0.25, sweep=840, waveform="soft-square"),
        *chord(0.76, 0.92, [554.37, 830.61, 1244.51, 1661.22], 0.98),
    ], sparkle=0.058)
    render("gacha-equip-6-blackbull.wav", 1.94, [
        Tone(0.00, 0.92, 82.41, 0.30, sweep=240, waveform="soft-square"),
        Tone(0.32, 0.72, 220.00, 0.28, sweep=330, waveform="triangle"),
        *chord(0.74, 1.08, [293.66, 440.00, 587.33, 880.00], 1.02),
    ], sparkle=0.046)
    render("gacha-equip-6-strike.wav", 2.36, [
        Tone(0.00, 1.18, 82.41, 0.28, sweep=620, waveform="soft-square"),
        Tone(0.38, 0.92, 329.63, 0.25, sweep=760, waveform="triangle"),
        *chord(0.86, 1.34, [392.00, 659.25, 987.77, 1567.98], 1.08),
    ], sparkle=0.068)


if __name__ == "__main__":
    main()
