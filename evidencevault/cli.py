"""Provide direct commands and a guided operator menu."""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

from . import VERSION
from .audit import AuditStore, load_run
from .core import (
    CODECS, DEFAULT_WORKERS, HASH_ALGOS, FileResult, IntegrityError, RunResult,
    VaultError, check_output_separate, collect_sources, reject_symlinks,
)
from .operations import hash_files, organize_files, save_manifest, transform_files
from .report import create_report
from .vault import (
    DEFAULT_MAX_FILE_BYTES, DEFAULT_MAX_TOTAL_BYTES, check_vault, create_vault, extract_vault,
)

# --------------------------------------------------------------------------- #
# Startup banner -- terminal-only, cyberpunk/retro-terminal vault aesthetic.
# Printed exactly once per process: main() can recurse (guided_menu() calls
# main() again for a dry-run preview, then again to actually run), so a plain
# "print at the top of main()" would show it 2-3 times per wizard session.
# The module-level _BANNER_SHOWN guard is what keeps it to a single showing
# at actual program startup, however many times main() is re-entered after.
# --------------------------------------------------------------------------- #

_BANNER_SHOWN = False

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
    "MOUNTING CASE MODULES",
    "VAULT INTEGRITY: NOMINAL",
]


def _banner_suppressed(arguments: list[str]) -> bool:
    if os.environ.get("NO_COLOR") is not None or os.environ.get("EVIDENCEVAULT_NO_BANNER") is not None:
        return True
    return any(flag in arguments for flag in ("--no-banner", "-q", "--quiet"))


def _c(text: str, color: str, use_color: bool) -> str:
    return _ANSI[color] + text + _ANSI["reset"] if use_color else text


def print_banner(arguments: list[str], animate: bool = True) -> None:
    """Show the startup banner at most once per process. Silently skipped on
    non-TTY output, when NO_COLOR/EVIDENCEVAULT_NO_BANNER is set, or when
    --no-banner/-q/--quiet is passed -- so piping/scripting output, and every
    later call() once the wizard is already running, stay untouched."""
    global _BANNER_SHOWN
    if _BANNER_SHOWN or _banner_suppressed(arguments):
        return
    try:
        if not sys.stdout.isatty():
            return
    except Exception:  # noqa: BLE001
        return
    _BANNER_SHOWN = True

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
            print(_c("[ EVIDENCEVAULT ]".center(width), "green", use_color))

        rule = "═" * min(width - 1, 64)
        print(_c(rule.center(width), "grey", use_color))
        tagline = "RETRO-TERMINAL FORENSICS UNIT // COLLECT · VERIFY · HASH · RENAME · SORT"
        print(_c(tagline[: width - 1].center(width - 1), "cyan", use_color))
        print(_c(("build v" + VERSION).center(width - 1), "grey", use_color))
        print(_c(rule.center(width), "grey", use_color))

        if animate and width >= 66:
            for line in _BOOT_LINES:
                msg = "[ " + line
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


