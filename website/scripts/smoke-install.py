"""Exercise the published tutorial in temporary homes/projects, never active installs."""
import hashlib
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

WEBSITE = Path(__file__).resolve().parents[1]
VERIFIED_DEVELOPMENT_REVISION = "838a2e1376a0b3e44931c54310be95d253380b1a"
WINDOWS = os.name == "nt"
SHELL = shutil.which("pwsh") or shutil.which("powershell") if WINDOWS else shutil.which("bash")
if not SHELL:
    raise RuntimeError("Required tutorial shell is unavailable")


def quote(value):
    return "'" + str(value).replace("'", "''") + "'" if WINDOWS else shlex.quote(str(value))


def shell(script, working, *, succeeds=True):
    prefix = "$ErrorActionPreference = 'Stop'\n" if WINDOWS else "set -e\n"
    command = [SHELL, "-NoProfile", "-NonInteractive", "-Command", prefix + script] if WINDOWS else [SHELL, "-c", prefix + script]
    result = subprocess.run(command, cwd=working, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    if (result.returncode == 0) != succeeds:
        raise RuntimeError(f"Tutorial shell returned {result.returncode}; expected success={succeeds}\n{result.stdout}\n{result.stderr}")
    return result


def hashes(directory):
    return {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.rglob("*") if p.is_file() and "__pycache__" not in p.parts}


def validate(destination):
    subprocess.run([sys.executable, "-B", str(destination / "scripts/validate.py"), "package", str(destination)], check=True, capture_output=True, timeout=30)


def remove_inside(destination, sandbox):
    target = destination.resolve()
    if not target.is_relative_to(sandbox.resolve()) or target == sandbox.resolve():
        raise RuntimeError("Removal target escaped the isolated sandbox")
    shutil.rmtree(target)


def exercise(locale, sandbox):
    sandbox.mkdir()
    project = sandbox / "sample project"
    personal = sandbox / "sample user"
    project.mkdir(); personal.mkdir()
    text = (WEBSITE / f"src/content/docs/{locale}/docs/install.mdx").read_text(encoding="utf-8")
    language = "powershell" if WINDOWS else "bash"
    blocks = re.findall(r"```" + language + r"\n(.*?)```", text, re.S)
    if len(blocks) != 4:
        raise RuntimeError(f"Expected the four tutorial blocks for {locale}/{language}; got {len(blocks)}")
    # Manual selection is explicit; never silently use the clone's default branch.
    # Substitute the documented verified development fallback, like the target paths.
    shell(blocks[0].replace("SELECTED_TAG_OR_COMMIT", VERIFIED_DEVELOPMENT_REVISION), sandbox)
    recorded = (sandbox / "ldt-skill-source/INSTALL_REVISION.txt").read_text(encoding="utf-8-sig").strip()
    if recorded != VERIFIED_DEVELOPMENT_REVISION:
        raise RuntimeError("Installation provenance does not match the selected commit")
    # Exercise annotated-tag resolution without creating or publishing a release.
    subprocess.run(["git", "-C", str(sandbox / "ldt-skill-source"),
                    "-c", "user.name=Installation smoke", "-c", "user.email=smoke@example.invalid",
                    "tag", "-a", "smoke-stable-fixture", VERIFIED_DEVELOPMENT_REVISION,
                    "-m", "Local test fixture, not a published release"], check=True, capture_output=True)
    selection = blocks[0][blocks[0].index("git -C ldt-skill-source checkout"):]
    shell(selection.replace("SELECTED_TAG_OR_COMMIT", "smoke-stable-fixture"), sandbox)
    if (sandbox / "ldt-skill-source/INSTALL_REVISION.txt").read_text(encoding="utf-8-sig").strip() != recorded:
        raise RuntimeError("Annotated tag did not resolve to the immutable selected commit")
    shell(selection, sandbox, succeeds=False)
    if (sandbox / "ldt-skill-source/INSTALL_REVISION.txt").read_text(encoding="utf-8-sig").strip() != recorded:
        raise RuntimeError("Failed selection changed the installation provenance")
    source = sandbox / "ldt-skill-source/.agents/skills/architect-dev-team"
    project_block = blocks[1].replace("C:\\Pfad\\zu\\deinem\\Projekt", str(project)).replace("C:\\path\\to\\your\\project", str(project)).replace("/pfad/zu/deinem/projekt", str(project)).replace("/path/to/your/project", str(project))
    # Substitute only the home operand in test code. Never repurpose HOME/$HOME.
    personal_block = blocks[2].replace("$HOME", "$smokeUserHome" if WINDOWS else "$smoke_user_home")
    for label, block, destination in (
        ("project", project_block, project / ".agents/skills/architect-dev-team"),
        ("personal", personal_block, personal / ".agents/skills/architect-dev-team"),
    ):
        def prefix(current_source):
            if WINDOWS:
                return f"$skillSource = {quote(current_source)}\n$smokeUserHome = {quote(personal)}\n"
            return f"skill_source={quote(current_source)}\nsmoke_user_home={quote(personal)}\n"
        shell(prefix(source) + block + "\n" + blocks[3], sandbox)
        validate(destination)
        if hashes(destination) != hashes(source):
            raise RuntimeError("Installed package differs from pinned source")
        (destination / "old-install-marker.txt").write_text("synthetic old installation", encoding="utf-8")
        before = hashes(destination)
        shell(prefix(source) + block, sandbox, succeeds=False)
        if hashes(destination) != before:
            raise RuntimeError("Existing installation was overwritten")

        # Test the documented staged replacement procedure with a synthetic marker,
        # without pretending to test an actual future upstream release or migration.
        candidate = sandbox / f"new candidate {label}"
        shutil.copytree(source, candidate)
        (candidate / "update-marker.txt").write_text("synthetic update fixture", encoding="utf-8")
        validate(candidate)
        backup = sandbox / "backups" / label
        shutil.copytree(destination, backup)
        remove_inside(destination, sandbox)
        shell(prefix(candidate) + block + "\n" + blocks[3], sandbox)
        if hashes(destination) != hashes(candidate):
            raise RuntimeError("Replacement retained stale files or lost candidate files")
        validate(destination)
        remove_inside(destination, sandbox)
        if destination.exists() or not destination.parent.exists() or not backup.exists():
            raise RuntimeError("Removal touched unrelated parent/backup or failed")
        # Exercise recovery of the preserved previous package in the same sandbox.
        shutil.copytree(backup, destination)
        validate(destination)
        remove_inside(destination, sandbox)
        print(f"PASS {locale}/{label}: selected commit recorded, tutorial copy, validation, no-overwrite, staged replacement, removal, recovery", flush=True)


def main():
    with tempfile.TemporaryDirectory(prefix="ldt-install-smoke-") as temp:
        for locale in ("de", "en"):
            exercise(locale, Path(temp) / locale)
    print(f"PASS {sys.platform}: isolated tutorial smoke; personal-home operand substituted; no active installation changed; Codex discovery NOT tested.")


if __name__ == "__main__":
    main()
