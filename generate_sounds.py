#!/usr/bin/env python3
"""
Generates cat mating call WAV files using pure Python/numpy synthesis.
No internet, no AI account, no broken dependencies.
Run once:  python3 generate_sounds.py
"""

import struct
import math
import random
import os

FOLDER = os.path.dirname(os.path.abspath(__file__))
SAMPLE_RATE = 44100


def write_wav(filename, samples):
    """Write a list of float samples (-1.0 to 1.0) as a 16-bit mono WAV file."""
    num_samples = len(samples)
    with open(filename, "wb") as f:
        # RIFF header
        data_size = num_samples * 2
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        # fmt chunk
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))       # chunk size
        f.write(struct.pack("<H", 1))        # PCM
        f.write(struct.pack("<H", 1))        # mono
        f.write(struct.pack("<I", SAMPLE_RATE))
        f.write(struct.pack("<I", SAMPLE_RATE * 2))  # byte rate
        f.write(struct.pack("<H", 2))        # block align
        f.write(struct.pack("<H", 16))       # bits per sample
        # data chunk
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        for s in samples:
            val = max(-1.0, min(1.0, s))
            f.write(struct.pack("<h", int(val * 32767)))


def envelope(t, total, attack=0.05, decay=0.1, sustain=0.7, release=0.2):
    """Simple ADSR amplitude envelope."""
    a = attack * total
    d = decay * total
    s_end = (1 - release) * total
    r = release * total
    if t < a:
        return t / a
    elif t < a + d:
        return 1.0 - (1.0 - sustain) * (t - a) / d
    elif t < s_end:
        return sustain
    else:
        return sustain * max(0.0, 1.0 - (t - s_end) / r)


def generate_mating_call(seed=None):
    """
    Synthesise a cat mating yowl.
    Cat mating calls are 300–900 Hz with:
      - a slow rising sweep
      - vibrato (~6 Hz wobble)
      - breathy noise mixed in
      - a characteristic 'n' nasal resonance (odd harmonics stronger)
    Returns a list of float samples.
    """
    rng = random.Random(seed)
    duration = rng.uniform(1.4, 2.6)           # seconds
    base_freq = rng.uniform(320, 480)           # starting pitch
    peak_freq = rng.uniform(600, 950)           # peak pitch
    vibrato_rate = rng.uniform(5.0, 7.5)        # Hz
    vibrato_depth = rng.uniform(0.06, 0.14)     # fraction of freq
    noise_mix = rng.uniform(0.04, 0.10)         # breathiness
    # second yowl sometimes appended
    add_second = rng.random() < 0.6

    def make_yowl(dur, f0, f1, vib_rate, vib_dep, n_mix):
        n = int(dur * SAMPLE_RATE)
        samples = []
        phase = 0.0
        phase2 = 0.0   # second harmonic
        phase3 = 0.0   # third harmonic (nasal quality)
        for i in range(n):
            t = i / SAMPLE_RATE
            # frequency sweep with vibrato
            sweep = f0 + (f1 - f0) * math.sin(math.pi * t / dur * 0.9)
            freq = sweep * (1.0 + vib_dep * math.sin(2 * math.pi * vib_rate * t))
            dt = freq / SAMPLE_RATE

            phase += dt
            phase2 += dt * 2
            phase3 += dt * 3

            # odd harmonics stronger → nasal/yowl quality
            sig = (0.55 * math.sin(2 * math.pi * phase) +
                   0.20 * math.sin(2 * math.pi * phase2) +
                   0.18 * math.sin(2 * math.pi * phase3) +
                   0.07 * math.sin(2 * math.pi * phase * 4))

            # breath noise
            noise = (rng.random() * 2 - 1) * n_mix

            amp = envelope(t, dur)
            samples.append((sig + noise) * amp * 0.72)
        return samples

    samples = make_yowl(duration, base_freq, peak_freq,
                        vibrato_rate, vibrato_depth, noise_mix)

    if add_second:
        gap = int(rng.uniform(0.08, 0.22) * SAMPLE_RATE)
        samples += [0.0] * gap
        d2 = rng.uniform(0.8, 1.6)
        f0b = rng.uniform(280, 420)
        f1b = rng.uniform(550, 850)
        samples += make_yowl(d2, f0b, f1b, vibrato_rate,
                             vibrato_depth * rng.uniform(0.8, 1.2), noise_mix)

    return samples


def main():
    # Generate cat1–cat4 only if they don't already exist (keeps your real downloads)
    targets = {
        "cat1.wav": 1,
        "cat3.wav": 3,
        "cat4.wav": 4,
    }
    # cat2 was deleted — regenerate it with the AI synthesiser
    targets["cat2.wav"] = 2

    for filename, seed in targets.items():
        path = os.path.join(FOLDER, filename)
        if os.path.exists(path):
            print(f"  {filename} already exists — skipping (delete it to regenerate)")
            continue
        print(f"  Generating {filename} ...")
        samples = generate_mating_call(seed=seed)
        write_wav(path, samples)
        print(f"  Done → {path}  ({len(samples)/SAMPLE_RATE:.1f}s)")

    print("\nAll done! Test with:  paplay cat2.wav")
    print("Run again with different seeds to get different sounds.")


if __name__ == "__main__":
    main()