def positive(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("Use a positive whole number.")
    return number


def worker_count(value: str) -> int:
    number = positive(value)
    if number > 32:
        raise argparse.ArgumentTypeError("Use from 1 to 32 workers.")
    return number


def common(parser, case_style: bool = False) -> None:
    parser.add_argument("--case-name", dest="case_name", default="", help="Case name or identifier.")
    if not case_style:
        parser.add_argument("--case", dest="case_name", help="Alias for --case-name.")
    parser.add_argument("--operator", default="", help="Name to record for this operation.")
    parser.add_argument("--workers", type=worker_count, default=DEFAULT_WORKERS, help="File workers, from 1 to 32. Default: %(default)s.")
    parser.add_argument("--db", help="SQLite audit database. A case package includes one by default.")
    parser.add_argument("--report", help="Write an offline HTML report to a new file.")
    parser.add_argument("--log-file", help="Write command messages to this log file.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show technical error details.")


def limits(parser) -> None:
    parser.add_argument("--max-file-bytes", type=positive, default=DEFAULT_MAX_FILE_BYTES, help="Maximum restored file size. Default: 2 GiB.")
    parser.add_argument("--max-total-bytes", type=positive, default=DEFAULT_MAX_TOTAL_BYTES, help="Maximum archive output size. Default: 20 GiB.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evidencevault",
        description="Create case packages, check file contents, and organize working copies.",
        epilog="Run without a command in a terminal to open the guided menu.",
    )
    parser.add_argument("--version", action="version", version="EvidenceVault " + VERSION)
    parser.add_argument("--no-banner", "-q", "--quiet", action="store_true", help="Skip the startup logo. It is also skipped automatically when output is piped or redirected.")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("wizard", help="Open the guided operator menu.")

    for name, description in (
        ("collect", "Create a ZIP package, audit database, inventory, and HTML report."),
        ("bundle", "Create a ZIP or JSON archive from files."),
        ("hash", "Create a file inventory with hashes."),
        ("encode", "Create encoded working copies."),
        ("decode", "Restore encoded working copies."),
    ):
        sub = commands.add_parser(name, help=description, description=description)
        sub.add_argument("paths", nargs="+", help="Source file or folder paths.")
        sub.add_argument("-r", "--recursive", action="store_true", default=name == "collect", help="Include subfolders. Collect includes them by default.")
        sub.add_argument("-o", "--output", required=name in ("collect", "bundle", "encode", "decode"), help="New output file or folder.")
        common(sub)
        if name in ("collect", "bundle"):
            sub.add_argument("--format", choices=("zip", "json"), default="zip", help="Archive format. Default: ZIP.")
            sub.add_argument("--hash-algo", choices=HASH_ALGOS, default="sha256", help="File hash algorithm.")
            sub.add_argument("-e", "--encoding", choices=tuple(CODECS), default="base64", help="JSON payload encoding.")
            sub.add_argument("--compress", action="store_true", help="Compress JSON payloads.")
            sub.add_argument("--compression", type=int, choices=range(1, 10), default=6, help="ZIP compression level, from 1 to 9. Default: 6.")
            sub.add_argument("--minify", action="store_true", help="Use compact JSON.")
            if name == "collect":
                limits(sub)
        elif name == "hash":
            sub.add_argument("--algo", choices=HASH_ALGOS, default="sha256", help="File hash algorithm.")
            sub.add_argument("--md5", action="store_true", help="Add a legacy MD5 hash in the same read.")
        else:
            sub.add_argument("-e", "--encoding", choices=tuple(CODECS), default=None if name == "decode" else "base64", help="Payload encoding. Decode can use the file extension.")
            sub.add_argument("--decompress" if name == "decode" else "--compress", action="store_true", help="Use zlib compression.")
            sub.add_argument("--max-file-bytes", type=positive, default=DEFAULT_MAX_FILE_BYTES, help="Maximum decoded size. Default: 2 GiB.")

    for name, description in (
        ("verify", "Check archive paths, file sizes, and file hashes."),
        ("extract", "Restore checked files into new output paths."),
    ):
        sub = commands.add_parser(name, help=description, description=description)
        sub.add_argument("vault_file", help="ZIP or JSON case archive.")
        if name == "extract":
            sub.add_argument("-o", "--output", required=True, help="Output folder. Existing files are never replaced.")
        common(sub)
        limits(sub)

    for name, description in (
        ("rename", "Create working copies with consistent file names."),
        ("sort", "Create working copies in folders by file type or date."),
    ):
        sub = commands.add_parser(name, help=description, description=description)
        sub.add_argument("path", help="Source file or folder.")
        sub.add_argument("-o", "--output", help="Folder for the working copies.")
        sub.add_argument("-r", "--recursive", action="store_true", help="Include subfolders.")
        sub.add_argument("--dry-run", action="store_true", help="Show the plan. Do not write files or records.")
        sub.add_argument("--in-place", action="store_true", help="Change source paths. Requires an audit database outside the source.")
        common(sub, case_style=name == "rename")
        if name == "rename":
            sub.add_argument("--pattern", default="{name}_{n:04d}{ext}", help="Name template. Default: %(default)s.")
            sub.add_argument("--start", type=positive, default=1, help="First file number.")
            sub.add_argument("--hash-length", type=positive, choices=range(1, 65), default=8, help="Hash characters in a file name.")
            sub.add_argument("--folders", action="store_true", help="Rename folders in the working copy too.")
            sub.add_argument("--case", dest="case_style", choices=("none", "lower", "upper", "title"), default="none", help="File name letter case.")
        else:
            sub.add_argument("--by", choices=("category", "ext", "date", "encoding"), default="category", help="Folder rule. Default: category.")

    sub = commands.add_parser("report", help="Create an HTML report from an archive or a saved run.")
    sub.add_argument("vault_file", nargs="?", help="Optional archive to check.")
    sub.add_argument("-o", "--output", required=True, help="New HTML report file.")
    sub.add_argument("--db", help="Database with a saved run.")
    sub.add_argument("--run-id", default="", help="Saved run identifier. Default: latest complete run.")
    sub.add_argument("--workers", type=worker_count, default=DEFAULT_WORKERS)
    limits(sub)
    return parser


def select_option(label: str, options: tuple) -> str:
    """Show names and accept a number. Keep the first option as the default."""
    print("\n" + label)
    for number, (value, name) in enumerate(options, start=1):
        print(str(number) + "  " + name)
    while True:
        choice = input("Select a number [1]: ").strip() or "1"
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1][0]
        print("Select a listed number.", file=sys.stderr)


