<p align="center">
  <img src="docs/assets/readme-banner.svg" alt="LittleDevTeam. Architecture first. Build in steps." width="1280" />
</p>

<p align="center">
  <a href="https://github.com/YoungJibbit95/ltd-skill/actions/workflows/validate.yml"><img src="https://github.com/YoungJibbit95/ltd-skill/actions/workflows/validate.yml/badge.svg?branch=main" alt="Skill-Prüfungen auf main" /></a>
  <a href="https://github.com/YoungJibbit95/ltd-skill/actions/workflows/website.yml"><img src="https://github.com/YoungJibbit95/ltd-skill/actions/workflows/website.yml/badge.svg?branch=main" alt="Website-Prüfungen auf main" /></a>
  <a href="https://youngjibbit95.github.io/ltd-skill/de/docs/install/"><img src="https://img.shields.io/badge/Python-3.10%2B-ae91ed?style=flat&amp;logo=python&amp;logoColor=white&amp;labelColor=16152b" alt="Python 3.10 oder neuer" /></a>
  <a href="https://youngjibbit95.github.io/ltd-skill/en/"><img src="https://img.shields.io/badge/Docs-DE%20%7C%20EN-d99dc4?style=flat&amp;labelColor=16152b" alt="Dokumentation auf Deutsch und Englisch" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-88cfc7?style=flat&amp;labelColor=16152b" alt="Apache License 2.0" /></a>
</p>

<p align="center">
  <a href="https://youngjibbit95.github.io/ltd-skill/de/">Website</a> ·
  <a href="https://youngjibbit95.github.io/ltd-skill/de/docs/install/">Installation</a> ·
  <a href="https://youngjibbit95.github.io/ltd-skill/de/docs/guide/">Guide</a> ·
  <a href="https://youngjibbit95.github.io/ltd-skill/de/demo/">Demo</a> ·
  <a href="https://youngjibbit95.github.io/ltd-skill/en/">English docs</a>
</p>

## 🚀 Direkt in deinem Projekt starten

Öffne dein bestehendes Projekt in Codex und kopiere diesen Prompt in einen Chat. Codex übernimmt damit den vollständigen Skill in dein Projekt, prüft die Installation und beginnt anschließend mit der Planung deines Auftrags.

> [!TIP]
> Du brauchst keine Shell-Befehle anzupassen. Gib dein Ziel direkt unter dem Prompt an oder lass Codex danach fragen. Für die Paketprüfung braucht deine Umgebung Python ab 3.10.

```text
Richte LittleDevTeam in diesem Projekt ein.
Quelle: https://github.com/YoungJibbit95/ltd-skill
Commit: 9a062eb9de0990ce1074dd677d26e5a528ee14a0

Lies die Projektregeln und die Skill-Anweisungen. Übernimm den vollständigen
Ordner .agents/skills/architect-dev-team aus diesem Commit in denselben Pfad
meines Projekts, einschließlich scripts/ldt_core und aller Begleitdateien.
Wenn das Ziel bereits existiert, zeige mir die Unterschiede vor Änderungen.
Prüfe das Paket mit Python 3.10+ vom Projektstamm aus:
python -B .agents/skills/architect-dev-team/scripts/validate.py package .agents/skills/architect-dev-team

Nutze danach $architect-dev-team mit dem Profil Balanced für meinen Auftrag.
Frage nach meinem Ziel, falls es noch fehlt. Untersuche das Projekt und lege
mir einen Architekturvorschlag mit erstem Meilenstein und Prüfungen vor.
Beginne die Umsetzung nach meiner Freigabe des konkreten Vorschlags.
```

