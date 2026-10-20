# LittleDevTeam

LittleDevTeam ist ein Skill für die strukturierte Zusammenarbeit mit einem Coding-Agenten: erst Anforderungen und Architektur klären, dann einen überschaubaren Schritt umsetzen, prüfen und gemeinsam bewerten.

Der technische Skill-Name lautet **`architect-dev-team`**. Das Projekt und seine geplante Dokumentationswebsite heißen **LittleDevTeam**.

## Wie der Skill arbeitet

```text
Auftrag → Intake → Untersuchung → Spezifikation → Architektur-Team
       → Task-Verträge → Projektansicht → Start-Freigabe
       → Umsetzung → Prüfung → Review → Integration → Freigabe → nächste Iteration
```

- Lean, Balanced und Rigorous passen den Aufwand an die Aufgabe an.
- Versionierte Vorschläge und konkrete Meilensteine machen Entscheidungen nachvollziehbar.
- Lokale Zustandsdateien halten Umfang, Entscheidungen und Prüfergebnisse fest.
- Python-Werkzeuge prüfen unter anderem Pakete, Zustände, Freigabebezüge und Quellcode-Snapshots.
- Zusätzliche Agenten werden nur eingesetzt, wenn sie verfügbar, erlaubt und für die Aufgabe sinnvoll sind.
- Externe Skills sind optionale Kandidaten mit Herkunftsnachweisen; ein Registry-Eintrag installiert oder aktiviert sie nicht.

Die Prüfwerkzeuge kontrollieren die Konsistenz lokaler Daten. Sie authentifizieren keine menschlichen Entscheidungen und ersetzen keine Berechtigungen des ausführenden Systems.

## Agentenausführung

Umsetzung und Review laufen als **echte Agenten** der Harness-Laufzeit, nicht als
Python-Stubs. Der Adapter in
[`scripts/ldt_core/runtime.py`](.agents/skills/architect-dev-team/scripts/ldt_core/runtime.py)
ruft die dokumentierte OpenCode-Schnittstelle auf:

```sh
opencode run --agent <agent> --model <provider/model> --format json <prompt>
```

| Rolle | Nativer Agent | Schreibzugriff |
| --- | --- | --- |
| Recherche | `explore` | keiner |
| Umsetzung | `general` | gemäß Vertrag |
| Kritik | `explore` | keiner |
| Architektur-Lead | `plan` | keine Edits |

Die Schreibgrenze des Kritikers wird durch die native Berechtigung erzwungen,
nicht durch eine Richtlinie. Jeder Lauf wird mit Session-ID, Agent, Modell und
Protokollfällen der Modell-Rückfallebene protokolliert. Die Unabhängigkeit
einer Prüfung ergibt sich aus zwei getrennten, verifizierbaren Sessions und
einem schreibgeschützten Kritiker-Agenten. Für das Profil `rigorous` ist
diese Evidenz hashgebunden zu binden; ein selbst deklariertes Feld genügt
dort nicht.

Ist die Laufzeit nicht erreichbar, meldet der Adapter ehrlich
`unavailable`. Es werden keine Befunde, keine Unabhängigkeit und keine
Prüfergebnisse erfunden.

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

### Workflow-Befehle

```sh
V=<skill>/scripts/validate.py
python $V runtime detect                       # Laufzeit, Agenten, Modelle
python $V runtime verify --session-id <id>     # Session-Evidenz
python $V intake <projekt>                     # Projektbrief
python $V arch-team <projekt> decompose        # Research-Verträge
python $V research <projekt> research-001 execute
python $V arch-team <projekt> integrate       # Architektur
python $V task-contracts <projekt> create-impl --task-id impl-001 --role "Backend" \
    --goal "…" --arch-version v1 --milestone M1 --acceptance "…" \
    --required-checks unit-tests --review-assignment critic-001
python $V task-contracts <projekt> create-critic --task-id critic-001 \
    --review-target impl-001 --arch-version v1 --milestone M1
python $V project-view <projekt> generate      # Projektansicht + Startfrage
python $V pair-exec <projekt> run-pair --impl-task-id impl-001 --critic-task-id critic-001
python $V integration <projekt> run            # Tests am Gesamtstand
```

Die End-to-End-Auswertung mit echten nativen Agenten liegt unter
[`tools/`](tools/). Sie benötigt die OpenCode-CLI und ist deshalb nicht Teil
der Standard-Regression.

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

Die Dokumente unter `design/` sind historische Vorschläge. Die `ldt`-CLI, ein Setup-Wizard, die Skill-Auswahl und die erweiterten Rollenbeschreibungen sind **nicht** umgesetzt und dürfen nicht als vorhandene Produktfunktionen dargestellt werden. Der Runtime-Adapter für OpenCode ist umgesetzt; eine entsprechende Codex-Anbindung ist strukturell vorbereitet, aber nicht verifiziert. Lokale Entwicklungsprotokolle, Freigabeaufzeichnungen und Auswertungsläufe werden nicht mit veröffentlicht.

Eine Projektlizenz wurde noch nicht festgelegt. Lizenzangaben in der Registry betreffen die jeweils referenzierten Drittquellen und lizenzieren dieses Repository nicht.