def guided_menu() -> int:
    if not sys.stdin.isatty():
        print("The guided menu requires a terminal. Use --help for direct commands.", file=sys.stderr)
        return 1
    print("\nEvidenceVault " + VERSION)
    actions = (
        ("collect", "Prepare a case package"), ("verify", "Check a case package"),
        ("extract", "Restore checked files"), ("hash", "Create a file inventory"),
        ("sort", "Organize working copies"), ("rename", "Rename working copies"),
        ("report", "Create a report from a saved run"), ("bundle", "Create an archive"),
        ("encode", "Encode working copies"), ("decode", "Decode working copies"),
    )
    for number, (_, label) in enumerate(actions, start=1):
        print(str(number) + "  " + label)
    print("0  Exit")
    try:
        choice = input("\nSelect an action [1]: ").strip() or "1"
        if choice == "0":
            return 0
        names = {str(number): action for number, (action, _) in enumerate(actions, start=1)}
        if choice not in names:
            print("Select a number from 0 to " + str(len(actions)) + ".", file=sys.stderr)
            return 1
        action = names[choice]
        label = "Database path" if action == "report" else ("Archive path" if action in ("verify", "extract") else "Source path")
        entered = input(label + ": ").strip()
        if not entered:
            print("Enter a source path.", file=sys.stderr)
            return 1
        source = str(Path(entered).expanduser())
        arguments = [action, "--db", source] if action == "report" else [action, source]
        if action != "verify":
            default = {
                "collect": "case_output", "extract": "restored_files", "hash": "manifest.json",
                "sort": "sorted_files", "rename": "renamed_files", "report": "report.html",
                "bundle": "case.vault.zip", "encode": "encoded_files", "decode": "decoded_files",
            }[action]
            output = str(Path(input("Output path [" + default + "]: ").strip() or default).expanduser())
            arguments += ["-o", output]
        if action in ("collect", "hash", "sort", "rename", "bundle", "encode", "decode"):
            if action != "collect":
                arguments.append("-r")
            arguments += ["--case-name", input("Case name [optional]: ").strip()]
            arguments += ["--operator", input("Operator name [optional]: ").strip()]
        if action == "bundle":
            container = select_option("Archive format", (("zip", "ZIP"), ("json", "JSON for a small case")))
            arguments += ["--format", container]
        if action in ("encode", "decode"):
            codecs = tuple((name, name) for name in CODECS)
            if action == "decode":
                codecs = (("auto", "Use the file extension"),) + codecs
            encoding = select_option("File encoding", codecs)
            if encoding != "auto":
                arguments += ["--encoding", encoding]
            question = "Was zlib compression used [y/N]: " if action == "decode" else "Compress before encoding [y/N]: "
            if input(question).strip().lower() in ("y", "yes"):
                arguments.append("--decompress" if action == "decode" else "--compress")
        if action == "sort":
            rule = select_option("Folder rule", (("category", "File category"), ("ext", "File extension"),
                                               ("date", "Modification month"), ("encoding", "File encoding")))
            arguments += ["--by", rule]
        if action == "rename":
            pattern = input("File name template [EVID_{n:04d}{ext}]: ").strip() or "EVID_{n:04d}{ext}"
            arguments += ["--pattern", pattern]
        if action in ("sort", "rename"):
            print("\nCheck the proposed file paths:")
            code = main(arguments + ["--dry-run"])
            if code:
                return code
        print("\nAction: " + action)
        print("Source: " + source)
        if action != "verify":
            print("Output: " + output)
        if input("Press Enter to start. Type cancel to stop: ").strip():
            print("The operation was cancelled.")
            return 0
        return main(arguments)
    except (EOFError, KeyboardInterrupt):
        print("\nThe operation was cancelled.")
        return 130


