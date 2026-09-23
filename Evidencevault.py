#!/usr/bin/env python3
"""
EvidenceVault
=============
A lightweight, dependency-free, cross-platform (Linux / Windows / macOS / Termux)
command-line toolkit for fast batch encoding, bundling, renaming, and sorting of
files, folders, and images -- built with digital-forensics / OSINT / cyber-crime
intelligence workflows in mind (hashing, chain-of-custody logs, integrity checks).

USAGE EXAMPLES
--------------
    # Encode every file under ./case_files (recursively) to Base64, in parallel
    python3 evidencevault.py encode ./case_files -e base64 -r -o ./encoded --workers 8

    # Decode a previously encoded file/folder back to its original bytes
    python3 evidencevault.py decode ./encoded -o ./restored

    # Bundle a whole investigation folder into ONE portable, hash-verified vault file
    python3 evidencevault.py bundle ./case_files -e base64 -r --compress \
        --case "CASE-2026-0091" -o case_0091.vault.json

    # Verify a vault's integrity without extracting anything
    python3 evidencevault.py verify case_0091.vault.json

    # Extract a vault back to disk, re-checking every SHA-256 hash on the way out
    python3 evidencevault.py extract case_0091.vault.json -o ./restored_case

    # Generate a chain-of-custody hash manifest (SHA-256 + MD5) for a folder
    python3 evidencevault.py hash ./case_files -r -o manifest.csv

    # Batch-rename a folder (and its subfolders) using a naming template, safely
    python3 evidencevault.py rename ./messy_dump -r \
        --pattern "EVID_{date}_{n:04d}_{hash}{ext}" --dry-run

    # Sort a folder's contents into subfolders by file type
    python3 evidencevault.py sort ./inbox --by ext -o ./sorted

REQUIREMENTS
------------
Python 3.8+. Standard library only -- no pip installs required, which is why
this runs unmodified on Termux, a bare Debian box, Windows, or macOS.

INSTALL (optional)
-------------------
    chmod +x evidencevault.py
    ./evidencevault.py --help

Author: EvidenceVault contributors. License: Apache-2.0.
"""

from __future__ import annotations

import argparse
import base64
import concurrent.futures
import csv
import hashlib
import json
import logging
import os
import re
import shutil
import sys
import time
import zlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote_from_bytes, unquote_to_bytes

VERSION = "1.0.0"
VAULT_FORMAT_VERSION = "1.0"

# --------------------------------------------------------------------------- #
# Encoding registry -- add a new codec here and every subcommand picks it up
# --------------------------------------------------------------------------- #


def _urlenc_encode(data: bytes) -> bytes:
    return quote_from_bytes(data, safe="").encode("ascii")


def _urlenc_decode(data: bytes) -> bytes:
    return unquote_to_bytes(data.decode("ascii"))


ENCODINGS: Dict[str, Dict] = {
    "base64":    {"ext": "b64",    "encode": base64.b64encode,         "decode": base64.b64decode},
    "base64url": {"ext": "b64u",   "encode": base64.urlsafe_b64encode, "decode": base64.urlsafe_b64decode},
    "base32":    {"ext": "b32",    "encode": base64.b32encode,         "decode": base64.b32decode},
    "base16":    {"ext": "hex",    "encode": base64.b16encode,         "decode": base64.b16decode},
    "base85":    {"ext": "b85",    "encode": base64.b85encode,         "decode": base64.b85decode},
    "ascii85":   {"ext": "a85",    "encode": base64.a85encode,         "decode": base64.a85decode},
    "urlenc":    {"ext": "urlenc", "encode": _urlenc_encode,           "decode": _urlenc_decode},
}
EXT_TO_ENCODING = {v["ext"]: k for k, v in ENCODINGS.items()}

ILLEGAL_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
RESERVED_WIN_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

EXT_CATEGORIES = {
    "images":   {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp", ".heic", ".svg"},
    "documents": {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".csv", ".ppt", ".pptx"},
    "archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"},
    "encoded":  {f".{e['ext']}" for e in ENCODINGS.values()} | {".vault.json"},
    "video":    {".mp4", ".mkv", ".avi", ".mov", ".webm"},
    "audio":    {".mp3", ".wav", ".flac", ".ogg", ".m4a"},
}

