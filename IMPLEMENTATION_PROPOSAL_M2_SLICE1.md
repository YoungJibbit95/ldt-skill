# LittleDevTeam M2 — Erster funktionaler Durchstich: Umsetzungsvorschlag

**Zustand**: Entwurf zur Architektur-Freigabe | **Baseline**: M1a–M1c abgeschlossen (nur Doku/Validierung) | **Branch**: `m1d-roadmap-addendum`

---

## 1. Ziel und Scope

Ein **kleiner, aber vollständiger funktionaler Durchstich** durch den gesamten Projektstart-Workflow:

```
Intake → Architektur-Team & Recherche → Detaillierte Spezialaufträge
  → Projektansicht → Startfreigabe → Echtes Umsetzer/Kritiker-Paar
  → Integration & Tests → Ergebnisbericht
```

**Nicht enthalten** (separate, später freizugebende Teilpakete):
- Skill-Bibliothek/Registry-Erweiterungen (M3)
- Setup/Installation-Adapter (M5)
- Optionale `ldt`-CLI (M4)
- Erweiterte Delegation/Rollen (M2-Folge-Slices)

---

## 2. Bestandsaufnahme: Was existiert, was fehlt

| Komponente | Status | Wiederverwendung |
|------------|--------|------------------|
| **Shared Core** (`ldt_core`) | ✅ Voll implementiert, getestet | State, Scope, Snapshot, Registry, Inventory, Approvals, Package |
| **Validation CLI** (`validate.py`) | ✅ Voll implementiert, getestet | Alle Gates (`implement`, `review`, `advance`), Migration |
| **Architecture Template** | ✅ Vorhanden | Basis für versionierte Architektur-Dokumente |
| **State Template** (Schema 2) | ✅ Vorhanden | Phasen, Approvals, Checks, Review, Milestone-Policy |
| **Registry** (Schema 1 + 2) | ✅ 3 Kandidaten, alle `candidate` | Metadaten, Migration, Verifikation — **keine Installation** |
| **Inventory API** | ✅ Read-only, getestet | Projekt-Discovery (Stack, Configs, Skills) |
| **Approval Protocol** | ✅ Dokumentiert | Zwei Gates (Architektur, Iteration), Scope-Bindung, Waiver-Regeln |
| **Delegation Contract** | ✅ Dokumentiert | Kompakte Task-Verträge, unabhängige Review-Fallback |
| **Delivery Protocol** | ✅ Dokumentiert | Ein Milestone, Quality Gates, PR/Local Handoff |
| **Agent Config** | ⚠️ Nur `openai.yaml` | OpenCode-native Skill-Aktivierung |
| **Intake/Discovery Workflow** | ❌ Fehlt | **Neu**: Automatisierter Projekt-Brief mit Frageblöcken |
| **Architecture Team** | ❌ Fehlt | **Neu**: Lead + Research-Spezialisten mit Aufträgen |
| **Task Contract System** | ❌ Fehlt | **Neu**: Strukturierte Aufträge mit allen Pflichtfeldern |
| **Project View Generator** | ❌ Fehlt | **Neu**: Markdown+Mermaid aus versionierten Daten |
| **Start Gate** | ❌ Fehlt | **Neu**: Explizite „Soll ich starten?“ Frage mit Scope-Bindung |
| **Implementer/Critic Pair** | ❌ Fehlt | **Neu**: Echte Paar-Execution mit getrennten Artefakten |
| **Integration Test Runner** | ❌ Fehlt | **Neu**: Pflichtprüfungen am Gesamtstand |

---

## 3. Konkreter Umsetzungsplan: 4 Teilpakete (A–D)

Alle 4 Pakete gehören **zum ersten Durchstich** und werden **gemeinsam freigegeben**.

### Paket A: Intake & Projekt-Brief (Automatisierter Start)

**Ziel**: Bei vager Nutzeranweisung startet Planning statt Coding. Erzeugt versionierten Projekt-Brief.