def run_operation(args, result: RunResult, audit) -> None:
    action = args.command
    if action in ("verify", "extract"):
        if action == "verify":
            check_vault(Path(args.vault_file), result, args.workers, args.max_file_bytes, args.max_total_bytes)
        else:
            extract_vault(Path(args.vault_file), Path(args.output), result, args.max_file_bytes, args.max_total_bytes)
        return
    paths = args.paths if hasattr(args, "paths") else [args.path]
    sources = args.sources
    if action in ("collect", "bundle"):
        output = Path(args.output)
        destination = output / "case.vault.zip" if action == "collect" else output
        if action == "collect" and args.format != "zip":
            raise VaultError("Collect uses ZIP. Use bundle for a JSON archive.")
        if action == "collect":
            sizes = [source.path.stat().st_size for source in sources]
            if any(size > args.max_file_bytes for size in sizes) or sum(sizes) > args.max_total_bytes:
                raise VaultError("The source files exceed the case size limits.")
        try:
            create_vault(
                sources, destination, result, args.format, args.hash_algo, args.encoding,
                args.compress, args.workers, args.compression, args.minify,
            )
        except Exception:
            for row in result.files:
                row.status = "error"
                row.note = "The archive was not published."
            raise
        if action == "collect":
            checked = RunResult("verify")
            check_vault(destination, checked, args.workers, args.max_file_bytes, args.max_total_bytes)
            if any(row.status != "ok" for row in checked.files):
                result.files = checked.files
                result.notes.append("The archive was created but its check failed.")
            result.finish()
            save_manifest(output / "manifest.json", result)
            result.notes.extend(checked.notes)
        return
    if action == "hash":
        extra = hash_files(sources, result, args.algo, args.md5, args.workers)
        if args.output:
            result.finish()
            save_manifest(Path(args.output), result, extra)
        else:
            for row in result.files:
                if row.status == "ok":
                    print(row.digest + "  " + row.path)
        return
    if action in ("encode", "decode"):
        transform_files(sources, Path(args.output), result, args, action == "decode")
        return
    output = Path(args.output or (args.path if args.in_place else args.command + "_files"))
    organize_files(sources, output, result, args, audit)