log = logging.getLogger("evidencevault")


# --------------------------------------------------------------------------- #
# Startup banner -- terminal-only, cyberpunk/retro-terminal vault aesthetic
# --------------------------------------------------------------------------- #

_ANSI = {
    "reset": "\033[0m", "bold": "\033[1m", "dim": "\033[2m",
    "green": "\033[38;5;46m", "amber": "\033[38;5;214m",
    "cyan": "\033[38;5;51m", "magenta": "\033[38;5;201m", "grey": "\033[38;5;240m",
}

# ANSI Shadow block-font renderings of "EVIDENCE" and "VAULT", 64/41 cols wide.
_TITLE_EVIDENCE = r"""
███████╗██╗   ██╗██╗██████╗ ███████╗███╗   ██╗ ██████╗███████╗
██╔════╝██║   ██║██║██╔══██╗██╔════╝████╗  ██║██╔════╝██╔════╝
█████╗  ██║   ██║██║██║  ██║█████╗  ██╔██╗ ██║██║     █████╗
██╔══╝  ╚██╗ ██╔╝██║██║  ██║██╔══╝  ██║╚██╗██║██║     ██╔══╝
███████╗ ╚████╔╝ ██║██████╔╝███████╗██║ ╚████║╚██████╗███████╗
╚══════╝  ╚═══╝  ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═══╝ ╚═════╝╚══════╝
""".strip("\n").splitlines()

_TITLE_VAULT = r"""
██╗   ██╗ █████╗ ██╗   ██╗██╗  ████████╗
██║   ██║██╔══██╗██║   ██║██║  ╚══██╔══╝
██║   ██║███████║██║   ██║██║     ██║
╚██╗ ██╔╝██╔══██║██║   ██║██║     ██║
 ╚████╔╝ ██║  ██║╚██████╔╝███████╗██║
  ╚═══╝  ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝
""".strip("\n").splitlines()

# Small radial vault-door / optic glyph shown above the title on wide terminals.
_VAULT_EYE = [
    "         .:▓▓▓▓▓▓▓▓▓▓:.",
    "      .:▓▓░░░░░░░░░░░░▓▓:.",
    "    :▓▓░░◢▓▓▓▓▓▓▓▓▓▓▓◣░░▓▓:",
    "   ▓▓░░◢▓▓▓▓▓█▓▓█▓▓▓▓▓◣░░▓▓",
    "   ▓▓░░▓▓▓▓█▓▓◉◉▓▓█▓▓▓▓░░▓▓",
    "   ▓▓░░◥▓▓▓▓▓█▓▓█▓▓▓▓▓◤░░▓▓",
    "    :▓▓░░◥▓▓▓▓▓▓▓▓▓▓▓◤░░▓▓:",
    "      ':▓▓░░░░░░░░░░░░▓▓:'",
    "         ':▓▓▓▓▓▓▓▓▓▓:'",
]

_BOOT_LINES = [
    "INITIALIZING TERMINAL",
    "CALIBRATING OPTICAL SENSOR",
    "MOUNTING ENCODING MODULES",
    "VAULT INTEGRITY: NOMINAL",
]


def _banner_enabled() -> bool:
    if os.environ.get("NO_COLOR") is not None or os.environ.get("EVIDENCEVAULT_NO_BANNER") is not None:
        return False
    if "--no-banner" in sys.argv or "-q" in sys.argv or "--quiet" in sys.argv:
        return False
    try:
        return sys.stdout.isatty()
    except Exception:  # noqa: BLE001 -- never let banner logic crash the tool
        return False


def _c(text: str, color: str, use_color: bool) -> str:
    return f"{_ANSI[color]}{text}{_ANSI['reset']}" if use_color else text


