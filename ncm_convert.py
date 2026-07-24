#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Batch-convert NetEase Cloud Music .ncm files to their embedded audio.

The original .ncm and .lrc files are never altered. Converted files retain
the source folder hierarchy below the chosen input directory.

Requires: Python 3 and PyCryptodome (``python -m pip install pycryptodome``).
"""

from __future__ import annotations

import argparse
import base64
import json
import shutil
import sys
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Util.strxor import strxor


CORE_KEY = bytes.fromhex("687A4852416D736F356B496E62617857")
META_KEY = bytes.fromhex("2331346C6A6B5F215C5D2630553C2728")
CHUNK_SIZE = 1024 * 1024
AUDIO_EXTENSIONS = {"mp3", "flac", "m4a", "wav", "aac", "ogg"}


def read_u32(stream) -> int:
    raw = stream.read(4)
    if len(raw) != 4:
        raise ValueError("unexpected end of NCM file")
    return int.from_bytes(raw, "little")


def build_key_box(key: bytes) -> bytearray:
    if not key:
        raise ValueError("empty NCM audio key")
    box = bytearray(range(256))
    j = 0
    for index in range(256):
        j = (box[index] + j + key[index % len(key)]) & 0xFF
        box[index], box[j] = box[j], box[index]
    return box


def build_key_stream(key_box: bytearray) -> bytes:
    """The NCM stream transform repeats every 256 bytes."""
    stream = bytearray(256)
    for index in range(256):
        j = (index + 1) & 0xFF
        stream[index] = key_box[(key_box[j] + key_box[(key_box[j] + j) & 0xFF]) & 0xFF]
    return bytes(stream)


def pkcs7_unpad(value: bytes) -> bytes:
    padding = value[-1] if value else 0
    if 1 <= padding <= AES.block_size and value.endswith(bytes([padding]) * padding):
        return value[:-padding]
    return value


def decode_metadata(raw: bytes) -> dict:
    """Decode optional NCM metadata, returning an empty dict if unavailable."""
    try:
        encoded = bytes(value ^ 0x63 for value in raw)
        encrypted = base64.b64decode(encoded[22:])
        decrypted = pkcs7_unpad(AES.new(META_KEY, AES.MODE_ECB).decrypt(encrypted))
        return json.loads(decrypted[6:].decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return {}


def output_extension(metadata: dict) -> str:
    extension = str(metadata.get("format") or "mp3").lower().strip(".")
    return extension if extension in AUDIO_EXTENSIONS else "mp3"


def convert_one(source: Path, destination: Path) -> Path:
    with source.open("rb") as stream:
        if stream.read(8) != b"CTENFDAM":
            raise ValueError("not a standard NCM file")
        stream.seek(2, 1)

        key_length = read_u32(stream)
        encrypted_key = stream.read(key_length)
        if len(encrypted_key) != key_length:
            raise ValueError("truncated NCM key")
        encrypted_key = bytes(value ^ 0x64 for value in encrypted_key)
        audio_key = AES.new(CORE_KEY, AES.MODE_ECB).decrypt(encrypted_key)[17:]
        key_stream = build_key_stream(build_key_box(pkcs7_unpad(audio_key)))

        metadata_length = read_u32(stream)
        metadata = decode_metadata(stream.read(metadata_length))
        stream.seek(4, 1)  # CRC32
        stream.seek(5, 1)  # unused gap
        cover_length = read_u32(stream)
        stream.seek(cover_length, 1)

        # Append rather than replace the suffix: titles can contain a dot.
        output = Path(f"{destination}.{output_extension(metadata)}")
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("wb") as audio:
            while chunk := stream.read(CHUNK_SIZE):
                repeats = (len(chunk) + len(key_stream) - 1) // len(key_stream)
                audio.write(strxor(chunk, (key_stream * repeats)[: len(chunk)]))
    return output


def existing_audio_path(destination: Path) -> Path | None:
    for extension in AUDIO_EXTENSIONS:
        candidate = Path(f"{destination}.{extension}")
        if candidate.is_file():
            return candidate
    return None


def copy_lyrics(source: Path, audio: Path) -> bool:
    lyrics = source.with_suffix(".lrc")
    if not lyrics.is_file():
        return False
    shutil.copy2(lyrics, audio.with_suffix(".lrc"))
    return True


def main() -> int:
    for console in (sys.stdout, sys.stderr):
        if hasattr(console, "reconfigure"):
            console.reconfigure(errors="backslashreplace")

    parser = argparse.ArgumentParser(description="Convert NetEase .ncm files without modifying originals.")
    parser.add_argument("source", type=Path, help="folder containing .ncm files")
    parser.add_argument("output", type=Path, help="folder for converted music")
    parser.add_argument("--overwrite", action="store_true", help="replace existing converted audio")
    parser.add_argument("--copy-lyrics", action="store_true", help="copy matching .lrc files alongside audio")
    args = parser.parse_args()

    source_root = args.source.resolve()
    if not source_root.is_dir():
        parser.error(f"source folder does not exist: {source_root}")
    output_root = args.output.resolve()
    files = sorted(source_root.rglob("*.ncm"))
    if not files:
        print("No .ncm files found.")
        return 1

    converted = skipped = failed = lyrics = 0
    for number, source in enumerate(files, 1):
        relative_base = source.relative_to(source_root).with_suffix("")
        destination_base = output_root / relative_base
        existing = existing_audio_path(destination_base)
        if existing and not args.overwrite:
            skipped += 1
            print(f"[{number}/{len(files)}] skip  {source.name} (already converted)")
            if args.copy_lyrics and copy_lyrics(source, existing):
                lyrics += 1
            continue
        try:
            if existing and args.overwrite:
                existing.unlink()
            output = convert_one(source, destination_base)
            converted += 1
            print(f"[{number}/{len(files)}] done  {source.name} -> {output.name}")
            if args.copy_lyrics and copy_lyrics(source, output):
                lyrics += 1
        except (OSError, ValueError) as error:
            failed += 1
            print(f"[{number}/{len(files)}] FAIL  {source.name}: {error}", file=sys.stderr)

    print(f"\nFinished: {converted} converted, {skipped} skipped, {failed} failed, {lyrics} lyric files copied.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
