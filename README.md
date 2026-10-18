# LittleDevTeam

LittleDevTeam ist ein Skill für die strukturierte Zusammenarbeit mit einem Coding-Agenten: erst Anforderungen und Architektur klären, dann einen überschaubaren Schritt umsetzen, prüfen und gemeinsam bewerten.

Der technische Skill-Name lautet **`architect-dev-team`**. Das Projekt und seine geplante Dokumentationswebsite heißen **LittleDevTeam**.

## Wie der Skill arbeitet

```text
Auftrag → Untersuchung → Spezifikation → Architektur → Freigabe
       → Umsetzung → Prüfung → Review → Freigabe → nächste Iteration
```

- Lean, Balanced und Rigorous passen den Aufwand an die Aufgabe an.
- Versionierte Vorschläge und konkrete Meilensteine machen Entscheidungen nachvollziehbar.
- Lokale Zustandsdateien halten Umfang, Entscheidungen und Prüfergebnisse fest.
- Python-Werkzeuge prüfen unter anderem Pakete, Zustände, Freigabebezüge und Quellcode-Snapshots.
- Zusätzliche Agenten werden nur eingesetzt, wenn sie verfügbar, erlaubt und für die Aufgabe sinnvoll sind.
- Externe Skills sind optionale Kandidaten mit Herkunftsnachweisen; ein Registry-Eintrag installiert oder aktiviert sie nicht.

Die Prüfwerkzeuge kontrollieren die Konsistenz lokaler Daten. Sie authentifizieren keine menschlichen Entscheidungen und ersetzen keine Berechtigungen des ausführenden Systems.

## Im Repository ausprobieren

```sh
git clone https://github.com/YoungJibbit95/ltd-skill.git
cd ltd-skill
```

Der vollständige Skill liegt unter [`.agents/skills/architect-dev-team`](.agents/skills/architect-dev-team/SKILL.md). In dieser Arbeitsumgebung ist er als `architect-dev-team` verfügbar. Ein möglicher Auftrag lautet:

```text
Nutze $architect-dev-team. Untersuche das Projekt und erstelle einen
Architekturvorschlag mit einem kleinen ersten Meilenstein. Zeige mir
den konkreten Vorschlag zur Freigabe, bevor du ihn implementierst.
```

Ein vollständiges Installationstutorial für andere Projekte und Umgebungen wird im Website-Projekt erarbeitet. Kopiere bei manueller Übernahme immer den gesamten Skill-Ordner einschließlich `scripts/ldt_core`.

## Lokal prüfen

Voraussetzungen: Python ab 3.10 und Git. Die Prüfwerkzeuge und Tests verwenden die Python-Standardbibliothek.

```sh
python -B .agents/skills/architect-dev-team/scripts/validate.py package .agents/skills/architect-dev-team
python -B .agents/skills/architect-dev-team/scripts/validate.py registry .agents/skills/architect-dev-team/registry/skills.json
python -B .agents/skills/architect-dev-team/scripts/validate.py registry .agents/skills/architect-dev-team/registry/index.json
python -B -m unittest discover -s tests -v
```

Die GitHub-Actions-Checks führen diese Prüfungen auf Windows und Linux mit Python 3.10 und 3.12 aus. Plattformabhängige Auslassungen werden im Testprotokoll ausgewiesen.

## Die Website als Demonstration

**Die LittleDevTeam-Website wird mit dem LittleDevTeam-Skill entwickelt und dient als nachvollziehbares Demonstrationsprojekt für seine Arbeitsweise.**

Geplant sind eine moderne Startseite, Dokumentation, ein praktischer Guide, ein Installationstutorial und eine Fallstudie zur Entstehung der Website. Die Fallstudie soll tatsächliche Planung, freigegebene Schritte und ausgeführte Prüfungen zeigen. Noch nicht umgesetzte Funktionen werden als geplant gekennzeichnet.

Der [Projektbrief](docs/website-brief.md) hält den Auftrag fest. Design, Technik und Umsetzungsschritte werden anschließend gemeinsam in der Planungsphase festgelegt. Eine Website ist noch nicht implementiert oder veröffentlicht.

## Entwicklungsstand und Orientierung

Dieses Repository startet als **Entwicklungsstand**, nicht als freigegebene V2-Veröffentlichung. Es enthält bereits den Skill, den gemeinsamen Python-Kern, Registry-Validierung für Schema 1 und 2 sowie Regressionstests. Vorhandener Code allein belegt keinen abgeschlossenen Review oder freigegebenen Meilenstein.

| Bereich | Einstieg |
| --- | --- |
| Skill und Arbeitsweise | [SKILL.md](.agents/skills/architect-dev-team/SKILL.md) |
| Python-Prüfwerkzeuge | [scripts/](.agents/skills/architect-dev-team/scripts/) |
| Vorlagen | [assets/](.agents/skills/architect-dev-team/assets/) |
| Arbeitsabläufe und Zustandsmodell | [references/](.agents/skills/architect-dev-team/references/) |
| Herkunft externer Skill-Kandidaten | [registry/](.agents/skills/architect-dev-team/registry/) |
| Regressionstests und historische Test-Orakel | [tests/](tests/) |
| Frühere V2-Entwürfe und Recherche | [design/](design/) |

Die Dokumente unter `design/` sind historische Vorschläge. Insbesondere CLI, Runtime-Adapter und erweiterte Rollenbeschreibungen dürfen nicht als vorhandene Produktfunktionen dargestellt werden. Lokale Entwicklungsprotokolle, Freigabeaufzeichnungen und Auswertungsläufe werden nicht mit veröffentlicht.

Eine Projektlizenz wurde noch nicht festgelegt. Lizenzangaben in der Registry betreffen die jeweils referenzierten Drittquellen und lizenzieren dieses Repository nicht.