**Neue Dateien**:
```
.agents/skills/architect-dev-team/
├── references/intake.md                    # Intake-Protokoll, Fragekatalog, Brief-Template
├── scripts/ldt_core/intake.py              # Core-Logik: Repository-Scan → Fragen → Brief
└── assets/brief.template.md                # Template für Projekt-Brief
```

**Funktionen**:
1. `intake.discover(root)` — nutzt bestehende `inventory()` + liest AGENTS.md, README, configs
2. `intake.identify_gaps(discovery)` — prüft: Nutzerziele, Akzeptanz, Funktionen, Daten/Sicherheit, Plattform, Design, Kosten
3. `intake.generate_questions(gaps)` — max. 3–5 Fragen pro Block, überspringt Beantwortetes
4. `intake.compile_brief(answers, discovery)` — schreibt `brief.template.md` → `.architect-dev-team/brief.md`
5. **Integration**: `validate.py` neuer Command `intake` (read-only, keine State-Änderung)

**Akzeptanzkriterien**:
- [ ] Vages Webprojekt (`"mach eine Website"`) → startet mit Fragen, nicht mit Code
- [ ] Präzise Kleinänderung (`"fix typo in README"`) → umgeht Intake, direkt Lean-Delivery
- [ ] Brief enthält: Ziel, Nicht-Ziele, Akzeptanzkriterien, Risiken, offene Entscheidungen
- [ ] Fragen nicht redundant; reversible Defaults als Annahmen markiert

---

### Paket B: Architektur-Team & Recherche-Aufträge

**Ziel**: Lead formuliert präzise Arbeitsaufträge; Research-Team liefert Spezifikationen, keine Vollarchitektur.

**Neue Dateien**:
```
.agents/skills/architect-dev-team/
├── references/architecture-team.md         # Rollen, Auftrags-Vorlagen, Research-Protokoll
├── scripts/ldt_core/arch_team.py           # Lead: Auftrags-Zerlegung, Research-Dispatch
├── scripts/ldt_core/research.py            # Research-Spezialist: Quellen, Versionen, Unsicherheit
└── assets/research.template.md             # Research-Ergebnis-Template
```

**Rollen** (nicht dauerhaft, auf Bedarf):
- **Architecture Lead**: Koordiniert, integriert, schreibt gemeinsames Dokument
- **System Architecture**: Grenzen, Datenflüsse, Tech-Entscheidungen, ADRs
- **Data/Interface**: Schemas, Contracts, Migration, Kompatibilität
- **Domain Intelligence** (falls nötig): Fachmodelle, Formeln, Einheiten, Invarianten
- **Security/Trust**: Auth-Grenzen, Secrets, Permissions, Supply Chain

**Research-Auftrag** (strukturiert):
```json
{
  "task_id": "research-001",
  "question": "Konkret zu beantwortende Frage",
  "sources": ["offizielle Doku URL", "Standard RFC", "Originalarbeit"],
  "required": ["Version", "Anwendbarkeit", "Unsicherheit", "widersprechende Befunde"],
  "output": "research.template.md"
}
```

**Integration**: Lead nutzt `arch_team.decompose(brief, architecture_template)` → erzeugt Research-Aufträge → Research-Spezialisten führen aus (nativ oder Subagent) → Lead integriert in `architecture.md`.

**Akzeptanzkriterien**:
- [ ] Lead schreibt **nicht** die komplette Architektur allein
- [ ] Research-Ergebnisse haben Quellen, Versionen, Unsicherheit
- [ ] Fachexperten liefern Spezifikationen/Formeln/Invarianten (kein Produktionscode)
- [ ] Architektur enthält nur nötige Komponenten, Datenflüsse, Verträge, ADRs, Milestones
- [ ] Unabhängiger Reviewer prüft folgenreiche Entscheidungen vor Startfreigabe

---

### Paket C: Detaillierte Spezialaufträge & Projektansicht