def print_banner(animate: bool = True) -> None:
    """Print the EvidenceVault startup banner. Silently skipped on non-TTY output,
    when NO_COLOR/EVIDENCEVAULT_NO_BANNER is set, or when --no-banner/-q is passed --
    so piping/scripting output is never polluted."""
    if not _banner_enabled():
        return

    if os.name == "nt":
        os.system("")  # enable ANSI/VT100 escape processing on legacy Windows cmd.exe

    use_color = os.environ.get("EVIDENCEVAULT_NO_COLOR") is None
    width = shutil.get_terminal_size(fallback=(80, 24)).columns

    try:
        if width >= 66:
            for line in _VAULT_EYE:
                print(_c(line.center(width - 1), "green", use_color))
            print()
            for line in _TITLE_EVIDENCE:
                print(_c(line.center(width - 1), "green", use_color))
            for line in _TITLE_VAULT:
                print(_c(line.center(width - 1), "amber", use_color))
        else:
            # Compact fallback for narrow terminals (Termux portrait, small SSH panes)
            print(_c("[ EVIDENCEVAULT ]".center(width), "green", use_color))

        rule = "═" * min(width - 1, 64)
        print(_c(rule.center(width), "grey", use_color))
        tagline = "RETRO-TERMINAL FORENSICS UNIT // BATCH ENCODE · BUNDLE · RENAME · SORT"
        print(_c(tagline[: width - 1].center(width - 1), "cyan", use_color))
        print(_c(f"build v{VERSION}".center(width - 1), "grey", use_color))
        print(_c(rule.center(width), "grey", use_color))

        if animate and width >= 66:
            for line in _BOOT_LINES:
                msg = f"[ {line}"
                sys.stdout.write(_c(msg, "magenta" if use_color else "grey", use_color))
                sys.stdout.flush()
                for _ in range(3):
                    time.sleep(0.03)
                    sys.stdout.write(_c(".", "magenta", use_color))
                    sys.stdout.flush()
                print(_c(" OK ]", "green", use_color))
            print(_c("[ READY. ]".center(width - 1), "amber", use_color))
        print()
    except Exception:  # noqa: BLE001 -- a cosmetic banner must never break the tool
        pass


# --------------------------------------------------------------------------- #
# Small utilities
# --------------------------------------------------------------------------- #


def setup_logging(verbose: bool, logfile: Optional[str] = None) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handlers: List[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if logfile:
        handlers.append(logging.FileHandler(logfile, encoding="utf-8"))
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )


def hash_file(path: Path, algo: str = "sha256", chunk_size: int = 1 << 20) -> str:
    """Stream a file through a hash function -- safe for multi-GB evidence files."""
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_input_files(paths: List[str], recursive: bool) -> List[Path]:
    """Expand a mixed list of file/folder CLI arguments into a flat file list."""
    out: List[Path] = []
    for raw in paths:
        p = Path(raw)
        if not p.exists():
            log.warning("Path does not exist, skipping: %s", p)
            continue
        if p.is_file():
            out.append(p)
        elif p.is_dir():
            walker = p.rglob("*") if recursive else p.glob("*")
            out.extend(sorted(f for f in walker if f.is_file()))
    return out


def sanitize_filename(name: str, replacement: str = "_") -> str:
    """Strip characters illegal on any of Windows/Linux/macOS and trim edge cruft."""
    stem, ext = os.path.splitext(name)
    stem = ILLEGAL_CHARS_RE.sub(replacement, stem).strip().rstrip(". ")
    if not stem:
        stem = "unnamed"
    if stem.upper() in RESERVED_WIN_NAMES:
        stem = f"{stem}_file"
    return f"{stem}{ext}"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


class Timer:
    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.elapsed = time.perf_counter() - self.start


# --------------------------------------------------------------------------- #
# encode / decode -- fast batch, one file <-> one encoded file
# --------------------------------------------------------------------------- #


def _encode_one(args: Tuple[str, str, str, bool]) -> Tuple[str, bool, str]:
    """Worker: (src_path, encoding_name, out_path, compress) -> (src, ok, message)."""
    src_str, encoding, out_str, compress = args
    src, out = Path(src_str), Path(out_str)
    try:
        data = src.read_bytes()
        if compress:
            data = zlib.compress(data, level=9)
        encoded = ENCODINGS[encoding]["encode"](data)
        ensure_parent(out)
        out.write_bytes(encoded)
        return (src_str, True, str(out))
    except Exception as exc:  # noqa: BLE001 -- surface every failure to the caller
        return (src_str, False, str(exc))


