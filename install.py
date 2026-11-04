"""Install the ECE workflow into the current user's Codex CLI configuration."""
import argparse
from datetime import datetime
from hashlib import sha256
import json
import os
import re
from pathlib import Path
from shutil import copy2, which
import sys
import shlex
import subprocess
from tempfile import NamedTemporaryFile

if not sys.platform.startswith("linux"):
    raise SystemExit("Run this installer on the ECE Linux VM.")

src = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description="Install Cadex; live activation always requires a later CIW action")
parser.add_argument("--home", type=Path, default=Path.home(), help="Explicit destination home (isolated tests/staging)")
parser.add_argument("--live", action="store_true", help="Install the pinned SkillBridge dependency in a dedicated venv; does not attach")
parser.add_argument("--live-python", default=which("python3.11") or sys.executable)
args = parser.parse_args()
# Preserve the spelling of UF's /home alias so installed manifest keys remain stable.
home = args.home.expanduser().absolute()
codex = home / ".codex"
global_file = (Path(os.environ.get("CODEX_HOME") or codex) if home.resolve() == Path.home().resolve() else codex) / "AGENTS.md"
skills = home / ".agents/skills"
manifest = codex / "ece-workflow-installed.json"
installed = json.loads(manifest.read_text()) if manifest.exists() else {}
section = (src / "AGENTS.md").read_text().strip()
old = global_file.read_text() if global_file.exists() else ""
# Migrate only exact known managed sections; preserve all surrounding user text.
heading = section.splitlines()[0]
previous_sections = {"fe26ebab783797c2c5eb33bdbca8193a9d3af7e05691d43f7ddfe6b22bb6557b"}
pattern = re.compile(r"(?m)^" + re.escape(heading) + r"\n.*?(?=^## |\Z)", re.DOTALL)
matches = list(pattern.finditer(old))
if not matches and heading in old.splitlines():
    raise SystemExit("Incomplete ECE section. Review AGENTS.md before installing.")
if len(matches) > 1:
    raise SystemExit("Duplicate ECE sections. Review AGENTS.md before installing.")
if matches:
    match = matches[0]
    current = match.group().rstrip()
    if current != section and sha256(current.encode()).hexdigest() not in previous_sections:
        raise SystemExit("Existing ECE section differs. Merge AGENTS.md manually.")
    updated = old[:match.start()] + section + match.group()[len(current):] + old[match.end():]
else:
    updated = (old.rstrip() + "\n\n" + section + "\n").lstrip("\n")
if updated != old and global_file.is_symlink():
    raise SystemExit("Global AGENTS.md is a symlink. Merge at its source.")

required_skills = {"analog-design-flow", "analog-design", "cadence-simulation",
                   "cadence-layout", "cadence-virtuoso", "sv-design-verification", "vams-modeling"}
found_skills = {p.parent.name for p in (src / "skills").glob("*/SKILL.md")}
if found_skills != required_skills:
    raise SystemExit("Incomplete or unexpected skill bundle: " + ", ".join(sorted(found_skills ^ required_skills)))
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
sources = [(p, skills / p.relative_to(src / "skills"), 0o644)
           for p in sorted((src / "skills").rglob("*"))
           if p.is_file() and not any(part.startswith("._") or part == ".DS_Store"
                                     for part in p.relative_to(src / "skills").parts)]
sources.append((launcher, codex / "scripts/virtuoso-batch.sh", 0o700))
payloads = [(source.read_bytes(), dest, mode) for source, dest, mode in sources]
live_dir = codex / "share/cadex-live"
state_dir = home / ".local/state/cadex/live"
venv = home / ".venvs/cadex-live"
python = venv / "bin/python"
bridge_il = venv / "lib/python3.11/site-packages/skillbridge/server/python_server.il"
# Resolve the real venv's site-packages after dependency setup below; the path
# query is unlicensed and never opens a Workspace.
def bridge_resource(executable):
    query = "import pathlib, skillbridge; print(pathlib.Path(skillbridge.__file__).parent / 'server/python_server.il')"
    return Path(subprocess.check_output([str(executable), "-c", query], universal_newlines=True).strip())