**Ziel**: Aus Architektur → Tasks mit allen Pflichtfeldern; lesbare Projektübersicht vor Start.

**Neue Dateien**:
```
.agents/skills/architect-dev-team/
├── references/task-contracts.md            # Vollständiges Vertrags-Schema, Handoff-Format
├── scripts/ldt_core/task_contracts.py      # Erstellung, Validierung, Serialisierung
├── scripts/ldt_core/project_view.py        # Markdown+Mermaid Generator aus State/Architecture
├── assets/task.template.md                 # Task-Vertrag Template
└── assets/project-view.template.md         # Projektansicht Template (MD + Mermaid)
```

**Task-Vertrag (Pflichtfelder laut Arbeitsanweisung §6)**:
```json
{
  "task_id": "impl-001",
  "role": "Backend Specialist",
  "goal": "Konkretes Einzelergebnis",
  "architecture_version": "v1.2",
  "milestone_id": "M1",
  "base_revision": "abc123...",
  "contract_refs": ["contract-api-001", "contract-db-001"],
  "input_paths": ["src/api/", "specs/openapi.yaml"],
  "dependencies": ["research-001", "task-contract-002"],
  "allowed_actions": ["write:src/api/**", "read:specs/**"],
  "file_ownership": {"src/api/users.py": "impl-001"},
  "acceptance": ["POST /users returns 201", "validation rejects invalid email"],
  "required_checks": ["unit-tests", "contract-test"],
  "skill_pins": ["fastapi@49f948f"],
  "model_profile": "medium",
  "resource_budget": {"tokens": 50000, "time_seconds": 300},
  "review_assignment": "critic-001",
  "escalation": ["scope_change", "missing_decision", "security_risk"]
}
```

**Projektansicht** (generiert aus `state.json` + `architecture.md` + `brief.md`):
- Ziel & wichtigste Funktionen
- Komponenten-/Datenflussdiagramm (Mermaid) + Text-Alternative
- Erste Meilensteine mit Abhängigkeiten
- Geplante Rollen, Tasks, Review-Zuordnung
- Skills (Installations-/Freigabestatus), Modelle
- Wesentliche Risiken, offene Entscheidungen, Pflichtprüfungen, nächste Aktion
- **Status-Markierung**: `Entwurf` / `Geprüft` / `Genehmigt` / `Umgesetzt`

**Startfreigabe**: Nach Projektansicht → **explizite Frage**:  
> „Soll ich den ersten beschriebenen Meilenstein **M1** mit diesem Plan, Team, Skills und Prüfpolitik starten?“

**Akzeptanzkriterien**:
- [ ] Jeder Task-Vertrag hat alle Pflichtfelder
- [ ] Projektansicht aus versionierten Daten, nicht aus Konversation
- [ ] Mermaid-Diagramm + lesbare Textalternative
- [ ] Startfrage verknüpft exakte Architektur, Scope, Prüfpolitik
- [ ] Skill-Auswahl/Installation/Rechte separate Zustimmungen (kein „Ja zu allem“)

---

### Paket D: Umsetzer/Kritiker-Paar → Integration & Tests

**Ziel**: Echtes Paar mit getrennten Artefakten; Integration am Gesamtstand; finales Reporting.

**Neue Dateien**:
```
.agents/skills/architect-dev-team/
├── references/implementation.md            # Paar-Protokoll, Reparatur-Schleifen, Eskalation
├── scripts/ldt_core/pair_execution.py      # Dispatcher: Implementierer + Kritiker
├── scripts/ldt_core/integration.py         # Integration, Architektur-Konformität, Final-Tests
└── assets/integration-report.template.md   # Ergebnisbericht Template
```

