"""Install the ECE workflow into the current user's Codex CLI configuration."""
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
from shutil import copy2
import sys
from tempfile import NamedTemporaryFile

if not sys.platform.startswith("linux"):
    raise SystemExit("Run this installer on the ECE Linux VM.")

src = Path(__file__).resolve().parent
home = Path.home()
codex = home / ".codex"
global_file = Path(os.environ.get("CODEX_HOME") or codex) / "AGENTS.md"
skills = home / ".agents/skills"
manifest = codex / "ece-workflow-installed.json"
installed = json.loads(manifest.read_text()) if manifest.exists() else {}
section = (src / "AGENTS.md").read_text().strip()
old = global_file.read_text() if global_file.exists() else ""
if section.splitlines()[0] in old.splitlines() and section not in old:
    raise SystemExit("Existing ECE section differs. Merge AGENTS.md manually.")
updated = old if section in old else (old.rstrip() + "\n\n" + section + "\n").lstrip("\n")
if updated != old and global_file.is_symlink():
    raise SystemExit("Global AGENTS.md is a symlink. Merge at its source.")

if len(list((src / "skills").glob("*/SKILL.md"))) != 3:
    raise SystemExit("Incomplete skill bundle.")
launcher = src / "scripts/virtuoso-batch.sh"
if not launcher.is_file():
    raise SystemExit("Missing scripts/virtuoso-batch.sh.")

# Upgrade only known shipped content or the last installer-managed version.
previous_cadence = {
    "d8ff2042669ea79c7ffb77450ffaa40e6af1a6474e079638bc0edc90c437653d",
    "defb4d67a6f0d895e8e445f12daf0c95e1b56af12529766bee0bb14395766b21",
    "5acfee35755424f04c229c83947c586c5a6fd3d1cbec896425d2e9359dab7f73",
    "ff1c21b66814c17441446b39cd58f8dca52e40221fe6a28ed37a4455fcc8986b",
    "8850e6b2a318b49a1ac648bdef46daa0d9797643b607303d8d66f9018f2c24f0",
    "ee6ec1d5212fd00068f9f3bb7280ae0e691bee432842b2cd1789be3ad986fcd0",
}
legacy_hash = "220ef325ae1eb616d1c0894deaba0821a55adde8c1dc7687816ea30cf4c22418"
sources = [(p, skills / p.relative_to(src / "skills"), 0o644)
           for p in sorted((src / "skills").rglob("*"))
           if p.is_file() and not any(part.startswith("._") or part == ".DS_Store"
                                     for part in p.relative_to(src / "skills").parts)]
sources.append((launcher, codex / "scripts/virtuoso-batch.sh", 0o700))
changes = []
next_manifest = {}
for source, dest, mode in sources:
    content = source.read_bytes()
    key = str(dest)
    next_manifest[key] = sha256(content).hexdigest()
    if dest.is_symlink():
        raise SystemExit("Refusing to replace symlink: {}".format(dest))
    if dest.exists() and dest.read_bytes() != content:
        digest = sha256(dest.read_bytes()).hexdigest()
        known = previous_cadence if dest == skills / "cadence-virtuoso/SKILL.md" else set()
        if digest not in known and digest != installed.get(key):
            raise SystemExit("Existing file differs. Review {} before installing.".format(dest))
    if not dest.exists() or dest.read_bytes() != content or dest.stat().st_mode & 0o777 != mode:
        changes.append((dest, content, mode))

legacy = home / "cadence_work/codex-virtuoso/virtuoso-batch.sh"
if legacy.is_symlink() or (legacy.exists() and sha256(legacy.read_bytes()).hexdigest() != legacy_hash):
    raise SystemExit("Project-local launcher differs. Review {} before migrating.".format(legacy))
metadata_files = []
for key, digest in installed.items():
    path = Path(key)
    if str(path).startswith(str(skills) + "/") and path.name.startswith("._") and path.exists():
        if path.is_symlink() or sha256(path.read_bytes()).hexdigest() != digest or path.read_bytes()[:4] != b"\x00\x05\x16\x07":
            raise SystemExit("Unexpected archive metadata. Review {} before removing.".format(path))
        metadata_files.append(path)
if updated != old:
    mode = global_file.stat().st_mode & 0o777 if global_file.exists() else 0o600
    changes.append((global_file, updated.encode(), mode))

# All conflicts are checked before modifying any deployed file.
backup_dir = codex / "ece-install-backups" / datetime.utcnow().strftime("%Y%m%dT%H%M%S%fZ")
for dest, content, mode in changes:
    if dest.exists():
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / str(dest).lstrip("/")
        backup.parent.mkdir(parents=True, exist_ok=True)
        copy2(dest, backup)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=str(dest.parent), delete=False) as tmp:
        tmp.write(content)
    Path(tmp.name).chmod(mode)
    Path(tmp.name).replace(dest)
    print("Installed:", dest)

if legacy.exists():
    backup_dir.mkdir(parents=True, exist_ok=True)
    copy2(legacy, backup_dir / "project-local-virtuoso-batch.sh")
    legacy.unlink()
    print("Moved project-local launcher; backup:", backup_dir)

for path in metadata_files:
    path.unlink()
    print("Removed installer-created archive metadata:", path)

if installed != next_manifest:
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", dir=str(manifest.parent), delete=False) as tmp:
        json.dump(next_manifest, tmp, indent=2, sort_keys=True)
        tmp.write("\n")
    Path(tmp.name).replace(manifest)
print("Configured", global_file, skills, "and", codex / "scripts/virtuoso-batch.sh")