Der Prompt verwendet den dokumentierten Entwicklungsstand der [Installationsanleitung](https://youngjibbit95.github.io/ltd-skill/de/docs/install/). Codex erkennt neue Skills automatisch; falls der Skill nicht erscheint, starte Codex neu. Der Projektpfad `.agents/skills` ist in den [offiziellen Codex-Skill-Hinweisen](https://learn.chatgpt.com/docs/build-skills) beschrieben.


## 🪐 Was ist LittleDevTeam?

LittleDevTeam hilft dir, größere Entwicklungsaufgaben mit einem Coding-Agenten in prüfbare Schritte aufzuteilen. Du klärst Anforderungen, bewertest einen Architekturvorschlag und gibst einen konkreten Meilenstein frei. Nach der Umsetzung prüfst du das Ergebnis, bevor die nächste Iteration beginnt.

Der Skill heißt technisch `architect-dev-team`. Seine Anweisungen und Python-Prüfwerkzeuge liegen vollständig in diesem Repository.

| Was du brauchst | Was der Skill dafür vorsieht |
| --- | --- |
| Einen nachvollziehbaren Plan | Versionierte Architekturvorschläge und begrenzte Meilensteine |
| Übersicht nach einer Unterbrechung | Lokale Aufzeichnungen zu Umfang, Entscheidungen und Prüfungen |
| Belege für ein Ergebnis | Prüfbefehle, Quellcode-Snapshots und Review mit benannten Grenzen |
| Unterstützung bei größeren Aufgaben | Begrenzte Agentenaufträge, sofern die Umgebung sie erlaubt und unterstützt |


## 🧭 Erst im Beispiel-Repository ausprobieren

Du brauchst Git und eine Coding-Agent-Umgebung mit Skill-Unterstützung. Für die Prüfhilfen ist Python ab 3.10 nötig; zusätzliche Python-Pakete brauchst du nicht.

### 1. Repository öffnen

```sh
git clone https://github.com/YoungJibbit95/ltd-skill.git
cd ltd-skill
```

Öffne diesen Ordner in Codex. Der vollständige Skill liegt unter [`.agents/skills/architect-dev-team`](.agents/skills/architect-dev-team/SKILL.md). Lies vor dem ersten Einsatz seine Anweisungen. Für die Übernahme in ein anderes Projekt oder dein persönliches Skill-Verzeichnis nutze das [Installationstutorial für Windows, macOS und Linux](https://youngjibbit95.github.io/ltd-skill/de/docs/install/).

### 2. Einen kleinen Auftrag geben

```text
Nutze $architect-dev-team mit dem Profil Balanced.
Untersuche das Projekt und plane eine kleine Verbesserung an der Dokumentation.
Erstelle einen Architekturvorschlag mit einem ersten Meilenstein und passenden
Prüfungen. Zeige mir den konkreten Vorschlag zur Freigabe, bevor du ihn umsetzt.
```

### 3. Vorschlag bewerten und Ergebnis prüfen

Prüfe Umfang, Annahmen und Abnahmekriterien. Bitte bei Bedarf um eine Überarbeitung. Nach deiner Freigabe setzt der Agent den vereinbarten Schritt um und legt Änderungen, Prüfergebnisse und offene Punkte vor. Die nächste Iteration, ein Merge und eine Veröffentlichung benötigen jeweils die dafür geltende Freigabe.

Der [Praxisguide](https://youngjibbit95.github.io/ltd-skill/de/docs/guide/) führt dich durch diesen Ablauf. Die [interaktive Demo](https://youngjibbit95.github.io/ltd-skill/de/demo/) zeigt Freigabe, Überarbeitung und Review als lokale Simulation; sie führt keine Agenten aus.


## 🛠️ So läuft ein Meilenstein ab

<p align="center">
  <a href="https://youngjibbit95.github.io/ltd-skill/de/docs/workflow/"><img src="https://img.shields.io/badge/Lean-kleiner%20Umfang-88cfc7?style=flat&amp;labelColor=16152b" alt="Lean für kleinen Umfang" /></a>
  <a href="https://youngjibbit95.github.io/ltd-skill/de/docs/workflow/"><img src="https://img.shields.io/badge/Balanced-Standard-ae91ed?style=flat&amp;labelColor=16152b" alt="Balanced als Standard" /></a>
  <a href="https://youngjibbit95.github.io/ltd-skill/de/docs/workflow/"><img src="https://img.shields.io/badge/Rigorous-mehr%20Pr%C3%BCftiefe-d99dc4?style=flat&amp;labelColor=16152b" alt="Rigorous mit mehr Prüftiefe" /></a>
</p>

```mermaid
flowchart LR
    A[Auftrag untersuchen] --> B[Architektur vorschlagen]
    B --> C{Deine Freigabe}
    C -->|Überarbeiten| B
    C -->|Freigeben| D[Meilenstein umsetzen]
    D --> E[Prüfen und reviewen]
    E --> F[Ergebnis gemeinsam bewerten]
```

Lean, Balanced und Rigorous passen den Planungs- und Prüfaufwand an die Aufgabe an. Balanced ist der Standard. Freigaben bleiben in jedem Profil erforderlich.

Die Python-Hilfen prüfen unter anderem Pakete, Registry-Daten, lokale Zustände und die Bindung von Reviews an Quellcode-Snapshots. Sie können keine menschliche Entscheidung authentifizieren oder Systemberechtigungen durchsetzen. Externe Skills bleiben optionale Kandidaten: Ein Registry-Eintrag installiert oder aktiviert sie nicht.


## 🌌 Mit LittleDevTeam gebaut

Die Dokumentationswebsite entstand mit dem LittleDevTeam-Skill und demonstriert seine Arbeitsweise. Die [Fallstudie](https://youngjibbit95.github.io/ltd-skill/de/built-with-littledevteam/) zeigt tatsächliche Planung, Entscheidungen, Umsetzung und Prüfbelege.

Die Website enthält eine deutsche und englische Einführung, Installationsanleitungen, technische Referenz, Suche und die interaktive Simulation. Sie nutzt Astro, Starlight und lokal eingebundene Schriften im dunklen Nebula-Design. Die Dokumentation benennt den Skill-Quellstand, auf den sie sich bezieht.

Den Auftrag findest du im [Projektbrief](docs/website-brief.md), die Meilensteine im [Website-Plan](docs/website-plan.md). Die [Anleitung für Release und Wiederherstellung](docs/website-release.md) beschreibt den manuellen Veröffentlichungsweg und seine Grenzen. Veröffentlichung und vollständige W3-Abnahme sind getrennte Entscheidungen.

<details>
<summary>Website lokal starten</summary>

Voraussetzung: Node.js 24.

```sh
cd website
npm ci
npm run dev
```

Öffne die ausgegebene Adresse mit `/ltd-skill/de/` oder `/ltd-skill/en/`. Die [Website-Anleitung](website/README.md) beschreibt Produktionsbuild, Linkprüfung und Browserchecks.

</details>


## ✅ Skill lokal prüfen

Führe die Befehle im Repository-Stamm aus. Auf macOS und Linux heißt Python häufig `python3`; verwende den bei dir verfügbaren Python-3.10+-Befehl.

```sh
python -B .agents/skills/architect-dev-team/scripts/validate.py package .agents/skills/architect-dev-team
python -B .agents/skills/architect-dev-team/scripts/validate.py registry .agents/skills/architect-dev-team/registry/skills.json
python -B .agents/skills/architect-dev-team/scripts/validate.py registry .agents/skills/architect-dev-team/registry/index.json
python -B -m unittest discover -s tests -v
```

GitHub Actions prüft den Skill unter Windows und Linux mit Python 3.10 und 3.12. Plattformabhängige Auslassungen erscheinen im Testprotokoll. Kopiere bei manueller Installation immer den gesamten Skill-Ordner einschließlich `scripts/ldt_core`.


## 🗂️ Im Repository zurechtfinden

| Bereich | Einstieg |
| --- | --- |
| Skill-Anweisungen | [SKILL.md](.agents/skills/architect-dev-team/SKILL.md) |
| Python-Prüfwerkzeuge | [scripts/](.agents/skills/architect-dev-team/scripts/) |
| Architektur- und Zustandsvorlagen | [assets/](.agents/skills/architect-dev-team/assets/) |
| Arbeitsabläufe und Zustandsmodell | [references/](.agents/skills/architect-dev-team/references/) |
| Herkunft externer Skill-Kandidaten | [registry/](.agents/skills/architect-dev-team/registry/) |
| Regressionstests | [tests/](tests/) |
| Website-Quellcode | [website/](website/) |
| V2-Entwürfe und Recherche | [design/](design/) |


## 📌 Entwicklungsstand und Lizenz

Der Skill ist ein Entwicklungsstand. Die Dokumente unter `design/` sind Vorschläge und historische Recherche; die dort beschriebene CLI, Runtime-Adapter und erweiterten Rollen sind keine freigegebene V2. Ein vorhandenes Modul allein belegt keinen abgeschlossenen Review.

Lokale Freigabedateien, Entwicklungsprotokolle und Auswertungsläufe bleiben außerhalb von Git. Tatsächliche Codex-Erkennung wurde in den dokumentierten Installations-Smokes nicht geprüft.

Das Repository steht unter der [Apache License 2.0](LICENSE). Lizenzangaben in der Registry betreffen die referenzierten Drittquellen; die Website liefert die Lizenzen ihrer mitgelieferten Schriften mit.