**Ablauf (nach Startfreigabe)**:
1. **Verträge bereitstellen** → genehmigte Skills laden (nur konsentierte)
2. **Implementierer** arbeitet nach Vertrag + passende Tests
3. **Deterministische Prüfungen** (Unit, Contract, Lint, Type)
4. **Kritiker** (eigenständiger Agent/Session):
   - Erhält: Requirements, Spec, zu prüfende Artefakte (NICHT Gedankengang des Implementierers)
   - Prüft: Anforderungen, Fehlerszenarien, folgt Schwachstellen nach
   - Belegt: Datei/Zeile, Reproduktion, Referenz, Test
   - **Schreibt keine Produktionsdateien**; Tests nur in genehmigten isolierten Bereichen
5. **Reparatur-Schleife**: Blocker / wichtige Reparaturen / optionale Verbesserungen
   - Max 2 gezielte Reparaturrunden pro Befundgruppe → dann Lead bewertet
6. **Bereichsabnahme** → **Integration** (Lead oder Integration Engineer)
   - Schnittstellen, Fehlerbehandlung, ausführbarer Gesamtstand
7. **Architecture Lead** prüft: Architektur vs. Fachverträge vs. Implementierung
8. **Finale Pflichtprüfungen** am Gesamtstand (Integration, E2E, Security, Perf)
   - Veränderte Integrations-Änderungen → betroffene Reviews invalidieren → erneut prüfen
9. **Ergebnisbericht**: Lauffähiges Ergebnis/Demo, Revision, erfüllte Kriterien, Testresultate, Review-Unabhängigkeit, offene Risiken, Rollen/Skills/Modelle, Aufwand

**Modell-Profile** (Rollen-basiert, nicht hardcoded):
| Rolle | Bevorzugtes Profil | Begründung |
|-------|-------------------|------------|
| Lead / Architecture Lead | High (stärkstes freigegebenes, nutzbares Modell) | Anspruchsvolle Planung, Entscheidungen |
| Implementierer (klare Verträge) | Medium | Standard für klare Verträge; High bei Komplexität |
| Kritiker | Medium/High nach Risiko | Security/Math/Architektur → starkes Modell |
| Extraktion/Formatierung | Low (schnell, günstig) | Routine-Zusammenfassungen |

**Akzeptanzkriterien**:
- [ ] Echtes Paar: Unterschiedliche Session-IDs/Artefakte belegen Trennung
- [ ] Kritiker findet und repariert absichtlich eingebauten Fehler
- [ ] Widersprüchliche Reviews → begründete Klärung, keine Mehrheitsabstimmung
- [ ] Reparatur-Schleife: max 2 Runden, dann Lead-Eskalation
- [ ] Integration führt Prüfungen am **Gesamtstand** aus (grünes Teilpaket ≠ funktionierende App)
- [ ] Veraltete Reviews / geänderte Pflichtprüfungen blockieren Fortschritt
- [ ] Bericht zeigt: Revision, Kriterien, Tests, Unabhängigkeit, Risiken, Aufwand

---

## 4. Betroffene Bestandsdateien (Änderungen)

| Datei | Art der Änderung |
|-------|------------------|
| `scripts/validate.py` | + Commands: `intake`, `brief`, `project-view`, `pair-run`, `integrate` (alle read-only bis Gate) |
| `scripts/ldt_core/__init__.py` | + Exports: `intake`, `arch_team`, `research`, `task_contracts`, `project_view`, `pair_execution`, `integration` |
| `scripts/ldt_core/common.py` | + Shared Exceptions, Dataclasses für Task/Research/Brief |
| `references/architecture.md` | Ergänzung: Research-Team, Task-Vertrag-Referenz, Projektansicht |
| `references/approvals.md` | Ergänzung: Start-Gate als Teil von Architecture-Approval |
| `references/delegation.md` | Ergänzung: Paar-Protokoll, Reparatur-Schleifen, Eskalation |
| `references/delivery.md` | Ergänzung: Integration, Architecture-Conformance, Final-Tests |
| `assets/architecture.template.md` | + Sections: Research-Ergebnisse, Task-Vertrag-Liste, Projektansicht-Ref |
| `assets/state.template.json` | + Fields: `brief`, `research_results`, `task_contracts`, `project_view`, `pair_results` |

