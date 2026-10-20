"""Check documentation parity, source pin, command table and executable examples."""
import ast
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

WEBSITE = Path(__file__).resolve().parents[1]
ROOT = WEBSITE.parent
PIN = "9a062eb9de0990ce1074dd677d26e5a528ee14a0"
PACKAGE = ROOT / ".agents/skills/architect-dev-team"
SCRIPT = PACKAGE / "scripts/validate.py"


def run(arguments):
    result = subprocess.run(arguments, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"Command failed: {arguments}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def main():
    prompts = json.loads((WEBSITE / "src/data/quickstart.json").read_text(encoding="utf-8"))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    quickstart = readme.split("## Quickstart\n", 1)[1].split("## ", 1)[0]
    copied = re.search(r"```text\n(.*?)\n```", quickstart, re.S).group(1)
    if copied != prompts["en"] or prompts["de"] in quickstart:
        raise RuntimeError("README Quickstart must contain only the shared English prompt")
    for locale, prompt in prompts.items():
        if "https://github.com/YoungJibbit95/ldt-skill" not in prompt or "$architect-dev-team" not in prompt:
            raise RuntimeError(f"Wrong repository or skill identifier: {locale}")
        if re.search(r"\b[0-9a-f]{40}\b", prompt):
            raise RuntimeError(f"Primary Quickstart must not pin a commit: {locale}")
    print("Quickstart: shared English README copy, DE/EN repository and identifier checked.")
    # A documented pin is useful only while the actual described sources match it.
    tracked = run(["git", "ls-tree", "-r", "--name-only", PIN, "--", ".agents/skills/architect-dev-team"]).splitlines()
    for relative in tracked:
        expected = subprocess.run(["git", "show", f"{PIN}:{relative}"], cwd=ROOT, capture_output=True, check=True).stdout
        if (ROOT / relative).read_bytes() != expected:
            raise RuntimeError(f"Documented source differs from {PIN}: {relative}")
    print(f"Source comparison: {len(tracked)} skill files byte-identical to {PIN[:7]}.")

    docs = WEBSITE / "src/content/docs"
    pairs = {locale: {p.relative_to(docs / locale).as_posix() for p in (docs / locale).rglob("*.mdx")} for locale in ("de", "en")}
    if pairs["de"] != pairs["en"]:
        raise RuntimeError(f"Missing translations: {pairs['de'] ^ pairs['en']}")
    for relative in pairs["de"]:
        for locale in ("de", "en"):
            text = (docs / locale / relative).read_text(encoding="utf-8")
            if not re.search(r"^title: .+", text, re.M) or not re.search(r"^description: .+", text, re.M):
                raise RuntimeError(f"Missing page metadata: {locale}/{relative}")
    print(f"Translation structure: {len(pairs['de'])} complete DE/EN documentation pairs.")
    translations = {locale: json.loads((WEBSITE / f"src/content/i18n/{locale}.json").read_text(encoding="utf-8")) for locale in ("de", "en")}
    if translations["de"].keys() != translations["en"].keys() or any(not value for data in translations.values() for value in data.values()):
        raise RuntimeError("UI translation keys are missing or empty")

    commands = json.loads((WEBSITE / "src/data/commands.json").read_text(encoding="utf-8"))
    help_text = run([sys.executable, "-B", str(SCRIPT), "--help"])
    actual = set(re.search(r"\{([a-z,-]+)\}", help_text).group(1).split(","))
    if actual != {command["name"] for command in commands}:
        raise RuntimeError("Public command table differs from actual CLI help")
    for command in commands:
        run([sys.executable, "-B", str(SCRIPT), command["name"], "--help"])

    for arguments in (["package", str(PACKAGE)], ["registry", str(PACKAGE / "registry/skills.json")], ["registry", str(PACKAGE / "registry/index.json")]):
        run([sys.executable, "-B", str(SCRIPT), *arguments])
    proposal = json.loads(run([sys.executable, "-B", str(SCRIPT), "registry", str(PACKAGE / "registry/skills.json"), "--migration-proposal"]))
    if "source" not in proposal or "validation_issues" not in proposal:
        raise RuntimeError("Unexpected registry proposal output")
    with tempfile.TemporaryDirectory() as temp:
        state_path = Path(temp) / "state.json"
        state_path.write_bytes((PACKAGE / "assets/state.template.json").read_bytes())
        run([sys.executable, "-B", str(SCRIPT), "state", str(state_path), "--root", temp])
    # These are public enums in the described source, rather than restated gate logic.
    tree = ast.parse((PACKAGE / "scripts/ldt_core/state.py").read_text(encoding="utf-8"))
    phases = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "PHASES" for t in node.targets))
    for locale in ("de", "en"):
        lifecycle = (docs / locale / "docs/workflow.mdx").read_text(encoding="utf-8")
        if any(f"`{phase}`" not in lifecycle for phase in phases):
            raise RuntimeError(f"Documented lifecycle is incomplete: {locale}")
    print(f"Reference: {len(commands)} actual commands, real package/registry/template validation and registry migration output checked.")


if __name__ == "__main__":
    main()
