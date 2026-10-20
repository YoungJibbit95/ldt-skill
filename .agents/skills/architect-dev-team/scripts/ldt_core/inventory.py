"""Bounded project observations. No project code, tools or network are executed."""
import json
import os
from pathlib import Path
import re
import stat

from .common import Invalid, require, unique_object


LIMITS = {"depth": 5, "directories": 128, "entries_per_directory": 256,
          "entries": 4096, "file_bytes": 131072, "total_bytes": 2097152}
DIRECTORIES = {"src", "app", "apps", "packages", "lib", "tests", "test", "backend",
               "frontend", "server", "client", "services", "web", "docs"}
MANIFESTS = {"package.json", "pyproject.toml", "requirements.txt", "setup.cfg",
             "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "build.gradle.kts",
             "Gemfile", "composer.json", "pubspec.yaml", "Package.swift",
             "CMakeLists.txt", "global.json"}
CONFIGS = {"tsconfig.json", "next.config.js", "next.config.mjs", "next.config.ts",
           "vite.config.js", "vite.config.ts", "vitest.config.ts", "jest.config.js",
           "playwright.config.ts", "pytest.ini", "Dockerfile", "compose.yaml",
           "docker-compose.yml", "vercel.json", "netlify.toml"}
EXTENSIONS = {".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript",
              ".ts": "TypeScript", ".tsx": "TypeScript", ".go": "Go", ".rs": "Rust",
              ".java": "Java", ".kt": "Kotlin", ".cs": "C#", ".rb": "Ruby",
              ".php": "PHP", ".swift": "Swift", ".dart": "Dart", ".cpp": "C++",
              ".c": "C"}
MANIFEST_LANGUAGES = {"pyproject.toml": "Python", "requirements.txt": "Python",
                      "setup.cfg": "Python", "Cargo.toml": "Rust", "go.mod": "Go",
                      "pom.xml": "Java", "build.gradle": "JVM", "build.gradle.kts": "JVM",
                      "Gemfile": "Ruby", "composer.json": "PHP", "pubspec.yaml": "Dart",
                      "Package.swift": "Swift", "CMakeLists.txt": "C/C++"}
DEPENDENCIES = {"react": ("framework", "React"), "next": ("framework", "Next.js"),
                "vue": ("framework", "Vue"), "svelte": ("framework", "Svelte"),
                "@angular/core": ("framework", "Angular"),
                "express": ("framework", "Express"), "typescript": ("language", "TypeScript"),
                "vite": ("tooling", "Vite"), "vitest": ("tooling", "Vitest"),
                "jest": ("tooling", "Jest"), "@playwright/test": ("tooling", "Playwright"),
                "react-native": ("platform", "React Native")}
CONFIG_SIGNALS = {"tsconfig.json": ("language", "TypeScript"),
                  "pytest.ini": ("tooling", "pytest"), "Dockerfile": ("platform", "Docker"),
                  "compose.yaml": ("platform", "Docker Compose"),
                  "docker-compose.yml": ("platform", "Docker Compose"),
                  "vercel.json": ("platform", "Vercel"), "netlify.toml": ("platform", "Netlify")}
SAFE_NAME = re.compile(r"[A-Za-z0-9_@][A-Za-z0-9_.@-]{0,127}\Z")
SENSITIVE = re.compile(r"(^|[_.-])(secret[s]?|credential[s]?|password[s]?|token[s]?)([_.-]|$)", re.I)


def _linked(info):
    # Windows junctions and other reparse points may not report is_symlink().
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def _identity(info):
    return info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns


def inventory(root):
    """Return path-backed facts/inferences, never permission or a recommendation.

    The caller supplies a stable, local directory. This is a bounded inventory,
    not a full tree attestation or an atomic defense against concurrent mutation.
    """
    require(isinstance(root, (str, os.PathLike)) and bool(os.fspath(root)), "inventory root must be a directory")
    root = Path(root).absolute()
    try:
        for part in reversed([root, *root.parents]):
            require(not _linked(part.lstat()), "inventory root cannot traverse links/reparse points")
        require(root.is_dir(), "inventory root must be a directory")
    except (OSError, ValueError) as exc:
        if isinstance(exc, Invalid):
            raise
        raise Invalid("inventory root unavailable") from None
    observations, inferences, issues = [], [], set()
    counts = {"directories_scanned": 0, "directory_attempts": 0,
              "files_read": 0, "bytes": 0, "entries": 0}
    seen_languages = set()

    def issue(path, reason):
        issues.add((path, reason))

    def fact(target, kind, value, path, signal):
        item = {"kind": kind, "value": value, "evidence": {"path": path, "signal": signal}}
        if item not in target:
            target.append(item)

    def infer(kind, value, path, signal):
        fact(inferences, kind, value, path, signal)

    def guards(path):
        chain = [root]
        relative = path.relative_to(root)
        for name in relative.parts[:-1]:
            chain.append(chain[-1] / name)
        result = []
        for parent in chain:
            info = parent.lstat()
            if _linked(info) or not stat.S_ISDIR(info.st_mode):
                raise OSError("unsafe parent")
            result.append((parent, info.st_dev, info.st_ino))
        return result

    def unchanged(parents):
        for path, device, inode in parents:
            info = path.lstat()
            if _linked(info) or (info.st_dev, info.st_ino) != (device, inode):
                raise OSError("parent changed")

    def read_package(path, relative):
        try:
            parents = guards(path)
            before = path.lstat()
            if _linked(before) or not stat.S_ISREG(before.st_mode) or before.st_nlink > 1:
                issue(relative, "unsafe file type or multiple hard links")
                return
            if before.st_size > LIMITS["file_bytes"]:
                issue(relative, "file byte limit")
                return
            if counts["bytes"] + before.st_size > LIMITS["total_bytes"]:
                issue(relative, "total byte limit")
                return
            flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
            descriptor = os.open(path, flags)
            with os.fdopen(descriptor, "rb") as stream:
                require(_identity(os.fstat(stream.fileno())) == _identity(before), "input changed")
                raw = stream.read(LIMITS["file_bytes"] + 1)
                require(_identity(os.fstat(stream.fileno())) == _identity(before), "input changed")
            unchanged(parents)
            require(_identity(path.lstat()) == _identity(before), "input changed")
            counts["files_read"] += 1
            counts["bytes"] += len(raw)
            if len(raw) > LIMITS["file_bytes"]:
                issue(relative, "file byte limit")
                return
            value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object,
                               parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
            if not isinstance(value, dict):
                raise ValueError()
            # Never echo arbitrary values, scripts, names, URLs or exception text.
            selected = []
            for field in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                dependencies = value.get(field, {})
                if not isinstance(dependencies, dict) or any(not isinstance(x, str) for x in dependencies.values()):
                    raise ValueError()
                for dependency in sorted(DEPENDENCIES.keys() & dependencies.keys()):
                    selected.append((field, dependency))
            fact(observations, "manifest-format", "JSON object", relative, "parsed package.json")
            for field, dependency in selected:
                fact(observations, "dependency", dependency, relative, field + "." + dependency)
                kind, name = DEPENDENCIES[dependency]
                infer(kind, name, relative, "declared dependency; not runtime verification")
        except (OSError, ValueError, UnicodeError, RecursionError, OverflowError):
            issue(relative, "unreadable, malformed or changed manifest")

    def descend(parts, name):
        if not parts:
            return name in DIRECTORIES or name in {".github", ".agents"}
        if parts == (".github",):
            return name == "workflows"
        if parts == (".agents",):
            return name == "skills"
        if parts == (".agents", "skills"):
            return bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name))
        if parts[0] in {".agents", ".github"}:
            return False
        return name in DIRECTORIES or (len(parts) == 1 and parts[0] in {"apps", "packages", "services"})

    def walk(path, parts):
        relative = "/".join(parts) or "."
        if counts["directory_attempts"] >= LIMITS["directories"]:
            issue(relative, "directory limit")
            return
        if counts["entries"] >= LIMITS["entries"]:
            issue(relative, "total entry limit")
            return
        counts["directory_attempts"] += 1
        try:
            parents = guards(path / "placeholder")
            entries = []
            with os.scandir(path) as iterator:
                while True:
                    if counts["entries"] >= LIMITS["entries"]:
                        issue(relative, "total entry limit")
                        return
                    try:
                        entry = next(iterator)
                    except StopIteration:
                        break
                    counts["entries"] += 1
                    if len(entries) >= LIMITS["entries_per_directory"]:
                        issue(relative, "directory entry limit")
                        return  # No order-dependent partial directory results.
                    entries.append(entry)
            unchanged(parents)
            counts["directories_scanned"] += 1
        except OSError:
            issue(relative, "unreadable or changed directory")
            return
        for entry in sorted(entries, key=lambda x: x.name):
            name = entry.name
            if name == ".git" and not parts:
                try:
                    info = entry.stat(follow_symlinks=False)
                    if _linked(info) or not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
                        issue(".git", "unsafe Git marker")
                    else:
                        fact(observations, "git-marker-presence", "present", ".git", "filesystem marker only")
                except OSError:
                    issue(".git", "unreadable Git marker")
                continue
            if (not SAFE_NAME.fullmatch(name) and name not in {".agents", ".github"}) or SENSITIVE.search(name):
                issue("/".join(parts) or ".", "unsafe or sensitive name excluded")
                continue  # Do not emit attacker-controlled/secret-bearing names.
            relative = "/".join((*parts, name))
            try:
                info = entry.stat(follow_symlinks=False)
                if _linked(info):
                    # Disclose only paths the inventory would otherwise inspect.
                    if descend(parts, name) or name in MANIFESTS | CONFIGS or Path(name).suffix in EXTENSIONS or (parts[:2] == (".agents", "skills") and name == "SKILL.md"):
                        issue(relative, "link or reparse point skipped")
                    continue
                if stat.S_ISDIR(info.st_mode):
                    if descend(parts, name):
                        fact(observations, "structure", name if name in DIRECTORIES else "supported directory", relative, "directory presence")
                        if len(parts) >= LIMITS["depth"]:
                            issue(relative, "depth limit")
                        else:
                            walk(Path(entry.path), (*parts, name))
                    continue
                if not stat.S_ISREG(info.st_mode):
                    if name in MANIFESTS | CONFIGS:
                        issue(relative, "unsupported file type")
                    continue
                if parts[:2] == (".agents", "skills"):
                    if len(parts) == 3 and name == "SKILL.md":
                        fact(observations, "installed-skill-manifest", "present", relative, "file presence only; no trust, activation or consent")
                    continue
                if name in MANIFESTS | CONFIGS:
                    fact(observations, "manifest" if name in MANIFESTS else "configuration", name, relative, "file presence only")
                    if name == "package.json":
                        read_package(Path(entry.path), relative)
                    if name in MANIFEST_LANGUAGES:
                        infer("language", MANIFEST_LANGUAGES[name], relative, "manifest filename only; content not parsed")
                    if name in CONFIG_SIGNALS:
                        infer(*CONFIG_SIGNALS[name], relative, "configuration filename only; not executed")
                    if name.startswith("next.config."):
                        infer("framework", "Next.js", relative, "configuration filename only; not executed")
                    if name.startswith(("vite.config.", "vitest.config.", "jest.config.", "playwright.config.")):
                        infer("tooling", name.split(".", 1)[0].capitalize(), relative, "configuration filename only; not executed")
                language = EXTENSIONS.get(Path(name).suffix)
                if language and language not in seen_languages:
                    seen_languages.add(language)
                    infer("language", language, relative, "source filename extension only; content not read")
            except OSError:
                issue(relative, "unreadable entry")

    walk(root, ())
    key = lambda item: json.dumps(item, sort_keys=True, ensure_ascii=True)
    observations.sort(key=key)
    inferences.sort(key=key)
    needs = {}
    for item in inferences:
        need = {"language": "language-aware engineering", "framework": "framework-aware engineering",
                "tooling": "test/build tooling assessment", "platform": "platform configuration assessment"}[item["kind"]]
        needs.setdefault(need, set()).add(item["evidence"]["path"])
    unknowns = ["Runtime behavior, dependency resolution, versions and compatibility are not verified.",
                "Installed skill files do not establish trust, activation or consent.",
                "Non-JSON configuration contents and unsupported project locations/formats are not interpreted.",
                "Git marker presence does not authenticate a repository; absence is not proof of no Git context."]
    if not inferences:
        unknowns.append("No supported technology signal observed; technology stack remains unknown.")
    return {"output_version": 1, "observations": observations, "inferences": inferences,
            "capability_needs": [{"need": name, "status": "inferred", "evidence": sorted(paths)} for name, paths in sorted(needs.items())],
            "unknowns": unknowns,
            "coverage": {"complete": False, "policy": "bounded allowlisted inventory; stable local tree required",
                         "limits": dict(LIMITS), "issues": [{"path": p, "reason": reason} for p, reason in sorted(issues)],
                         "excluded": ["arbitrary directories and file contents", "credentials and sensitive names", "Git metadata contents", "configuration/script execution", "network and external tools"],
                         "directories_scanned": counts["directories_scanned"], "files_read": counts["files_read"]}}