def main(arguments: list[str] | None = None) -> int:
    print_banner(sys.argv[1:] if arguments is None else arguments)  # once per process; see print_banner()
    parser = build_parser()
    args = parser.parse_args(arguments)
    if not args.command:
        if sys.stdin.isatty():
            return guided_menu()
        parser.print_help()
        return 0
    if args.command == "wizard":
        return guided_menu()
    if args.command == "report":
        try:
            if bool(args.vault_file) == bool(args.db):
                raise VaultError("Select one archive or one audit database.")
            if args.db:
                result = load_run(Path(args.db), args.run_id)
            else:
                result = RunResult("verify")
                check_vault(Path(args.vault_file), result, args.workers, args.max_file_bytes, args.max_total_bytes)
                result.finish()
            create_report(result, Path(args.output))
            print("Report: " + args.output)
            return result.exit_code
        except Exception as error:
            print("Error: " + str(error), file=sys.stderr)
            return 3 if isinstance(error, IntegrityError) else 1

    result = RunResult(args.command, case=args.case_name or "", operator=args.operator)
    audit = None
    report_path = args.report
    database_path = args.db
    paths = args.paths if hasattr(args, "paths") else ([args.path] if hasattr(args, "path") else [args.vault_file])
    outputs_ready = False
    try:
        dry_run = getattr(args, "dry_run", False)
        if dry_run and any((database_path, report_path, args.log_file)):
            raise VaultError("A dry run does not write a database, report, or log.")
        if args.command == "collect":
            database_path = database_path or str(Path(args.output) / "audit.sqlite3")
            report_path = report_path or str(Path(args.output) / "report.html")
            for name in ("case.vault.zip", "manifest.json"):
                if (Path(args.output) / name).exists():
                    raise VaultError("A case output already exists. Select a new output folder.")
        if args.command in ("rename", "sort"):
            if args.in_place and not database_path:
                raise VaultError("An in-place operation requires --db outside the source folder.")
            if args.in_place and args.output and args.command == "rename":
                raise VaultError("Do not combine rename --in-place with an output folder.")
            if args.in_place and getattr(args, "folders", False):
                raise VaultError("Folder renames require a working copy output folder.")
            if args.in_place and args.command == "sort" and not Path(args.path).is_dir():
                raise VaultError("An in-place sort requires a source folder.")
            if not args.in_place and not args.output and not dry_run:
                raise VaultError("Select an output folder with -o to create working copies.")
            if not database_path and not dry_run:
                database_path = str(Path(args.output) / "audit.sqlite3")
        outputs = [value for value in (database_path, report_path, args.log_file) if value]
        if hasattr(args, "output") and args.output and not getattr(args, "in_place", False):
            outputs.append(args.output)
        for value in outputs:
            check_output_separate(paths, Path(value))
        if report_path and Path(report_path).exists():
            raise VaultError("The HTML report already exists. Select a new report path.")
        if hasattr(args, "paths") or hasattr(args, "path"):
            args.sources = collect_sources(paths, args.recursive)
            for value in outputs:
                target = Path(value)
                if target.is_file() and any(os.path.samefile(target, source.path) for source in args.sources):
                    raise VaultError("An output record is a hard link to a source file.")
        if args.log_file:
            reject_symlinks(Path(args.log_file))
        outputs_ready = True
        handlers = [logging.StreamHandler()]
        if args.log_file:
            handlers.append(logging.FileHandler(args.log_file, encoding="utf-8"))
        logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING, handlers=handlers, force=True)
        if database_path:
            audit = AuditStore(Path(database_path))
            audit.start(result)
        algorithm = getattr(args, "hash_algo", getattr(args, "algo", "sha256"))
        if algorithm in ("md5", "sha1"):
            result.notes.append("This run uses a legacy hash. Use SHA-256 for a new case.")
        run_operation(args, result, audit)
    except KeyboardInterrupt:
        result.exit_code = 130
        result.notes.append("The operator stopped the run. Check any completed output files.")
    except Exception as error:
        status = "mismatch" if isinstance(error, IntegrityError) else "error"
        result.files.append(FileResult(path="Operation", status=status, note=str(error)))
        logging.debug("Command error", exc_info=True)
    finally:
        result.finish()
        if audit is not None:
            try:
                audit.finish(result)
            except Exception as error:
                result.files.append(FileResult(path=str(database_path), status="error", note=str(error)))
                result.finish()
        if outputs_ready and report_path and not getattr(args, "dry_run", False):
            try:
                create_report(result, Path(report_path))
            except Exception as error:
                result.files.append(FileResult(path=str(report_path), status="error", note=str(error)))
                result.finish()
                if audit is not None:
                    try:
                        audit.finish(result)
                    except Exception:
                        pass
        if audit is not None:
            audit.close()

    for row in result.files:
        if row.status in ("error", "mismatch"):
            print(row.status.capitalize() + ": " + row.path + ": " + row.note, file=sys.stderr)
        elif row.status == "planned":
            print(row.path + " -> " + row.destination)
    counts = Counter(row.status for row in result.files)
    if args.command != "hash" or args.output:
        print(
            "Files complete: " + str(counts["ok"]) + ". Planned: " + str(counts["planned"])
            + ". Errors: " + str(counts["error"] + counts["mismatch"]) + "."
        )
    if database_path and audit is not None:
        print("Audit database: " + database_path)
    if outputs_ready and report_path and Path(report_path).is_file():
        print("Report: " + report_path)
    return result.exit_code