def _decode_one(args: Tuple[str, str, str, bool]) -> Tuple[str, bool, str]:
    """Worker: (src_path, encoding_name, out_path, decompress) -> (src, ok, message)."""
    src_str, encoding, out_str, decompress = args
    src, out = Path(src_str), Path(out_str)
    try:
        raw = ENCODINGS[encoding]["decode"](src.read_bytes())
        if decompress:
            raw = zlib.decompress(raw)
        ensure_parent(out)
        out.write_bytes(raw)
        return (src_str, True, str(out))
    except Exception as exc:  # noqa: BLE001
        return (src_str, False, str(exc))


def cmd_encode(args: argparse.Namespace) -> int:
    files = iter_input_files(args.paths, args.recursive)
    if not files:
        log.error("No input files found.")
        return 1

    ext = ENCODINGS[args.encoding]["ext"]
    tasks = []
    for f in files:
        if args.output:
            # Mirror relative structure under the output directory
            try:
                rel = f.relative_to(Path(args.paths[0]))
            except ValueError:
                rel = Path(f.name)
            out_path = Path(args.output) / rel.parent / f"{f.name}.{ext}"
        else:
            out_path = f.with_name(f"{f.name}.{ext}")
        tasks.append((str(f), args.encoding, str(out_path), args.compress))

    log.info("Encoding %d file(s) -> %s (%s workers)", len(tasks), args.encoding, args.workers)
    ok_count, fail_count = 0, 0
    with Timer() as t, concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        for src, ok, msg in pool.map(_encode_one, tasks):
            if ok:
                ok_count += 1
                log.debug("OK   %s -> %s", src, msg)
            else:
                fail_count += 1
                log.error("FAIL %s: %s", src, msg)

    log.info("Done: %d encoded, %d failed in %.2fs", ok_count, fail_count, t.elapsed)
    return 0 if fail_count == 0 else 2


def cmd_decode(args: argparse.Namespace) -> int:
    files = iter_input_files(args.paths, args.recursive)
    if not files:
        log.error("No input files found.")
        return 1

    tasks = []
    for f in files:
        detected = args.encoding or EXT_TO_ENCODING.get(f.suffix.lstrip("."))
        if not detected:
            log.warning("Cannot infer encoding for %s (use --encoding), skipping", f)
            continue
        base_name = f.name[: -(len(f.suffix))] if not args.encoding else f.name
        if args.output:
            try:
                rel = f.relative_to(Path(args.paths[0]))
            except ValueError:
                rel = Path(f.name)
            out_path = Path(args.output) / rel.parent / base_name
        else:
            out_path = f.with_name(base_name)
        tasks.append((str(f), detected, str(out_path), args.decompress))

    if not tasks:
        log.error("Nothing decodable found.")
        return 1

    log.info("Decoding %d file(s) (%s workers)", len(tasks), args.workers)
    ok_count, fail_count = 0, 0
    with Timer() as t, concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        for src, ok, msg in pool.map(_decode_one, tasks):
            if ok:
                ok_count += 1
                log.debug("OK   %s -> %s", src, msg)
            else:
                fail_count += 1
                log.error("FAIL %s: %s", src, msg)

    log.info("Done: %d decoded, %d failed in %.2fs", ok_count, fail_count, t.elapsed)
    return 0 if fail_count == 0 else 2


# --------------------------------------------------------------------------- #
# bundle / extract / verify -- compile everything into ONE vault file
# --------------------------------------------------------------------------- #


@dataclass
class VaultEntry:
    path: str          # posix-style relative path, preserved for reconstruction
    encoding: str
    compressed: bool
    sha256: str
    size: int
    mtime: str
    data: str          # the encoded payload itself


def _bundle_one(args: Tuple[str, str, str, bool]) -> Tuple[str, Optional[dict], Optional[str]]:
    """Worker: (abs_path, rel_path, encoding, compress) -> (abs_path, entry_dict|None, error|None)."""
    abs_str, rel_str, encoding, compress = args
    p = Path(abs_str)
    try:
        raw = p.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        stat = p.stat()
        payload = zlib.compress(raw, level=9) if compress else raw
        encoded = ENCODINGS[encoding]["encode"](payload).decode("ascii")
        entry = VaultEntry(
            path=rel_str,
            encoding=encoding,
            compressed=compress,
            sha256=digest,
            size=len(raw),
            mtime=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            data=encoded,
        )
        return (abs_str, asdict(entry), None)
    except Exception as exc:  # noqa: BLE001
        return (abs_str, None, str(exc))


