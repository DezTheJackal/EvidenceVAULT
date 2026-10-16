<p align="center">
  <img src="logo.svg" alt="EvidenceVault logo" width="240">
</p>

# EvidenceVault

**Version 1.1.2**

EvidenceVault helps an operator package, check, and organize local case files.
It uses Python and the standard library.
The file commands need no runtime packages and do not use the network.

Use it for working copies of incident response files, investigation notes, screenshots, and other collected material.
Keep the original evidence and separate collection records.

## Contents

- [Start here](#start-here)
- [The startup logo](#the-startup-logo)
- [The guided menu](#the-guided-menu)
- [Quick reference](#quick-reference)
- [Prepare a case with collect](#prepare-a-case-with-collect)
- [Check and restore a case](#check-and-restore-a-case)
- [Create archives with bundle](#create-archives-with-bundle)
- [Create a file inventory with hash](#create-a-file-inventory-with-hash)
- [Encode and decode working copies](#encode-and-decode-working-copies)
- [Rename working copies](#rename-working-copies)
- [Sort working copies](#sort-working-copies)
- [Reports and audit records](#reports-and-audit-records)
- [All options](#all-options)
- [Safety and resource limits](#safety-and-resource-limits)
- [Exit codes](#exit-codes)
- [Scope](#scope)
- [Tests, code guide, and demo](#tests-code-guide-and-demo)
- [Version history](#version-history)
- [Upgrade notes](#upgrade-notes)
- [Contributors and license](#contributors-and-license)
- [Dictionary](#dictionary) (each command, option, and term, with a definition and an example)

## Start here

### Linux, macOS, and Termux

Get the full repository.
The program uses small modules. Do not copy only the launcher file.

~~~bash
git clone https://github.com/DezTheJackal/EvidenceVAULT.git
cd EvidenceVAULT
python3 Evidencevault.py
~~~

The launcher name starts with a capital E.
Linux, macOS, and Termux file names are case sensitive.
Type the name exactly as shown.

On Termux, install Python first with `pkg install python`.
You can also start the package as a module:

~~~bash
python3 -m evidencevault
~~~

### Windows

Run this command in PowerShell on Windows 10 or Windows 11:

~~~powershell
irm https://raw.githubusercontent.com/DezTheJackal/EvidenceVAULT/main/install-windows.ps1 | iex
evidencevault
~~~

The installer downloads the complete main branch over HTTPS.
It reuses Python 3.11 or a newer version when available.
Otherwise, it installs Python 3.13 for the current user with WinGet.
If WinGet is unavailable or fails, it uses the Python 3.13.15 installer from python.org.
It checks that installer's SHA-256 value before it starts the installer.

The default folder is `%LOCALAPPDATA%\EvidenceVault`.
The installer creates a separate `.venv` environment and a `bin\evidencevault.cmd` command.
It adds the `bin` folder to the user PATH and the current terminal PATH.
It does not require a Git installation.
An existing install folder is not replaced.

To read the script before you run it, download it and run it as a file:

~~~powershell
irm https://raw.githubusercontent.com/DezTheJackal/EvidenceVAULT/main/install-windows.ps1 -OutFile install-windows.ps1
& .\install-windows.ps1 -InstallDir "$env:LOCALAPPDATA\EvidenceVault-1.1.2"
~~~

The script supports PowerShell 5.1 and PowerShell 7.
If a later terminal cannot find `evidencevault`, open a new terminal.

| Installer option | Meaning |
|---|---|
| `-InstallDir` | New install folder. Default: `%LOCALAPPDATA%\EvidenceVault`. |
| `-SourceRepo` | GitHub repository to download, as `owner/repo`. Default: `DezTheJackal/EvidenceVAULT`. |
| `-Revision` | `main`, or a full 40-character commit hash for an exact source version. |
| `-SourceDirectory` | Install from a local copy of the repository. No download occurs. |
| `-SkipPythonInstall` | Stop with an error if Python 3.11 or a newer version is missing. |
| `-NoPathUpdate` | Do not change the PATH. |

Use `-SourceRepo` only for a fork that you trust.
The installer runs the code that it downloads.

### Requirements

Python 3.8 or a newer version runs the source.
The Windows installer needs Python 3.11 or a newer version and installs it when needed.
The target systems are Linux, Windows, macOS, and Termux.

## The startup logo

A terminal run starts with the EvidenceVault logo: block letters, a vault door, and a short boot sequence.
The logo appears once for each program start.
The guided menu does not show it again for later steps.

The program skips the logo in these cases:

| Case | Result |
|---|---|
| Output goes to a pipe or a file. | No logo. Scripts see clean output. |
| You put `-q`, `--quiet`, or `--no-banner` before the command. | No logo. |
| The `NO_COLOR` variable is set. | No logo. |
| The `EVIDENCEVAULT_NO_BANNER` variable is set. | No logo. |
| The `EVIDENCEVAULT_NO_COLOR` variable is set. | The logo appears as plain text without color. |
| The terminal has fewer than 66 columns. | A short one-line logo. The boot sequence is skipped. |

Put the quiet option before the command name:

~~~bash
python3 Evidencevault.py -q hash ./case_files -r
~~~

The program rejects the option after the command name.
The quiet option hides only the logo. It does not hide the result summary.
On Windows, the program turns on terminal color by itself.

## The guided menu

The guided menu is the easiest way to start.
You do not need to remember options.
Start it in a terminal with no command, or use the `wizard` command:

~~~bash
python3 Evidencevault.py
python3 Evidencevault.py wizard
~~~

If input is not a terminal, the program shows help instead of a prompt.
The `wizard` command in that case prints a message and returns exit code 1.

The menu has ten actions:

| Number | Action | Command it runs |
|---|---|---|
| 1 | Prepare a case package | `collect` |
| 2 | Check a case package | `verify` |
| 3 | Restore checked files | `extract` |
| 4 | Create a file inventory | `hash` |
| 5 | Organize working copies | `sort` |
| 6 | Rename working copies | `rename` |
| 7 | Create a report from a saved run | `report` |
| 8 | Create an archive | `bundle` |
| 9 | Encode working copies | `encode` |
| 10 | Decode working copies | `decode` |
| 0 | Exit | None |

Press Enter at a prompt that shows `[1]` to accept the first choice.

The menu asks for these items, in this order:

1. The source path. Verify and extract ask for an archive path. Report asks for a database path.
2. The output path. Each action shows a default in square brackets.
3. The case name and the operator name. Both are optional. Verify, extract, and report skip them.
4. Action settings: archive format (bundle), codec and compression (encode and decode), folder rule (sort), or name template (rename).
5. A preview for rename and sort. The preview shows each planned path. It does not write files.
6. A final check. Press Enter to start. Type `cancel` to stop.

| Action | Default output |
|---|---|
| Collect | `case_output` |
| Extract | `restored_files` |
| Hash | `manifest.json` |
| Sort | `sorted_files` |
| Rename | `renamed_files` |
| Report | `report.html` |
| Bundle | `case.vault.zip` |
| Encode | `encoded_files` |
| Decode | `decoded_files` |

The menu includes subfolders for every action except verify, extract, and report.
Press Ctrl+C to stop. The program prints a cancel message and returns exit code 130.

## Quick reference

| Command | Result |
|---|---|
| `collect` | A checked ZIP case package, inventory, audit database, and HTML report. |
| `bundle` | A ZIP or JSON archive. |
| `verify` | A check of archive structure, file hashes, and file sizes. |
| `extract` | Checked files in new output paths. |
| `hash` | A file inventory in JSON or CSV, or hash lines in the terminal. |
| `encode` | Encoded working copies. |
| `decode` | Decoded working copies. |
| `rename` | Working copies with consistent names. |
| `sort` | Working copies in category, extension, date, or encoding folders. |
| `report` | An HTML report from an archive or a saved database run. |
| `wizard` | The guided menu. |

Which command do you need?

| You want to... | Use |
|---|---|
| Prepare a complete, checked case with records | `collect` |
| Make one portable file from some files | `bundle` |
| Prove that an archive still matches its manifest | `verify` |
| Get files back out of an archive | `extract` |
| List file hashes only | `hash` |
| Convert files to or from a text form | `encode` and `decode` |
| Give files a consistent naming scheme | `rename` |
| Put files into folders by type or date | `sort` |
| Make a report you can open in a browser | `report` |

Show help for any command:

~~~bash
python3 Evidencevault.py --help
python3 Evidencevault.py collect --help
python3 Evidencevault.py rename --help
python3 Evidencevault.py --version
~~~

## Prepare a case with collect

A hash is a value calculated from file contents.
A manifest lists file paths, sizes, hashes, and recorded times.

~~~bash
python3 Evidencevault.py collect ./case_files \
  -o ./case_output --case-name CASE-2026-0091 --operator "Your name"
~~~

This command includes subfolders.
It creates these files in the output folder:

| File | Purpose |
|---|---|
| `case.vault.zip` | Source file contents and their hash manifest. |
| `manifest.json` | A separate file inventory. |
| `audit.sqlite3` | Run details, file results, and operation records. |
| `report.html` | A local HTML report with file results and repeated hash groups. |

A good run prints a summary like this:

~~~text
Files complete: 4. Planned: 0. Errors: 0.
Audit database: case_output/audit.sqlite3
Report: case_output/report.html
~~~

The command checks the finished archive before it records a successful case.
Select a new output folder for each case package.
The folder must not contain `case.vault.zip` or `manifest.json`.

Collect always makes a ZIP archive.
Use `bundle` when you need a JSON archive.
Collect accepts `--hash-algo`, `--compression`, `--max-file-bytes`, and `--max-total-bytes`.

## Check and restore a case

~~~bash
python3 Evidencevault.py verify ./case_output/case.vault.zip
python3 Evidencevault.py extract ./case_output/case.vault.zip -o ./restored_files
~~~

The program checks manifest paths, file counts, sizes, and hashes.
It rejects an unsafe path or a destination collision before it writes a restored file.
It never replaces an existing output file.
Extract stops if any destination file already exists.

A file with a wrong hash or size does not become a finished output file.
Other valid files can complete. A partial result has a nonzero exit code.
This example shows a changed file:

~~~text
Mismatch: notes.txt: The file hash does not match the manifest.
Files complete: 3. Planned: 0. Errors: 1.
~~~

The exit code in that case is 3.
Both commands read ZIP and JSON archives.

## Create archives with bundle

ZIP is the default archive format.
It stores raw file bytes with compression.
The writer hashes the same bytes that enter the archive.

JSON is available for small, text-based transfers.
Its encoded payloads use more space.

~~~bash
python3 Evidencevault.py bundle ./case_files -r -o ./case.vault.zip
python3 Evidencevault.py bundle ./case_files -r --format json --compress -o ./case.vault.json
python3 Evidencevault.py bundle ./case_files -r --hash-algo blake2b --compression 9 -o ./case.vault.zip
~~~

Without `-r`, bundle includes only the files directly inside a source folder.
The output path must be new.

A ZIP archive holds each file under `files/` and a `manifest.json` entry.
A JSON archive holds the manifest and every encoded payload in one file.
The manifest has the case name, operator, hash algorithm, file count, and total size.

| Format | Best for | Limits |
|---|---|---|
| ZIP (default) | Any case size. | At most 100000 files. |
| JSON | Small, text-based transfers. | At most 16 MiB of raw file data in total. |

If you select several source folders, the archive keeps each folder name.
If two source paths still have the same logical destination, the program stops.
Source roots must have distinct names.

SHA-256 is the default hash.
BLAKE2b and BLAKE2s are also available.
MD5 and SHA-1 remain available for legacy use.
Use SHA-256 for a new case.
The program adds a note to the run record when you select MD5 or SHA-1.

## Create a file inventory with hash

An inventory lists each file with its size, time, and hash.

~~~bash
python3 Evidencevault.py hash ./case_files -r
python3 Evidencevault.py hash ./case_files -r -o ./manifest.json
python3 Evidencevault.py hash ./case_files -r --algo blake2b --md5 -o ./manifest.csv
~~~

Without `-o`, the command prints one `hash  path` line for each file.
It prints no summary in that case.
With `-o`, the extension decides the format: `.json` gives JSON, and any other extension gives CSV.

Each record has these fields: `path`, `size_bytes`, `modified_utc`, `algorithm`, `hash`, `status`, and `note`.
The `--md5` option adds an `md5` field from the same file read.
The terminal lines show only the main hash.

CSV exports protect file names that a spreadsheet could treat as formulas.
These displayed names have an apostrophe prefix.
JSON keeps the exact file names.

## Encode and decode working copies

A codec converts bytes to an encoded form and back.
Supported codecs are Base64, URL-safe Base64, Base32, Base16, Base85, ASCII85, and URL encoding.

~~~bash
python3 Evidencevault.py encode ./case_files -r -o ./encoded_files
python3 Evidencevault.py decode ./encoded_files -r -o ./decoded_files
~~~

Encode adds a codec extension to each file name.
Decode removes it, and it uses the extension to pick the codec.

| Codec name | File extension |
|---|---|
| `base64` (default for encode) | `.b64` |
| `base64url` | `.b64u` |
| `base32` | `.b32` |
| `base16` | `.hex` |
| `base85` | `.b85` |
| `ascii85` | `.a85` |
| `urlenc` | `.urlenc` |

Use `-e` to select a codec.
Use `--compress` for zlib compression before encoding.
Use `--decompress` to reverse that compression during decode.

If a file name has no codec extension, select the codec with `-e`.
Decode then adds `.decoded` to the output name.

~~~bash
python3 Evidencevault.py encode ./case_files -r -e base32 --compress -o ./encoded_files
python3 Evidencevault.py decode ./encoded_files -r --decompress -o ./decoded_files
python3 Evidencevault.py decode ./mystery_files -e base32 -o ./decoded_files
~~~

The hash in an encode or decode result describes the output contents.
ASCII85 and URL decoding accept at most 16 MiB of encoded input.

Encoding is not encryption.
Anyone with the encoded data can decode it.

## Rename working copies

Rename creates copies with new names.
It keeps the source paths unchanged.
It also creates an audit database in the output folder.

~~~bash
python3 Evidencevault.py rename ./case_files -r -o ./renamed_files \
  --pattern "EVID_{n:04d}_{hash}{ext}" --dry-run

python3 Evidencevault.py rename ./case_files -r -o ./renamed_files \
  --pattern "EVID_{n:04d}_{hash}{ext}"
~~~

A name template is called a pattern.
The default pattern is `{name}_{n:04d}{ext}`.

| Token | Meaning | Example result |
|---|---|---|
| `{name}` | Original name without the extension. | `notes` |
| `{ext}` | Original extension with its dot. | `.txt` |
| `{n}` | File number. Starts at `--start`. | `7` |
| `{n:04d}` | File number padded with zeros. | `0007` |
| `{hash}` | First characters of the SHA-256 hash. Set the length with `--hash-length`. | `72aeea18` |
| `{date}` | UTC date. | `20261016` |
| `{time}` | UTC time. | `063513` |
| `{parent}` | Name of the folder that holds the source file. | `logs` |

Only the number token supports a format such as `{n:04d}`.
If the pattern has no `{ext}` and the new name has no extension, the program keeps the original extension.
The new name must not contain a slash.
If two files get the same new path, the program stops before it writes anything.

More rename options:

| Option | Effect |
|---|---|
| `--start N` | First file number. Default: 1. |
| `--hash-length N` | Hash characters for `{hash}`, from 1 to 64. Default: 8. |
| `--case none\|lower\|upper\|title` | Letter case of the whole file name, including the extension. |
| `--folders` | Rename folders in the working copy too. Folders use the same pattern. `{ext}` and `{hash}` are empty for folders. |

Use `--case-name` for the case name on rename.
On rename, `--case` selects the letter case.

A dry run does not write files, a database, a report, or a log.
It prints one `path -> destination` line for each file.
Without `-o`, a dry run shows paths under `rename_files`.
Do not combine `--dry-run` with `--db`, `--report`, or `--log-file`.

An in-place action changes source paths.
Use it only on a working copy.
It requires a database outside the source folder.

~~~bash
python3 Evidencevault.py rename ./working_copy -r --in-place \
  --db ./records/audit.sqlite3 --pattern "EVID_{n:04d}{ext}"
~~~

In-place actions require hard link support and stay on one file system.
An in-place rename keeps each file in its current folder.
Do not combine `--in-place` with `-o` or `--folders`.
Folder renames require an output folder.

## Sort working copies

Sort creates copies in folders.
It keeps the source paths unchanged and creates an audit database in the output folder.
The original subfolder path stays below each new folder.

~~~bash
python3 Evidencevault.py sort ./case_files -r -o ./sorted_files --by category
python3 Evidencevault.py sort ./case_files -r -o ./sorted_files --by ext
python3 Evidencevault.py sort ./case_files -r -o ./sorted_files --by date --dry-run
~~~

| Rule (`--by`) | Folder names | Example |
|---|---|---|
| `category` (default) | The detected file kind. | `image/images/Screenshot.PNG` |
| `ext` | The lowercase extension, or `no_extension`. | `txt/notes.txt` |
| `date` | The UTC modification month. | `2026-10/notes.txt` |
| `encoding` | The codec name, or `unencoded`. | `base32/notes.txt.b32` |

The category names are `image`, `document`, `archive`, `audio`, `video`, `capture`, `encoded`, `database`, `executable`, and `other`.
The program checks known file signatures first.
It falls back to the extension.

Without `-o`, a dry run shows paths under `sort_files`.
An in-place sort moves files into folders inside the source folder.
It needs a source folder, not a single file, and it needs `--db`.

## Reports and audit records

Use `--db` to save a run.
Use `--report` to write its HTML report.

~~~bash
python3 Evidencevault.py verify ./case.vault.zip \
  --db ./records/audit.sqlite3 --report ./records/check.html

python3 Evidencevault.py report --db ./records/audit.sqlite3 -o ./saved_report.html
python3 Evidencevault.py report ./case.vault.zip -o ./fresh_report.html
~~~

A saved report uses the latest completed database run.
Use `--run-id` to select a specific run.
A fresh report checks the supplied archive.
Select a new report path. The program does not replace an existing file.

Reports include the case name, operator name, UTC run times, hashes, file results, and repeated hash groups.
The summary shows the count of groups of files that have the same contents.
They use local CSS.
They have no scripts, remote fonts, or network resources.
The report escapes all supplied text.
It has a print layout and a narrow-screen layout.

The file type result uses a small set of known file signatures.
It falls back to the extension.
It does not identify malware or prove the real file format.

The audit database is a SQLite file with three tables:

| Table | Content |
|---|---|
| `runs` | One row for each run: id, action, case name, operator, start and finish times, exit code, and the full result. |
| `files` | One row for each file result: path, destination, status, size, algorithm, and hash. |
| `events` | Time-stamped actions: `planned`, `complete`, and `error`. |

To list the runs, use the `sqlite3` tool or the Python `sqlite3` module:

~~~bash
sqlite3 ./case_output/audit.sqlite3 "select id, action, case_name, operator, exit_code from runs"
~~~

Rename and sort save a `planned` event before each file change.
They save a `complete` or `error` event afterward.

These records are not signed or protected against database edits.
A hash manifest alone is not a full chain-of-custody record.

Use `--log-file` to write command messages to a file.
Add `-v` to include technical error details.

## All options

### Options for the program

Put these before the command name.

| Option | Meaning |
|---|---|
| `-h`, `--help` | Show help and exit. |
| `--version` | Show the program version and exit. |
| `-q`, `--quiet`, `--no-banner` | Skip the startup logo. |

### Shared options

These options work on collect, bundle, hash, encode, decode, verify, extract, rename, and sort.

| Option | Meaning |
|---|---|
| `--case-name NAME` | Case name. On every command except rename, `--case NAME` is an alias. |
| `--operator NAME` | Operator name to record. |
| `--workers N` | File workers, from 1 to 32. Default: 4, or fewer on a small computer. |
| `--db PATH` | SQLite audit database. A new path. |
| `--report PATH` | HTML report to write. A new path. |
| `--log-file PATH` | File for command messages. |
| `-v`, `--verbose` | Show technical error details. |

### Source and output options

| Option | Commands | Meaning |
|---|---|---|
| `paths` | collect, bundle, hash, encode, decode | One or more source files or folders. |
| `path` | rename, sort | One source file or folder. |
| `vault_file` | verify, extract | A ZIP or JSON archive. |
| `vault_file` (optional) | report | An archive to check for a fresh report. |
| `-r`, `--recursive` | collect, bundle, hash, encode, decode, rename, sort | Include subfolders. Collect includes them by default. |
| `-o`, `--output PATH` | All except verify | A new output file or folder. Required for collect, bundle, encode, decode, extract, and report. |

### Options by command

| Command | Options |
|---|---|
| collect, bundle | `--format zip\|json`, `--hash-algo`, `-e/--encoding`, `--compress`, `--compression 1-9`, `--minify` |
| collect | `--max-file-bytes`, `--max-total-bytes` (collect always uses ZIP) |
| hash | `--algo`, `--md5` |
| encode | `-e/--encoding` (default `base64`), `--compress`, `--max-file-bytes` |
| decode | `-e/--encoding` (default: from the file extension), `--decompress`, `--max-file-bytes` |
| verify, extract | `--max-file-bytes`, `--max-total-bytes` |
| rename | `--pattern`, `--start`, `--hash-length`, `--case`, `--folders`, `--dry-run`, `--in-place` |
| sort | `--by category\|ext\|date\|encoding`, `--dry-run`, `--in-place` |
| report | `--db`, `--run-id`, `--workers`, `--max-file-bytes`, `--max-total-bytes` |

Hash algorithms: `sha256` (default), `blake2b`, `blake2s`, `sha1`, `md5`.
Codecs: `base64`, `base64url`, `base32`, `base16`, `base85`, `ascii85`, `urlenc`.

## Safety and resource limits

- Output paths must stay outside source folders, except for an explicit in-place action.
- The program rejects symbolic links and nonregular source files.
- Archive paths must be safe relative paths on Linux, Windows, and macOS.
- The program rejects duplicate paths, case collisions, and file-versus-folder collisions.
- Source files must keep the same identity, size, and change times during each read.
- Most file operations use 1 MiB memory blocks.
- An archive can list at most 100000 files.
- A ZIP manifest can use at most 16 MiB.
- A ZIP directory can use at most 64 MiB.
- A JSON archive can use at most 64 MiB.
- New JSON archives can contain at most 16 MiB of raw file data in total.
- ASCII85 and URL decoding accept at most 16 MiB of encoded input.
- Restored files have a default limit of 2 GiB each and 20 GiB in total.

Use `--max-file-bytes` and `--max-total-bytes` to change archive check limits.
These options accept whole byte counts.
Collect accepts the same limits.
Encode and decode accept `--max-file-bytes`.

Use `--workers` to select from one to 32 file workers.
The default is at most four workers.
The task queue holds at most two tasks per worker.
ZIP reads reuse one archive handle per worker.
Full source reads reuse one buffer per active task.
On Linux, large sequential reads can use an optional file system read hint.
Hash-based rename plans calculate their file hashes with the bounded workers.
The finished copy must still match its planned hash.
Sort plans for extensions, months, and encodings do not read source contents.
ZIP creation and in-place path changes run in sequence.
The default ZIP compression level is six.
Use `--compression` to select a level from one to nine.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | The requested operation completed. A dry-run plan can also return zero. |
| 1 | A report input or guided menu request failed. |
| 2 | An input, file operation, or output record failed. Command option errors also use two. |
| 3 | A file hash or payload size did not match. |
| 130 | The operator stopped the command. |

## Scope

EvidenceVault handles existing regular files.
It does not acquire a forensic disk image or recover deleted files.
It does not encrypt files, authenticate an operator, or sign a manifest.

Original modification times remain in the manifest.
Restored files have new file system times and permissions.
The package does not preserve empty folders, access controls, or extended attributes.

A completed case can contain a partial result if a later output record fails.
Check the exit code and report before you hand over a case.

## Tests, code guide, and demo

The CI workflow checks Linux, Windows, and macOS with several Python versions.

~~~bash
python3 -m compileall -q evidencevault Evidencevault.py tests
python3 -m unittest discover -s tests -v
~~~

Read [the code guide](docs/CODE_GUIDE.md) for a module map and a school presentation walkthrough.
Read [the contribution guide](CONTRIBUTING.md) for the code and writing rules.
Read [the benchmark guide](benchmarks/README.md) for measured planning results and their limits.

Create a complete dummy case and sample results for all ten operations.
From the repository folder, run:

~~~bash
python3 -m examples.build_demo -o ./demo_output
~~~

You can also start the script from the examples folder:

~~~bash
cd examples
python3 build_demo.py
~~~

The script uses the local package. No separate package installation is required.
Without `-o`, it creates `demo_output` in the current folder.
Use `-o` with a new folder for another run:

~~~bash
python3 build_demo.py -o ./another_demo
~~~

The output folder must be new.
Open `demo_output/case/report.html` to inspect the sample HTML report.
Read `demo_output/results.json` for the sample command results.
The sample files and events are synthetic.

## Version history

### 1.1.2

- Restored the startup logo. It appears once for each terminal start.
- Made the `-q`, `--quiet`, and `--no-banner` options work again.
- Changed the Windows installer and the CI check to use this repository by default.
- Added the `-SourceRepo` installer option.
- Rewrote the README with a full option reference and a dictionary.

### 1.1.1

- Fixed unsafe extraction paths, output replacement, rename collisions, and false success results.
- Added strict manifest checks and bounded decompression.
- Fixed MD5-only file inventories and source folder identity.
- Added the guided menu and the collect workflow.
- Added SQLite audit records and offline HTML reports.
- Added file signature categories and repeated hash groups.
- Added bounded file workers, streaming codecs, and one-pass ZIP hashing.
- Changed rename and sort to create working copies by default.
- Added modules, file safety tests, and a CI workflow.
- Kept one launcher and added module startup and a student code guide.
- Added the Windows network installer and its CI check.
- Added shared read buffers, parallel hash-name plans, and measured planning results.
- Added a dummy case builder for all ten main operations.
- Fixed direct demo startup and added a default sample output folder.

### 1.1.0

Added ZIP archives and more hash algorithm options.

### 1.0.0

Added encoding, JSON archives, hashing, renaming, and sorting.

## Upgrade notes

### From 1.1.1

No command changed.
The startup logo returns. Use `-q` before the command name to hide it.

### From 1.1.0

Get the full repository. The launcher now imports the package modules.
Bundle uses ZIP by default. Select `--format json` for the old container choice.
Encode and decode require an output folder.
Rename and sort require an output folder or an explicit audited in-place action.
Extraction does not support `--force`.
The unused `--timeout` option was removed.
Version 1.1.1 also dropped the animated banner. Version 1.1.2 restored it.
The old `--audit-log` option is replaced by the SQLite audit database.

Versions 1.0 and 1.1 JSON archives remain readable when their manifests pass the safety checks.

## Contributors and license

Original project: [DezTheJackal](https://github.com/DezTheJackal).
Version 1.1.1 updates: [0xb0rn3](https://github.com/0xb0rn3), also known as oxbv1.

Apache License 2.0. See [LICENSE](LICENSE).

---

## Dictionary

This dictionary explains each command, option, and term.
Each entry has a definition and an example.
Entries are in alphabetical order.
All examples use `python3 Evidencevault.py`. On Windows, after you use the installer, type `evidencevault` instead.

### Find a term by task

| If you want to... | Read this entry |
|---|---|
| Make a case package | [Collect](#collect) |
| Make one archive file | [Bundle](#bundle) |
| Check an archive | [Verify](#verify) |
| Get files out of an archive | [Extract](#extract) |
| List file hashes | [Inventory](#inventory) |
| Convert files to text form | [Encode](#encode) |
| Convert text form back to files | [Decode](#decode) |
| Change file names | [Rename](#rename) |
| Put files in folders | [Sort](#sort) |
| Make a report | [Report](#report) |
| Use menus instead of options | [Wizard](#wizard) |
| Hide the logo | [Quiet mode](#quiet-mode) |
| Preview before you change anything | [Dry run](#dry-run) |

### Algorithm

**Definition:** The method that calculates a hash.
The choices are `sha256` (default), `blake2b`, `blake2s`, `sha1`, and `md5`.
Use `--algo` with `hash`. Use `--hash-algo` with `collect` and `bundle`.
Use SHA-256 for a new case. MD5 and SHA-1 are legacy choices, and the run record notes their use.

**Example:**

~~~bash
python3 Evidencevault.py hash ./case_files -r --algo blake2b
python3 Evidencevault.py bundle ./case_files -r --hash-algo blake2b -o ./case.vault.zip
~~~

### Archive

**Definition:** One file that contains the case files and their manifest.
EvidenceVault makes two kinds: a [ZIP archive](#zip-archive) and a [JSON archive](#json-archive).

**Example:**

~~~bash
python3 Evidencevault.py bundle ./case_files -r -o ./case.vault.zip
~~~

### Audit database

**Definition:** The local SQLite file that stores runs and file actions.
It has the tables `runs`, `files`, and `events`.
Use `--db` to choose its path.
Collect, rename, and sort create `audit.sqlite3` in the output folder when you give no path.
The database is not signed.

**Example:**

~~~bash
python3 Evidencevault.py verify ./case.vault.zip --db ./records/audit.sqlite3
~~~

### Bundle

**Definition:** The command that creates an archive from files or folders. It is the "create archive" function.
The format is ZIP unless you select `--format json`.
The output path must be new.
Without `-r`, it includes only the files directly inside a folder.

**Example:**

~~~bash
python3 Evidencevault.py bundle ./case_files -r -o ./case.vault.zip
python3 Evidencevault.py bundle ./case_files -r --format json -o ./case.vault.json
~~~

### Case name

**Definition:** A label for the case. The program saves it in the manifest, the audit database, and the report.
Use `--case-name`. On every command except `rename`, `--case` is a shorter alias.
On `rename`, `--case` means [Letter case](#letter-case). Use `--case-name` there.

**Example:**

~~~bash
python3 Evidencevault.py collect ./case_files -o ./case_output --case-name CASE-2026-0091
~~~

### Case package

**Definition:** The four files that `collect` creates: `case.vault.zip`, `manifest.json`, `audit.sqlite3`, and `report.html`.

**Example:**

~~~bash
python3 Evidencevault.py collect ./case_files -o ./case_output
~~~

### Category

**Definition:** The file kind that `sort --by category` uses for folder names.
The kinds are `image`, `document`, `archive`, `audio`, `video`, `capture`, `encoded`, `database`, `executable`, and `other`.
The program checks the [file signature](#file-signature) first, then the extension.

**Example:**

~~~bash
python3 Evidencevault.py sort ./case_files -r -o ./sorted_files --by category
~~~

### Codec

**Definition:** A method that converts bytes to an encoded form and back.
The codecs are `base64`, `base64url`, `base32`, `base16`, `base85`, `ascii85`, and `urlenc`.
A codec is not encryption.

**Example:**

~~~bash
python3 Evidencevault.py encode ./case_files -r -e base32 -o ./encoded_files
~~~

### Collect

**Definition:** The command that prepares a [case package](#case-package).
It reads the files, writes a ZIP archive, checks the archive, and writes the inventory, audit database, and report.
It includes subfolders by default and always uses ZIP.
The output folder must be new.

**Example:**

~~~bash
python3 Evidencevault.py collect ./case_files -o ./case_output --case-name CASE-2026-0091 --operator "Your name"
~~~

### Compress

**Definition:** The `--compress` option. It compresses each file with zlib before encoding.
It applies to `encode` and to JSON archives from `bundle`.
A ZIP archive is always compressed. See [Compression level](#compression-level).

**Example:**

~~~bash
python3 Evidencevault.py encode ./case_files -r --compress -o ./encoded_files
python3 Evidencevault.py bundle ./case_files -r --format json --compress -o ./case.vault.json
~~~

### Compression level

**Definition:** The `--compression` option. A number from 1 to 9 for ZIP archives.
A low number is faster. A high number makes a smaller archive. The default is 6.

**Example:**

~~~bash
python3 Evidencevault.py bundle ./case_files -r --compression 9 -o ./case.vault.zip
~~~

### Decode

**Definition:** The command that restores files made by `encode`.
It picks the codec from the file extension, unless you give `-e`.
It removes the codec extension from the name. If there is none, it adds `.decoded`.

**Example:**

~~~bash
python3 Evidencevault.py decode ./encoded_files -r -o ./decoded_files
python3 Evidencevault.py decode ./mystery_files -e base32 -o ./decoded_files
~~~

### Decompress

**Definition:** The `--decompress` option for `decode`. It reverses the zlib compression that `encode --compress` applied.

**Example:**

~~~bash
python3 Evidencevault.py decode ./encoded_files -r --decompress -o ./decoded_files
~~~

### Dry run

**Definition:** The `--dry-run` option for `rename` and `sort`.
It prints each planned `path -> destination` line.
It writes no files, database, report, or log.
Do not combine it with `--db`, `--report`, or `--log-file`.

**Example:**

~~~bash
python3 Evidencevault.py rename ./case_files -r --pattern "EVID_{n:04d}{ext}" --dry-run
~~~

### Duplicate content group

**Definition:** A set of files that have the same hash. The report counts these groups and marks each repeated file.

**Example:**

~~~bash
python3 Evidencevault.py report ./case.vault.zip -o ./fresh_report.html
~~~

### Encode

**Definition:** The command that creates encoded working copies of files.
It adds the codec extension to each name, such as `notes.txt.b64`.
The output folder is required and must be new.
The default codec is `base64`.

**Example:**

~~~bash
python3 Evidencevault.py encode ./case_files -r -o ./encoded_files
python3 Evidencevault.py encode ./case_files -r -e base16 --compress -o ./encoded_files
~~~

### Encoding

**Definition:** The `-e` or `--encoding` option. It selects the [codec](#codec).
For `encode`, the default is `base64`.
For `decode`, the default is the codec that matches the file extension.
For `bundle`, it selects the codec for a JSON archive only.

**Example:**

~~~bash
python3 Evidencevault.py bundle ./case_files -r --format json -e base32 -o ./case.vault.json
~~~

### Exit code

**Definition:** The number that the program returns when it stops.
0 means success. 1 means a report or menu failure. 2 means an input, file, or output failure.
3 means a hash or size mismatch. 130 means the operator stopped the run.

**Example:**

~~~bash
python3 Evidencevault.py verify ./case.vault.zip
echo $?
~~~

### Extract

**Definition:** The command that restores files from an archive into a new output folder.
It checks every path, size, and hash.
It never replaces an existing file. It stops if any destination already exists.

**Example:**

~~~bash
python3 Evidencevault.py extract ./case_output/case.vault.zip -o ./restored_files
~~~

### File signature

**Definition:** Known bytes at the start of a file that can indicate its type.
The program uses signatures first and the extension second.
A signature does not prove the real file format and does not detect malware.

**Example:** A file that starts with `%PDF-` is a `document`, even if its name ends in `.dat`.

### Folders

**Definition:** The `--folders` option for `rename`. It renames folders in the working copy with the same pattern.
`{ext}` and `{hash}` are empty for folders.
It needs an output folder. It does not work with `--in-place`.

**Example:**

~~~bash
python3 Evidencevault.py rename ./case_files -r -o ./renamed_files --folders --pattern "EVID_{n:03d}{ext}"
~~~

### Hash

**Definition:** A value calculated from file contents.
A changed file gives a different hash.
The program stores hashes in manifests, inventories, the audit database, and reports.

**Example:** The SHA-256 hash of the text `Interview notes 1` and a line break is
`72aeea18d8b9b79fd4428a43a0da7632aee4c85891bd3bd6e4c2414f9ec88897`

### Hash length

**Definition:** The `--hash-length` option for `rename`. It sets how many hash characters the `{hash}` token inserts. The range is 1 to 64. The default is 8.

**Example:**

~~~bash
python3 Evidencevault.py rename ./case_files -r -o ./renamed_files --pattern "{n:03d}_{hash}{ext}" --hash-length 12
~~~

### Help

**Definition:** The `-h` or `--help` option. It shows the options for the program or for one command.

**Example:**

~~~bash
python3 Evidencevault.py --help
python3 Evidencevault.py bundle --help
~~~

### In place

**Definition:** The `--in-place` option for `rename` and `sort`. It changes the source paths instead of making copies.
It needs `--db` with a path outside the source folder.
It needs hard link support and one file system.
Use it only on a working copy.

**Example:**

~~~bash
python3 Evidencevault.py sort ./working_copy -r --in-place --db ./records/audit.sqlite3
~~~

### Inventory

**Definition:** A list of files with their sizes, times, and hashes. The `hash` command creates it.
Without `-o`, it prints `hash  path` lines.
With `-o`, `.json` gives JSON and any other extension gives CSV.

**Example:**

~~~bash
python3 Evidencevault.py hash ./case_files -r
python3 Evidencevault.py hash ./case_files -r -o ./manifest.json
~~~

### JSON archive

**Definition:** An archive in one JSON file. It holds the manifest and every encoded payload.
It suits small cases. It is limited to 16 MiB of raw file data.
Select it with `--format json`.

**Example:**

~~~bash
python3 Evidencevault.py bundle ./case_files -r --format json --compress -o ./case.vault.json
~~~

### Letter case

**Definition:** The `--case` option for `rename`. It changes the letters of the whole file name, including the extension.
The values are `none` (default), `lower`, `upper`, and `title`.

**Example:**

~~~bash
python3 Evidencevault.py rename ./case_files -r -o ./renamed_files --case lower
~~~

### Log file

**Definition:** The `--log-file` option. It writes command messages to a file.
Add `-v` to include technical error details.

**Example:**

~~~bash
python3 Evidencevault.py verify ./case.vault.zip --log-file ./records/run.log -v
~~~

### Manifest

**Definition:** A list of file paths, sizes, hashes, and recorded times.
Each archive has one. The program checks it, but it is not signed.

**Example:** A ZIP archive keeps its manifest as `manifest.json`. Check it with:

~~~bash
python3 Evidencevault.py verify ./case.vault.zip
~~~

### Max file bytes

**Definition:** The `--max-file-bytes` option. It sets the largest file size, in whole bytes, that the program accepts or restores.
The default is 2 GiB. `collect`, `verify`, `extract`, `report`, `encode`, and `decode` accept it.

**Example:**

~~~bash
python3 Evidencevault.py extract ./case.vault.zip -o ./restored_files --max-file-bytes 104857600
~~~

### Max total bytes

**Definition:** The `--max-total-bytes` option. It sets the largest total size, in whole bytes, for one archive operation.
The default is 20 GiB. `collect`, `verify`, `extract`, and `report` accept it.

**Example:**

~~~bash
python3 Evidencevault.py verify ./case.vault.zip --max-total-bytes 5368709120
~~~

### MD5 option

**Definition:** The `--md5` option for `hash`. It adds an `md5` field from the same file read.
MD5 is a legacy hash. Use it only when another system needs it.

**Example:**

~~~bash
python3 Evidencevault.py hash ./case_files -r --md5 -o ./manifest.json
~~~

### Minify

**Definition:** The `--minify` option. It writes compact JSON for a JSON archive.
It makes a smaller file that is harder to read. ZIP archives ignore it.

**Example:**

~~~bash
python3 Evidencevault.py bundle ./case_files -r --format json --minify -o ./case.vault.json
~~~

### Operator

**Definition:** The `--operator` option. It records the name of the person who runs the command.
The program saves it in the audit database and the report.

**Example:**

~~~bash
python3 Evidencevault.py collect ./case_files -o ./case_output --operator "Your name"
~~~

### Output

**Definition:** The `-o` or `--output` option. It names the new file or folder for the result.
The path must be new. It must be outside the source folder.

**Example:**

~~~bash
python3 Evidencevault.py encode ./case_files -r -o ./encoded_files
~~~

### Pattern

**Definition:** The `--pattern` option for `rename`. A name template made of text and [tokens](#token).
The default is `{name}_{n:04d}{ext}`.

**Example:**

~~~bash
python3 Evidencevault.py rename ./case_files -r -o ./renamed_files --pattern "EVID_{date}_{n:04d}{ext}"
~~~

### Quiet mode

**Definition:** The `-q`, `--quiet`, or `--no-banner` option. It hides the startup logo.
Put it before the command name. It does not hide the result summary.

**Example:**

~~~bash
python3 Evidencevault.py -q verify ./case.vault.zip
~~~

### Recursive

**Definition:** The `-r` or `--recursive` option. It includes subfolders.
`collect` includes them by default. The other commands include only the top folder unless you add `-r`.

**Example:**

~~~bash
python3 Evidencevault.py hash ./case_files -r
~~~

### Rename

**Definition:** The command that creates working copies with new, consistent file names.
It keeps the source files unchanged unless you add `--in-place`.
The output folder is required unless you use `--in-place` or `--dry-run`.

**Example:**

~~~bash
python3 Evidencevault.py rename ./case_files -r -o ./renamed_files --pattern "EVID_{n:04d}_{hash}{ext}"
~~~

### Report

**Definition:** The command that writes an offline HTML report.
Use it with an archive for a fresh check, or with `--db` for a saved run.
Separately, the `--report` option on other commands writes a report after that command.
The report path must be new.

**Example:**

~~~bash
python3 Evidencevault.py report ./case.vault.zip -o ./fresh_report.html
python3 Evidencevault.py report --db ./records/audit.sqlite3 -o ./saved_report.html
python3 Evidencevault.py hash ./case_files -r -o ./manifest.json --report ./hash_report.html
~~~

### Run

**Definition:** One command operation and its result.
The program gives each run a run ID and saves it when you use an audit database.

**Example:**

~~~bash
python3 Evidencevault.py verify ./case.vault.zip --db ./records/audit.sqlite3
~~~

### Run ID

**Definition:** The `--run-id` option for `report`. It selects one saved run by its identifier.
Without it, the report uses the latest completed run.

**Example:**

~~~bash
sqlite3 ./records/audit.sqlite3 "select id from runs"
python3 Evidencevault.py report --db ./records/audit.sqlite3 --run-id cd07a62bd70c413ca09fbc404724707b -o ./one_run.html
~~~

### Sort

**Definition:** The command that creates working copies in folders by file type or date.
The `--by` option picks the rule: `category` (default), `ext`, `date`, or `encoding`.
The original subfolder path stays below each new folder.

**Example:**

~~~bash
python3 Evidencevault.py sort ./case_files -r -o ./sorted_files --by ext
~~~

### Source

**Definition:** The file or folder that you give to a command as input.
EvidenceVault rejects symbolic links and nonregular files as sources.

**Example:**

~~~bash
python3 Evidencevault.py hash ./case_files ./extra_notes.txt -r
~~~

### Start number

**Definition:** The `--start` option for `rename`. It sets the first value of `{n}`. The default is 1.

**Example:**

~~~bash
python3 Evidencevault.py rename ./case_files -r -o ./renamed_files --pattern "EVID_{n:04d}{ext}" --start 100
~~~

### Token

**Definition:** A placeholder inside a rename [pattern](#pattern), written in braces.
The tokens are `{name}`, `{ext}`, `{n}`, `{hash}`, `{date}`, `{time}`, and `{parent}`.
Only `{n}` accepts a format such as `{n:04d}`.

**Example:** The pattern `{parent}_{n:03d}{ext}` can give `logs_007.log`.

### Verbose

**Definition:** The `-v` or `--verbose` option. It shows technical error details.

**Example:**

~~~bash
python3 Evidencevault.py extract ./case.vault.zip -o ./restored_files -v
~~~

### Verify

**Definition:** The command that checks an archive. It checks the archive structure, paths, file sizes, and file hashes.
It writes no restored files.
A changed file gives a `Mismatch` line and exit code 3.

**Example:**

~~~bash
python3 Evidencevault.py verify ./case_output/case.vault.zip
~~~

### Version

**Definition:** The `--version` option. It prints the program version and exits.

**Example:**

~~~bash
python3 Evidencevault.py --version
~~~

### Wizard

**Definition:** The guided menu. It asks questions and builds the command for you.
Start it with no command in a terminal, or with `wizard`.
It shows the logo once and previews rename and sort before it changes anything.

**Example:**

~~~bash
python3 Evidencevault.py wizard
~~~

### Worker

**Definition:** A thread that processes a file task.
The `--workers` option sets how many run at one time, from 1 to 32.
The default is at most four.

**Example:**

~~~bash
python3 Evidencevault.py hash ./case_files -r --workers 8
~~~

### Working copy

**Definition:** A new copy of a source file, made by `encode`, `decode`, `rename`, or `sort`.
The source stays unchanged, except with `--in-place`.

**Example:**

~~~bash
python3 Evidencevault.py sort ./case_files -r -o ./sorted_files
~~~

### ZIP archive

**Definition:** The default archive format. A standard ZIP file.
It holds each file under `files/` and a `manifest.json` entry.
Files keep their raw bytes with ZIP compression, so the archive is smaller than a JSON archive.
Use `--compression` to set the level.

**Example:**

~~~bash
python3 Evidencevault.py bundle ./case_files -r --compression 6 -o ./case.vault.zip
~~~