---

## 5. Vertrags-Änderungen (Breaking/Non-Breaking)

| Vertrag | Änderung | Breaking? |
|---------|----------|-----------|
| **State Schema 2** | + `brief`, `research_results`, `task_contracts`, `project_view`, `pair_results` | Nein (optional, null initial) |
| **Milestone.required_checks** | Muss nun `pair_review` + `integration_tests` enthalten für Balanced/Rigorous | Ja — **erfordert neue Architecture-Approval** |
| **Approval Evidence** | Start-Gate Decision (`kind: "start"`) bindet exakte Architektur + Task-Contracts | Nein (neuer Decision-Type) |
| **Review Independence** | Rigorous erzwingt `independence: "independent"` für Paar-Review | Ja — **erfordert neue Architecture-Approval** |

> **Wichtig**: Diese Vertrags-Änderungen sind **Teil des Durchstichs** und werden **mit der Architektur-Freigabe dieses Vorschlags** genehmigt. Keine stille Migration.

---

## 6. Harness-Grenzen & Realistische Annahmen (OpenCode, Stand 2026-10-20)

| Fähigkeit | Status | Workaround im Durchstich |
|-----------|--------|--------------------------|
| **Native Subagents** | ✅ Verfügbar (`opencode` agents) | Echte Subagents für Implementierer/Kritiker nutzen |
| **Plan Mode** | ✅ Verfügbar | Plan-Phase nutzt native Plan-Modus; Implementierung erst nach Gate |
| **Model Selection** | ✅ Via `opencode models` | Rollen-Profile → verfügbare Modelle mappen (siehe Tabelle oben) |
| **Permissions** | ✅ Granular | Task-Vertrag `allowed_actions` → Permission-Mapping |
| **Skill Discovery** | ✅ `.agents/skills/` | Bestehender Pfad wird nativ erkannt |
| **Nested Delegation** | ⚠️ Begrenzt | Master startet Subagents direkt; keine rekursive Delegation |
| **Concurrency Limit** | ⚠️ Unbekannt | Initial max 3 parallele Spezialisten (konfigurierbar) |
| **Codex-Kompatibilität** | 🔄 Strukturell | Shared Core (`ldt_core`) ist harness-neutral; CLI/Adapter später |

**Offene Fragen an Nutzer** (Entscheidungsrelevant):
1. **Modell-Zuordnung**: Sollen wir die oben genannte Profil-Tabelle als Default nehmen, oder willst du konkrete Modell-IDs (z. B. `opencode/nemotron-3.5-super-vl-free@high` für Lead) festlegen?
2. **Subagent-Verfügbarkeit**: Soll der Durchstich **echte Subagents** nutzen (bevorzugt) oder **sequenzielle Rollen-Pässe** mit `self`-Label als Fallback?
3. **Reparatur-Budget**: 2 Runden pro Befundgruppe OK, oder andere Zahl?
4. **Projektansicht-Format**: Markdown+Mermaid + Text-Alternative ausreichend, oder auch HTML-Export gewünscht (späteres Paket)?

---

## 7. Abnahmekriterien für Freigabe dieses Durchstichs

Alle Kriterien müssen **demonstrierbar** erfüllt sein (nicht nur dokumentiert):