def cmd_bundle(args: argparse.Namespace) -> int:
    files = iter_input_files(args.paths, args.recursive)
    if not files:
        log.error("No input files found.")
        return 1

    root = Path(args.paths[0]) if len(args.paths) == 1 and Path(args.paths[0]).is_dir() else None
    tasks = []
    for f in files:
        rel = f.relative_to(root).as_posix() if root else f.name
        tasks.append((str(f), rel, args.encoding, args.compress))

    log.info("Bundling %d file(s) into vault (%s, compress=%s)", len(tasks), args.encoding, args.compress)
    entries: List[dict] = []
    fail_count = 0
    with Timer() as t, concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        for abs_path, entry, err in pool.map(_bundle_one, tasks):
            if entry is not None:
                entries.append(entry)
            else:
                fail_count += 1
                log.error("FAIL %s: %s", abs_path, err)

    vault = {
        "vault_format": VAULT_FORMAT_VERSION,
        "tool": "EvidenceVault",
        "tool_version": VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "case_name": args.case,
        "file_count": len(entries),
        "total_raw_bytes": sum(e["size"] for e in entries),
        "files": sorted(entries, key=lambda e: e["path"]),
    }

    out_path = Path(args.output)
    ensure_parent(out_path)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(vault, fh, indent=None if args.minify else 2)

    log.info(
        "Vault written: %s (%d files, %d failed, %s raw -> %.2fs)",
        out_path, len(entries), fail_count, human_size(vault["total_raw_bytes"]), t.elapsed,
    )
    return 0 if fail_count == 0 else 2