if python.exists():
    probe = subprocess.run([str(python), "-c", "import skillbridge"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if probe.returncode == 0:
        bridge_il = bridge_resource(python)
config = {"schema": 1, "state_dir": str(state_dir), "log_dir": str(state_dir / "logs"),
          "bootstrap": str(live_dir / "bootstrap.il"), "skillbridge_version": "1.8.0"}
for name in ["client.py", "managed.py", "attach.py", "server.py", "live.il", "job.il", "recipes.il", "inspect.il", "api-index.json"]:
    payloads.append(((src / "live" / name).read_bytes(), live_dir / name, 0o600))
payloads.append(((json.dumps(config, indent=2) + "\n").encode(), live_dir / "config.json", 0o600))
wrapper = "#!/bin/sh\n"
wrapper += "if [ -x {0} ]; then exec {0} {1} \"$@\"; fi\n".format(shlex.quote(str(python)), shlex.quote(str(live_dir / "client.py")))
wrapper += "exec {0} {1} \"$@\"\n".format(shlex.quote(sys.executable), shlex.quote(str(live_dir / "client.py")))
payloads.append((wrapper.encode(), codex / "scripts/virtuoso-live", 0o700))

def bootstrap(path):
    text = (src / "live/bootstrap.il.in").read_text()
    values = {"BRIDGE_IL": str(path), "LIVE_IL": str(live_dir / "live.il"),
              "SERVER_WRAPPER": '\"' + str(live_dir / "server.py") + '\"',
              "SERVER_LOG": str(state_dir / "logs/skillbridge-skill.log"),
              "ATTACH_LOG": str(state_dir / "logs/attach.log"),
              "ATTACH_PY": str(live_dir / "attach.py"), "PYTHON": str(python)}
    for key, value in values.items():
        text = text.replace("@" + key + "@", json.dumps(value))
    return text.encode()

payloads.append((bootstrap(bridge_il), live_dir / "bootstrap.il", 0o600))
changes = []
next_manifest = {}
for content, dest, mode in payloads:
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

# All conflicts are checked before dependency setup or deployed-file changes.
if args.live:
    version = subprocess.check_output([args.live_python, "-c", "import sys; print(sys.version_info >= (3, 8))"], universal_newlines=True).strip()
    if version != "True":
        raise SystemExit("Live support requires Python 3.8+ (UF provides python3.11).")
    if not python.exists():
        venv.parent.mkdir(parents=True, exist_ok=True)
        subprocess.check_call([args.live_python, "-m", "venv", str(venv)])
    installed_version = subprocess.run([str(python), "-c", "import importlib.metadata; print(importlib.metadata.version('skillbridge'))"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if installed_version.returncode != 0:
        subprocess.check_call([str(python), "-m", "pip", "install", "skillbridge==1.8.0"])
    elif installed_version.stdout.strip() != "1.8.0":
        raise SystemExit("Dedicated live venv has another SkillBridge version; review before replacing it.")
    actual_bridge = bridge_resource(python)
    content = bootstrap(actual_bridge)
    dest = live_dir / "bootstrap.il"
    changes = [item for item in changes if item[0] != dest]
    next_manifest[str(dest)] = sha256(content).hexdigest()
    if not dest.exists() or dest.read_bytes() != content:
        changes.append((dest, content, 0o600))

for directory in [state_dir, state_dir / "logs", state_dir / "sessions", state_dir / "locks"]:
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if directory.is_symlink() or directory.stat().st_uid != os.getuid() or directory.stat().st_mode & 0o077:
        raise SystemExit("Live state directory must be private and owned: {}".format(directory))

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

print("Installation leaves GUI attachment unchanged. To opt in a GUI when desired, one CIW action:")
print("load({})".format(json.dumps(str(live_dir / "bootstrap.il"))))