| # | Kriterium | Nachweis |
|---|-----------|----------|
| **A1** | Vages neues Webprojekt startet mit Fragen/Planung, nicht mit Anwendungscode | E2E-Test: Input `"baue eine Todo-App"` → Output: Brief mit Fragen, kein Code |
| **A2** | Präzise Kleinänderung vermeidet unnötige Architektur-/Agentenlast | E2E-Test: Input `"fix typo in README.md"` → Lean-Delivery, kein Intake |
| **A3** | Architecture-Research, detaillierte Aufträge, Ergebnisübergaben sind nachweisbar | Artefakte: `brief.md`, `research/*.md`, `task_contracts/*.json`, `architecture.md` |
| **A4** | Echtes Umsetzer/Kritiker-Paar findet & repariert absichtlich eingebauten Fehler | Fixture: Bug in `calc.py` → Kritiker findet, Implementierer repariert, Tests grün; **getrennte Session-IDs** |
| **A5** | Widersprüchliche Reviews werden begründet geklärt, nicht überstimmt | Test: Kritiker A sagt „unsicher“, Kritiker B sagt „ok“ → Lead entscheidet mit Begründung |
| **A6** | Neues Fachprojekt prüft Einheiten, Grenzfälle, Referenzwerte | Test: Numerisches Modul → Domain-Research liefert Einheiten/Toleranzen → Tests prüfen diese |
| **A7** | Planmodus & direkte Agent-Einstiege umgehen keine Schreib-/Approval-Grenzen | Test: Plan-Agent versucht Write → verweigert; nur nach `implement` Gate erlaubt |
| **A8** | Abgelehnte Installation, manipulierte Skills, Versionswechsel, ungültige Lizenz → korrekt behandelt | Registry-Tests decken ab; Integration: Install-Versuch ohne Consent → Block |
| **A9** | Modelle/Varianten, Quota-Fallback, Ressourcenlimit, ausgeschöpfte Reparaturschleifen funktionieren | Test: Mock-Provider mit Quota-Error → Fallback-Modell genutzt; 3. Reparatur → Eskalation |
| **A10** | Integration führt Prüfungen am Gesamtstand; veraltete Reviews blockieren | Test: Integration ändert Interface → betroffener Review invalidiert → Neureview gefordert |
| **A11** | Abbruch/Resume, voller Datenträger, konkurrierende Änderungen, Windows-Pfade berücksichtigt | State-Migration-Tests + Snapshot-Tests decken ab; Windows-symlink Tests skipped (dokumentiert) |
| **A12** | Native Oberfläche & CLI (falls implementiert) erzeugen gleiche Workflow-Ergebnisse | Noch nicht im Durchstich; CLI folgt in M4-Paket |

---

## 8. Nächste Schritte nach Freigabe

Nach deiner **expliziten Architektur-Freigabe** für diesen Vorschlag:

1. **Implementierung** der 4 Pakete (A–D) in der angegebenen Reihenfolge
2. **Echte Tests** mit Fixtures (absichtliche Bugs, widersprüchliche Reviews, Quota-Fallback)
3. **Selbstständige Reparatur-Schleifen** innerhalb genehmigten Scopes
4. **Stopp** nur bei echtem Eskalationsgrund (Scope-Änderung, fehlende Entscheidung, Budget, Security-Risiko, Stillstand, unerfüllbares Pflichtkriterium)
5. **Ergebnisbericht** mit lauffähigem Demo, Revision, Tests, Unabhängigkeit, Risiken

**Keine** automatischen Folge-Meilensteine. Nächster Meilenstein (M2-Slice 2: erweiterte Delegation, M3: Skill-Auswahl, M4: CLI, M5: Installation) braucht **eigene Architektur-Freigabe**.

---

## 9. Fragen zur Freigabe

Bitte prüfe und gib explizit frei:

1. **Scope**: Sind Pakete A–D als **ein** Durchstich korrekt, oder soll etwas herausgelöst werden?
2. **Vertrags-Änderungen**: State-Schema-Erweiterungen, neue `required_checks` (`pair_review`, `integration_tests`), neuer Approval-Type `start` — akzeptiert?
3. **Modell-Profile**: Obige Default-Tabelle OK, oder konkrete Modell-IDs gewünscht?
4. **Subagents**: Echte Subagents für Paar (bevorzugt) oder sequenzieller Fallback?
5. **Reparatur-Budget**: 2 Runden pro Befundgruppe OK?
6. **Projektansicht**: Markdown+Mermaid+Text ausreichend für ersten Durchstich?

**Antwort mit „Freigegeben: [Punkte 1–6 bestätigt/angepasst]“ startet die Implementierung.**