def _load_vault(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def cmd_verify(args: argparse.Namespace) -> int:
    vault = _load_vault(args.vault_file)
    mismatches = 0
    for entry in vault.get("files", []):
        try:
            payload = ENCODINGS[entry["encoding"]]["decode"](entry["data"].encode("ascii"))
            if entry.get("compressed"):
                payload = zlib.decompress(payload)
            actual = hashlib.sha256(payload).hexdigest()
            if actual != entry["sha256"]:
                mismatches += 1
                log.error("MISMATCH %s (expected %s, got %s)", entry["path"], entry["sha256"], actual)
            else:
                log.debug("OK %s", entry["path"])
        except Exception as exc:  # noqa: BLE001
            mismatches += 1
            log.error("ERROR verifying %s: %s", entry["path"], exc)

    total = len(vault.get("files", []))
    log.info("Verified %d/%d files OK (%d mismatch/error)", total - mismatches, total, mismatches)
    return 0 if mismatches == 0 else 3


def cmd_extract(args: argparse.Namespace) -> int:
    vault = _load_vault(args.vault_file)
    out_root = Path(args.output)
    ok_count, mismatches = 0, 0
    for entry in vault.get("files", []):
        try:
            payload = ENCODINGS[entry["encoding"]]["decode"](entry["data"].encode("ascii"))
            if entry.get("compressed"):
                payload = zlib.decompress(payload)
            actual = hashlib.sha256(payload).hexdigest()
            if actual != entry["sha256"]:
                mismatches += 1
                log.error("HASH MISMATCH on extract: %s", entry["path"])
                if not args.force:
                    continue
            dest = out_root / entry["path"]
            ensure_parent(dest)
            dest.write_bytes(payload)
            ok_count += 1
        except Exception as exc:  # noqa: BLE001
            log.error("FAIL extracting %s: %s", entry["path"], exc)

    log.info("Extracted %d file(s) to %s (%d hash mismatches)", ok_count, out_root, mismatches)
    return 0 if mismatches == 0 else 3


# --------------------------------------------------------------------------- #
# hash -- chain-of-custody manifest generation
# --------------------------------------------------------------------------- #


def cmd_hash(args: argparse.Namespace) -> int:
    files = iter_input_files(args.paths, args.recursive)
    if not files:
        log.error("No input files found.")
        return 1

    rows = []
    with Timer() as t:
        for f in files:
            stat = f.stat()
            rows.append({
                "path": str(f),
                "size_bytes": stat.st_size,
                "modified_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
                "sha256": hash_file(f, "sha256"),
                "md5": hash_file(f, "md5") if args.md5 else "",
            })

    if args.output:
        out_path = Path(args.output)
        ensure_parent(out_path)
        if out_path.suffix.lower() == ".json":
            with open(out_path, "w", encoding="utf-8") as fh:
                json.dump({
                    "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "tool": "EvidenceVault",
                    "file_count": len(rows),
                    "files": rows,
                }, fh, indent=2)
        else:
            with open(out_path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
        log.info("Manifest written: %s (%d files, %.2fs)", out_path, len(rows), t.elapsed)
    else:
        for r in rows:
            print(f"{r['sha256']}  {r['path']}")

    return 0


# --------------------------------------------------------------------------- #
# rename -- safe, template-driven batch rename with an audit trail
# --------------------------------------------------------------------------- #

TOKEN_RE = re.compile(r"\{(name|ext|n(?::0\d+d)?|hash|date|time|parent)\}")


def _build_new_name(f: Path, index: int, pattern: str, case: str, hash_len: int) -> str:
    stem, ext = os.path.splitext(f.name)
    short_hash = hash_file(f, "sha256")[:hash_len] if "{hash}" in pattern else ""
    now = datetime.now()

    def repl(m: "re.Match") -> str:
        token = m.group(1)
        if token.startswith("n"):
            if ":" in token:
                fmt_spec = token.split(":")[1]  # e.g. 04d
                return format(index, fmt_spec)
            return str(index)
        return {
            "name": stem,
            "ext": ext,
            "hash": short_hash,
            "date": now.strftime("%Y%m%d"),
            "time": now.strftime("%H%M%S"),
            "parent": f.parent.name,
        }[token]

    new_name = TOKEN_RE.sub(repl, pattern)
    if "{ext}" not in pattern and not os.path.splitext(new_name)[1]:
        new_name += ext  # never silently drop the extension
    if case == "lower":
        new_name = new_name.lower()
    elif case == "upper":
        new_name = new_name.upper()
    elif case == "title":
        new_name = new_name.title()
    return sanitize_filename(new_name)


def cmd_rename(args: argparse.Namespace) -> int:
    root = Path(args.path)
    if not root.exists():
        log.error("Path does not exist: %s", root)
        return 1

    files = iter_input_files([str(root)], args.recursive) if root.is_dir() else [root]
    files.sort()

    audit_rows = []
    plan: List[Tuple[Path, Path]] = []
    for idx, f in enumerate(files, start=args.start):
        new_name = _build_new_name(f, idx, args.pattern, args.case, args.hash_length)
        dest = f.with_name(new_name)
        if dest.exists() and dest != f:
            base, ext = os.path.splitext(new_name)
            dest = f.with_name(f"{base}_{idx}{ext}")
        plan.append((f, dest))

    collisions = len(plan) - len({d for _, d in plan})
    if collisions:
        log.warning("%d destination-name collisions detected -- review before running for real", collisions)

    for src, dest in plan:
        audit_rows.append({"original": str(src), "renamed_to": str(dest)})
        if args.dry_run:
            log.info("[DRY-RUN] %s -> %s", src, dest.name)
        else:
            ensure_parent(dest)
            src.rename(dest)
            log.debug("%s -> %s", src, dest.name)

    if args.folders and root.is_dir() and not args.dry_run:
        # Rename subfolders deepest-first so paths above them stay valid, using
        # a simpler, extension-free version of the same template.
        subdirs = sorted([d for d in root.rglob("*") if d.is_dir()], key=lambda d: len(d.parts), reverse=True)
        for idx, d in enumerate(subdirs, start=args.start):
            simple_pattern = args.pattern.replace("{ext}", "")
            new_dir_name = sanitize_filename(_apply_folder_pattern(d, idx, simple_pattern, args.case))
            dest_dir = d.with_name(new_dir_name)
            if dest_dir != d and not dest_dir.exists():
                audit_rows.append({"original": str(d), "renamed_to": str(dest_dir)})
                d.rename(dest_dir)
                log.debug("[folder] %s -> %s", d, dest_dir.name)

    if args.audit_log:
        out_path = Path(args.audit_log)
        ensure_parent(out_path)
        with open(out_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["original", "renamed_to"])
            writer.writeheader()
            writer.writerows(audit_rows)
        log.info("Rename audit trail written: %s (%d entries)", out_path, len(audit_rows))

    log.info("%s %d item(s)%s", "Would rename" if args.dry_run else "Renamed", len(plan),
              " (dry-run, nothing changed)" if args.dry_run else "")
    return 0


def _apply_folder_pattern(d: Path, index: int, pattern: str, case: str) -> str:
    now = datetime.now()

    def repl(m: "re.Match") -> str:
        token = m.group(1)
        if token.startswith("n"):
            if ":" in token:
                return format(index, token.split(":")[1])
            return str(index)
        return {
            "name": d.name,
            "hash": "",
            "date": now.strftime("%Y%m%d"),
            "time": now.strftime("%H%M%S"),
            "parent": d.parent.name,
        }.get(token, "")

    name = TOKEN_RE.sub(repl, pattern).strip("_- ")
    return name or d.name


# --------------------------------------------------------------------------- #
# sort -- organize a folder's contents after (or instead of) renaming
# --------------------------------------------------------------------------- #


def _category_for(f: Path) -> str:
    ext = f.suffix.lower()
    for category, exts in EXT_CATEGORIES.items():
        if ext in exts:
            return category
    return "other"


def cmd_sort(args: argparse.Namespace) -> int:
    root = Path(args.path)
    files = iter_input_files([str(root)], args.recursive)
    if not files:
        log.error("No input files found.")
        return 1

    out_root = Path(args.output) if args.output else root
    moved = 0
    for f in files:
        if args.by == "ext":
            bucket = f.suffix.lower().lstrip(".") or "no_extension"
        elif args.by == "category":
            bucket = _category_for(f)
        elif args.by == "date":
            bucket = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m")
        else:  # encoding
            bucket = EXT_TO_ENCODING.get(f.suffix.lstrip("."), "unencoded")

        dest = out_root / bucket / f.name
        if dest == f:
            continue
        if dest.exists():
            base, ext = os.path.splitext(f.name)
            dest = out_root / bucket / f"{base}_{int(time.time()*1000)}{ext}"

        if args.dry_run:
            log.info("[DRY-RUN] %s -> %s", f, dest)
        else:
            ensure_parent(dest)
            shutil.move(str(f), str(dest))
            log.debug("%s -> %s", f, dest)
        moved += 1

    log.info("%s %d file(s) into %s", "Would sort" if args.dry_run else "Sorted", moved, out_root)
    return 0


# --------------------------------------------------------------------------- #
# CLI wiring
# --------------------------------------------------------------------------- #


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose (debug) logging")
    p.add_argument("--log-file", help="Also write logs to this file (audit trail)")
    p.add_argument("--timeout", type=float, default=None,
                   help="Reserved: abort the operation after N seconds (best-effort)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evidencevault",
        description="EvidenceVault -- fast batch encoding, bundling, renaming and "
                    "sorting for files, folders and images. Cross-platform, zero dependencies.",
    )
    parser.add_argument("--version", action="version", version=f"EvidenceVault {VERSION}")
    parser.add_argument("--no-banner", action="store_true", help="Skip the startup banner")
    parser.add_argument("-q", "--quiet", action="store_true", help="Alias for --no-banner")
    sub = parser.add_subparsers(dest="command", required=True)

    enc_choices = list(ENCODINGS.keys())

    # encode
    p = sub.add_parser("encode", help="Batch-encode files/folders/images")
    p.add_argument("paths", nargs="+", help="File(s) and/or folder(s) to encode")
    p.add_argument("-e", "--encoding", choices=enc_choices, default="base64")
    p.add_argument("-r", "--recursive", action="store_true", help="Recurse into folders")
    p.add_argument("-o", "--output", help="Output directory (mirrors input structure)")
    p.add_argument("--compress", action="store_true", help="zlib-compress before encoding (smaller output)")
    p.add_argument("--workers", type=int, default=os.cpu_count() or 4, help="Parallel worker processes")
    _add_common(p)
    p.set_defaults(func=cmd_encode)

    # decode
    p = sub.add_parser("decode", help="Batch-decode files previously produced by 'encode'")
    p.add_argument("paths", nargs="+", help="File(s) and/or folder(s) to decode")
    p.add_argument("-e", "--encoding", choices=enc_choices, default=None,
                   help="Force a codec; default is auto-detect from file extension")
    p.add_argument("-r", "--recursive", action="store_true")
    p.add_argument("-o", "--output", help="Output directory (mirrors input structure)")
    p.add_argument("--decompress", action="store_true", help="zlib-decompress after decoding")
    p.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    _add_common(p)
    p.set_defaults(func=cmd_decode)

    # bundle
    p = sub.add_parser("bundle", help="Compile files/folders into ONE encoded vault file")
    p.add_argument("paths", nargs="+", help="File(s) and/or folder(s) to bundle")
    p.add_argument("-e", "--encoding", choices=enc_choices, default="base64")
    p.add_argument("-r", "--recursive", action="store_true")
    p.add_argument("-o", "--output", required=True, help="Output vault file, e.g. case.vault.json")
    p.add_argument("--compress", action="store_true", help="zlib-compress each file before encoding")
    p.add_argument("--case", default=None, help="Case name/ID stored in the vault metadata")
    p.add_argument("--minify", action="store_true", help="Write compact JSON (smaller file, less readable)")
    p.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    _add_common(p)
    p.set_defaults(func=cmd_bundle)

    # extract
    p = sub.add_parser("extract", help="Restore all original files from a vault")
    p.add_argument("vault_file", help="Path to a .vault.json file")
    p.add_argument("-o", "--output", required=True, help="Directory to restore files into")
    p.add_argument("--force", action="store_true", help="Extract even if a hash mismatch is detected")
    _add_common(p)
    p.set_defaults(func=cmd_extract)

    # verify
    p = sub.add_parser("verify", help="Check every file's SHA-256 inside a vault without extracting")
    p.add_argument("vault_file", help="Path to a .vault.json file")
    _add_common(p)
    p.set_defaults(func=cmd_verify)

    # hash
    p = sub.add_parser("hash", help="Generate a chain-of-custody hash manifest (SHA-256 [+MD5])")
    p.add_argument("paths", nargs="+")
    p.add_argument("-r", "--recursive", action="store_true")
    p.add_argument("-o", "--output", help="Write manifest as .csv or .json (default: print to stdout)")
    p.add_argument("--md5", action="store_true", help="Also compute MD5 (in addition to SHA-256)")
    _add_common(p)
    p.set_defaults(func=cmd_hash)

    # rename
    p = sub.add_parser("rename", help="Batch-rename files (and optionally folders) with a safe template")
    p.add_argument("path", help="File or folder to rename")
    p.add_argument("-r", "--recursive", action="store_true", help="Recurse into subfolders")
    p.add_argument("--pattern", default="{name}_{n:04d}{ext}",
                   help="Template tokens: {name} {ext} {n} {n:04d} {hash} {date} {time} {parent}")
    p.add_argument("--start", type=int, default=1, help="Starting index for {n}")
    p.add_argument("--case", choices=["none", "lower", "upper", "title"], default="none")
    p.add_argument("--hash-length", type=int, default=8, help="Characters of SHA-256 to use for {hash}")
    p.add_argument("--folders", action="store_true", help="Also rename subfolders (deepest-first)")
    p.add_argument("--dry-run", action="store_true", help="Preview only -- never touches disk")
    p.add_argument("--audit-log", help="Write an original->renamed CSV audit trail")
    _add_common(p)
    p.set_defaults(func=cmd_rename)

    # sort
    p = sub.add_parser("sort", help="Organize a folder's files into subfolders")
    p.add_argument("path", help="Folder to sort")
    p.add_argument("-r", "--recursive", action="store_true")
    p.add_argument("--by", choices=["ext", "category", "date", "encoding"], default="category")
    p.add_argument("-o", "--output", help="Destination root (default: sort in place)")
    p.add_argument("--dry-run", action="store_true")
    _add_common(p)
    p.set_defaults(func=cmd_sort)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    print_banner()  # shown on every startup/restart; auto-skipped for non-TTY/--no-banner
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(getattr(args, "verbose", False), getattr(args, "log_file", None))
    try:
        return args.func(args)
    except KeyboardInterrupt:
        log.error("Interrupted by user.")
        return 130
    except Exception as exc:  # noqa: BLE001 -- top-level safety net, always exit cleanly
        log.error("Unhandled error: %s", exc, exc_info=getattr(args, "verbose", False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
