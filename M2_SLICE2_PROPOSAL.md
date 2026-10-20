# M2 Slice 2 — Intelligent Team Orchestration & Developer Experience

**Arbeitsentwurf zur Architekturfreigabe** | 20. Oktober 2026
**Repository**: `F:\Coding\LittleDevTeamSkill` | **Basis**: M2 Slice 1 abgeschlossen (Advance-Gate bestanden)

> **Nicht implementiert.** Dieses Dokument ist ein Vorschlag. Umsetzung erst
> nach ausdrücklicher Freigabe von Architektur und Umfang.

---

## 0. Ausgangslage: M2 Slice 1 Status

| Nachweis | Ergebnis |
|----------|----------|
| Vollständige Regression (`unittest discover -s tests`) | **201 Tests, 0 Fehler, 5 dokumentierte Skips** |
| Verifikationslauf (6 Schritte) | 6/6 OK, inkl. M1a-Differentialorakel |
| Native Agenten | Implementer `general` / Kritiker `explore`, getrennte verifizierte Sessions |
| Unabhängigkeit | Aus Runtime-Berechtigungen abgeleitet, hashgebunden belegt |
| Start-Gate | Durchgesetzt, `fail closed` an den Artefakten auf der Platte |
| Snapshot | `8e82438ae68db5259cffc4ac32b63d46cb7686943a13210fa7dd8315ea7684ee` (78 Dateien) |

**Zwei unabhängige Review-Runden** durch ein natives `explore`-Subagent:
erste Runde 19 Befunde (davon 1 Blocker), Reparaturrunde, zweite Runde
`approve_with_findings` mit 2 behauptungsrelevanten Punkten, die behoben wurden.

**Offene Limitierungen (aus dem Abschlussbericht übernommen, unverändert)**
- Keine effiziente Modellallokation
- Keine durchgehende tiefe Kritikabdeckung
- **Kein erfolgreich durchlaufener echter Agenten-Reparaturlauf**
- Keine verifizierte native Codex-Ausführung
- Keine vollständige automatische Skill-Auswahl
- Keine interaktive CLI-Integration

Slice 2 adressiert genau diese Punkte — mit Ausnahme der Codex-Ausführung,
die eine eigene Freigabe braucht.

---

## 1. Gemessene Ausgangslage (keine Vermutungen)

Eine echte Paar-Ausführung wurde instrumentiert
(`tools/measure_tokens.py`, Session `ses_ea7d24e62ffe2km7bNrHe468PR` /
`ses_ea7cc0c40ffe4n4d1yf58nWVMK`).

### 1.1 Was der Implementierer tatsächlich tat

| Kennzahl | Wert |
|----------|------|
| Modellereignisse | 102 (`step_start` 28, `tool_use` 41, `step_finish` 27) |
| Werkzeugaufrufe | 41: `shell` 26, `read` 8, `write` 3, `edit` 2, **`edit:error` 2** |
| Input-Tokens (Summe je Schritt) | 39 782 |
| Output-Tokens | 10 375 |
| Reasoning-Tokens | 14 444 |
| Cache-Reads | 721 014 |
| Textausgabe | 2 952 Zeichen |

### 1.2 Was der Kritiker tatsächlich tat

| Kennzahl | Wert |
|----------|------|
| Modellereignisse | 58 (`step_start` 13, `tool_use` 25, `step_finish` 12) |
| Werkzeugaufrufe | 25: `read` 15, `shell` 8, **`write:error` 2** |
| Input-Tokens | 43 543 |
| Output-Tokens | 6 098 |
| Textausgabe | 13 632 Zeichen |

### 1.3 Kostenzuordnung je Schritt (Auszug, echte Zahlen)

**Implementierer**

| Schritt | Input | Output | Bemerkung |
|---------|-------|--------|-----------|
| 1 | 4 445 | 102 | Erstkontext (Vertrag + Prompt) |
| 5 | **9 381** | 188 | größter Einzelbeitrag: ein sehr großes Werkzeugergebnis |
| 10 | 2 962 | 683 | |
| 17–22 | 1 744 ges. | **7 657** | die strukturierte Ergebnisausgabe des Agenten |
| 23–27 | 3 167 | 785 | ruhiger Ausgang |

**Kritiker**

| Schritt | Input | Output | Bemerkung |
|---------|-------|--------|-----------|
| 1 | 2 190 | 159 | Erstkontext |
| 4 | 6 774 | 215 | große Dateilesung |
| 5 | **11 596** | 237 | größter Einzelbeitrag: erneutes vollständiges Lesen |
| 12 | 6 918 | 2 774 | die strukturierte Prüfausgabe |

### 1.4 Daraus abgeleitete Befunde

| # | Befund | Beleg |
|---|--------|-------|
| T-1 | **Der Prompt ist nicht der Kostentreiber.** Der Erstkontext kostet 4 445 (Implementer) bzw. 2 190 (Kritiker) Input-Tokens, also 11 % bzw. 5 % der Gesamtsumme. | Schritt 1 oben |
| T-2 | **Der Kostentreiber sind einzelne sehr große Werkzeugergebnisse.** 3 Schritte tragen 27 751 der 83 325 Input-Tokens beider Rollen (33 %). | Schritt 5 / 4+5 |
| T-3 | **Die Input-Kosten wachsen mit der Schrittzahl**, weil jeder Schritt den akkumulierten Kontext erneut mitschickt. 27 bzw. 12 Schritte bei 39 782 bzw. 43 543 Input-Tokens. | Schrittfolgen |
| T-4 | **Der Kritiker liest dieselben Dateien erneut**, die der Implementierer gerade geschrieben hat: 15 `read` + 8 `shell`, aber nur 13 632 Zeichen Antwort. | Werkzeugzählung |
| T-5 | **Die strukturierte Ausgabe kostet real.** 7 657 Output-Tokens des Implementierers und 2 774 des Kritikers entfallen auf das JSON-Ergebnisformat inkl. Erzähltext. | Schritt 17–22 / 12 |
| T-6 | **Zwei `edit:error` sind Retries** durch CRLF-Zeilenenden — der Agent meldete selbst „the edit tool can't match this CRLF file". | Werkzeugzählung |
| T-7 | **Der Kritiker versuchte zweimal zu schreiben und wurde blockiert** (`write:error`). Die native Berechtigung wirkt — aber die M2-Slice-1-Spezifikation verspricht dem Kritiker, Tests unter `tests/critic/` anzulegen. Das ist mit `explore` **nicht ausführbar**. | Werkzeugzählung |
| T-8 | **Der Kritiker kostet fast so viel Input wie der Implementierer** (43 543 vs. 39 782) bei 1/3 der Tool-Aufrufe — sein Modell war das stärkere (`nemotron-3.5-super-vl-free`). | Gesamtsummen |

**Konsequenz**: Slice 2 muss den **Kontextfluss** ändern, nicht die Promptgröße.
Der Hebel liegt bei (a) vorkomponierten Kontextbündeln, (b) diff-begrenzter
Übergabe an den Kritiker, (c) einem strengen Ausgabeformat und (d) dem
Modellprofil je Rolle.

---

## 2. Slice-2-Ziele

1. **Echte Rollenhierarchie**: Bereichsleads (Department Leads) koordinieren
   Aufgaben wirklich — prüfen, verfeinern, zerlegen, Reviews anfordern.
2. **Effektive Kritik**: strukturierte, evidenzbasierte Kritik statt
   „Session existierte".
3. **Reparaturlauf real belegt**: ein E2E-Szenario, in dem ein echter
   Kritiker einen echten Defekt findet, ein echter Reparaturauftrag entsteht
   und die Integration danach grün ist.
4. **Messbar geringere Tokenkosten** bei gleicher Review-Qualität.
5. **Ein Sprachbefehl startet den Workflow** — ohne acht Python-Aufrufe.
6. **Vorbereitete Schnittstelle** zur Skill-Bibliothek (M3), ohne deren
   Umsetzung vorwegzunehmen.

---

## 3. Vorgeschlagene Umsetzungsschnitte

Jeder Schnitt ist eigenständig prüfbar. Reihenfolge = Abhängigkeit.

---

### Schnitt S1 — Rollenverträge & Koordinationskern

**Ziel**: Bereichsleads werden zu echten Koordinatoren. Der Master Lead bleibt
die einzige Koordinationsautorität.

**Umfang**
- Neue Vertragsart `LeadContract` (Erweiterung von `TaskContract`, keine neue Zustandsmaschine)
- Neue Rolle `department_lead` im Runtime-Mapping → nativer Agent `general` mit Lead-Aufgaben
- Zerlegungslogik: Lead nimmt einen Zielauftrag, prüft Architektur-Abhängigkeiten,
  erzeugt Spezialistenverträge, prüft die Rückgaben, fordert begrenzte Korrektur an
- Rückgabekanal: `LeadResult` mit integrierten Teilergebnissen

**Betroffene Dateien**
```
scripts/ldt_core/task_contracts.py   (LeadContract, Fabrik, Validierung)
scripts/ldt_core/pair_execution.py   (Lead-Ausführung, Delegation an Sub-Spezialisten)
scripts/ldt_core/runtime.py          (Rolle "department_lead" -> "general")
references/delegation.md             (10-Schritte-Vertrag des Bereichsleiters)
references/task-contracts.md         (LeadContract-Feldtabelle)
assets/task.template.md              (Lead-Abschnitt)
scripts/validate.py                  (Befehl "lead")
```

**Benötigte Laufzeitfähigkeiten**: native Subagenten (`general`), keine
neue Modellart, keine zusätzlichen Berechtigungen.

**Abnahmekriterien**
1. Ein Bereichsleads-Auftrag mit 3 Teilaufgaben erzeugt 3 Spezialistenverträge
   mit eindeutiger Dateieigentümerschaft, ohne überlappende Pfade.
2. Der Lead weist fehlende Informationen (fehlende Architekturgrundlage,
   unklare Schnittstelle) zurück, statt sie zu erfinden.
3. Der Lead prüft die Rückgabe jedes Spezialisten gegen dessen
   Akzeptanzkriterien und fordert bei Abweichung eine begrenzte Korrektur an.
4. Der Lead liefert ein integriertes Ergebnis; der Master Lead bleibt der
   einzige, der Umfang, Freigaben und Integration verantwortet.
5. Kein dauerhafter Rollenbestand: ohne Zielauftrag wird kein Lead gestartet.

**E2E-Tests**
- 1 Department Lead + 2 Spezialisten + 1 Kritiker, echte Agenten, getrennte Sessions
- Lead fordert genau eine Korrekturrunde an, danach Abnahme
- Rückgabe enthält die Vertrags-IDs und die Prüfergebnisse je Spezialist

**Sicherheit**
- Der Lead erhält Schreibrechte nur für seine eigenen Koordinationsartefakte.
- Dateieigentümerschaft wird vor jedem Start auf Überschneidung geprüft.
- Der Lead darf keine Freigaben erzeugen; `kind: "start"` bleibt beim Menschen.

**Kompatibilität**: `TaskContract` bleibt unverändert gültig; `LeadContract` ist
eine Unterklasse mit zusätzlichen Feldern. Schema 2 bleibt gültig, keine
neuen Pflichtfelder in `state.json`.

**Kosten/Kontext**: +1 Lead-Session pro Bereich. Erwartete Einsparung: der Lead
liest die Spezialistenergebnisse einmal statt dreifacher Lesevorgänge.

**Ausgeschlossen**: rekursive Delegation, Abteilungs-Erstaufbau, Skill-Auswahl.

---

### Schnitt S2 — Strukturierte Kritikqualität

**Ziel**: Eine Prüfung besteht nicht, weil eine Session existierte, sondern
weil sie belegte Arbeit geleistet hat.

**Umfang**
- Neues Ausgabeschema `CriticReport`:
  `requirements_checked`, `files_inspected`, `test_evidence_reviewed`,
  `defects` (oder `verified_non_findings`), `unchecked_areas`, `confidence`,
  `limitations`, `recommendation`
- **Gate**: Eine Kritik ohne `requirements_checked` **und** `files_inspected`
  gilt als unvollständig und blockiert die Abnahme.
- **Schwellenwert**: `confidence: "low"` oder nicht leeres `unchecked_areas`
  erzwingt eine zweite, engere Prüfrunde (max. 1, innerhalb des
  Zwei-Runden-Budgets).
- Der Kritiker erhält **nur** die geänderten Pfade und den Diff, nicht das
  ganze Repository (siehe T-4).

**Betroffene Dateien**
```
scripts/ldt_core/pair_execution.py   (CriticReport, Gate, Diff-Übergabe)
scripts/ldt_core/task_contracts.py   (CriticReport-Felder, Validierung)
assets/research.template.md          (Struktur wiederverwendet)
references/implementation.md         (Kritik-Qualitätsregeln)
references/task-contracts.md
scripts/validate.py                  (Befehl "critic-report" zur Prüfung)
```

**Benötigte Laufzeitfähigkeiten**: unverändert. Der native read-only-Agent
bleibt; nur die Eingabe wird verkleinert.

**Abnahmekriterien**
1. Ein `CriticReport` ohne `requirements_checked`/`files_inspected` wird
   abgelehnt (deterministischer Test).
2. Ein `CriticReport` mit geprüften Anforderungen, geprüften Dateien,
   geprüfter Testevidenz und Befunden wird angenommen.
3. `confidence: "low"` mit nicht leeren `unchecked_areas` löst genau eine
   zusätzliche, engere Prüfrunde aus.
4. Die Übergabe an den Kritiker enthält den Diff statt des Volltexts; die
   gelesenen Bytes sinken messbar (Schwellenwert in S4).
5. Ein Kritiker, der `write` versucht, wird weiterhin nativ blockiert.

**E2E-Tests**
- Kritiker findet den eingeplanten Defekt und liefert einen vollständigen Bericht
- Ein leerer Bericht blockiert die Abnahme
- Der enge Zweitlauf prüft nur die offenen Bereiche

**Sicherheit**
- Der Kritiker bleibt read-only; `CriticReport` enthält keine Geheimnisse.
- Die Evidenz wird in die Session-Bewertung übernommen (Bezug über `session_id`).

**Kompatibilität**: Die bestehende `independence`-Prüfung bleibt; der Report
ist eine **zusätzliche** Bedingung, keine Ersetzung.

**Kosten/Kontext**: Die Diff-Übergabe senkt die Kritiker-Input-Tokens
messbar (Ziel: ≥ 40 % weniger Input als die 43 543 aus §1.2).

**Ausgeschlossen**: automatische Bewertung der Kritikqualität durch ein Modell.

---

### Schnitt S3 — Realer Reparaturlauf (E2E)

**Ziel**: Der Reparaturlauf wird mit echten Agenten belegt, nicht nur
deterministisch getestet.

**Umfang**
- Neues Szenario `tools/e2e_repair.py`:
  1. Fixture mit **einem** Defekt, den das Akzeptanzkriterium **nicht** abdeckt
     (z. B. Groß-/Kleinschreibung bei der Duplikatprüfung).
  2. Der Auftrag enthält nur das Kriterium „exakter Duplikat wird abgelehnt".
  3. Der Implementierer behebt das exakte Kriterium, lässt den
     case-insensitiven Fall aber offen.
  4. Der Kritiker prüft Randfälle und findet den verbleibenden Defekt.
  5. Der Bereichsleads erzeugt einen **begrenzten** Reparaturauftrag
     (nur die betroffene Datei, max. 1 Runde).
  6. Der Implementierer repariert; der Kritiker prüft die **geänderte
     Revision** erneut (eigene Session).
  7. Integration: Tests am Gesamtstand grün.
  8. Der Master Lead erhält die vollständige Evidenzkette.
- Das Zwei-Runden-Budget bleibt unverändert.

**Betroffene Dateien**
```
tools/e2e_repair.py            (neu)
scripts/ldt_core/pair_execution.py   (Reparaturauftrag, Re-Review der neuen Revision)
references/implementation.md   (Protokoll)
```

**Benötigte Laufzeitfähigkeiten**: native Agenten, `general` für Umsetzung und
Lead, `explore` für Kritik.

**Abnahmekriterien**
1. Der Kritiker meldet den verbleibenden Defekt **mit Datei, Zeile,
   Reproduktion und Anforderungsbezug**.
2. Der Reparaturauftrag nennt genau eine Datei und eine Rundenzahl ≤ 2.
3. Nach der Reparatur prüft der Kritiker in einer **neuen Session** die
   geänderte Revision und meldet 0 offene Befunde.
4. Die Integration ist grün; der Bericht enthält die Session-Kette
   (Implementer → Kritiker → Reparatur → Kritiker).
5. Der Fall „Budget erschöpft" endet mit einer Eskalation, nicht mit
   einem gemeldeten Erfolg.

**E2E-Tests**: Das Szenario selbst; zusätzlich deterministische Tests für
Budget, Protokoll und Eskalation.

**Sicherheit**: Der Reparaturauftrag darf nur die betroffenen Pfade
freigeben; die Dateieigentümerschaft wird erneut geprüft.

**Kompatibilität**: Bestehende Verträge bleiben gültig; ein Reparaturlauf
erzeugt einen neuen Vertrag mit Ableitung `critic-<id>-r<n>`.

**Kosten/Kontext**: 4–6 zusätzliche Agentensessions im Szenario.

**Ausgeschlossen**: automatische Erhöhung des Reparaturbudgets.

---

### Schnitt S4 — Token- und Modelleffizienz

**Ziel**: Die in §1 gemessenen Kostenpositionen gezielt senken, ohne die
Prüfqualität zu senken.

**Umfang** (jede Maßnahme ist einzeln messbar)

| Maßnahme | Bekämpft | Umsetzung |
|----------|-----------|-----------|
| **Vorkomponiertes Kontextbündel** | T-2, T-3 | Der deterministische Kern liest die benannten Pfade und legt einen kompakten Kontextblock (Dateiliste + Inhalte + Basisrevision) bereit. Der Agent muss nicht mehr explorieren. | `scripts/ldt_core/context.py` (neu), `runtime.dispatch` nimmt einen `context_bundle` |
| **Diff-begrenzte Übergabe** | T-4 | Der Kritiker erhält die geänderten Pfade und den Diff, nicht das Repository. | `pair_execution.run_critic` |
| **Strenges Ausgabeformat** | T-5 | Der Prompt verlangt ausschließlich das JSON-Objekt ohne Erzähltext; der Parser akzeptiert nur ein JSON-Objekt und verwirft Fließtext. | `pair_execution._parse_agent_output`, `_prompt` |
| **Zeilenendungs-Hinweis** | T-6 | Der Kontextbundel nennt die Zeilenenden der betroffenen Datei; ein Retry ist dann vermeidbar. | `context.py` |
| **Modellprofil je Rolle** | T-8 | Kritiker: `medium` statt `high`, solange der Bericht vollständig ist; `high` nur bei `confidence: "low"`. Umsetzung: Implementierer `medium`, Kritiker `medium`, Eskalation `high`. | `runtime.model_candidates` |
| **Ablaufbedingungen** | T-3 | Der Vertrag nennt Abbruchbedingungen (z. B. „höchstens 3 Dateien lesen, höchstens 2 Prüfläufe"); der Agent meldet Überschreitung. | `task_contracts` |

**Betroffene Dateien**
```
scripts/ldt_core/context.py        (neu: Kontextbündel)
scripts/ldt_core/runtime.py        (context_bundle-Parameter, Modellprofil je Rolle)
scripts/ldt_core/pair_execution.py (Übergabe, Ausgabeformat)
scripts/ldt_core/task_contracts.py (Ablaufbedingungen, Kontextfelder)
scripts/ldt_core/integration.py    (Tokenbericht erweitern)
```

**Benötigte Laufzeitfähigkeiten**: unverändert.

**Abnahmekriterien**
1. Der Implementierer-Zeitkontext sinkt um **≥ 30 %** gegenüber 39 782
   Input-Tokens (Ziel ≤ 27 800), bei gleicher Akzeptanzabdeckung.
2. Der Kritiker-Inputkontext sinkt um **≥ 40 %** gegenüber 43 543
   (Ziel ≤ 26 100).
3. Kein `edit:error` mehr im Standardlauf (Zeilenendungs-Hinweis).
4. Die Gesamt-Ausgabetokens sinken um **≥ 25 %** gegenüber 16 473
   (Output + Reasoning des Paarlaufs).
5. Die Abnahmekriterien des Meilensteins bleiben vollständig erfüllt.
6. Die Tokenzahlen werden **gemessen**, nicht geschätzt, und im
   Integrationsbericht ausgewiesen.

**E2E-Tests**: `tools/measure_tokens.py` wird zum wiederholbaren Messwerkzeug
und liefert die Vorher/Nachher-Werte.

**Sicherheit**: Das Kontextbündel enthält nur die im Vertrag benannten Pfade.
Ein Vertrag, der Geheimnisse anfordert, wird nicht gebündelt.

**Kompatibilität**: Ohne Kontextbündel bleibt das alte Verhalten; das Bündel
ist eine Optimierung, keine Semantikänderung.

**Ausgeschlossen**: Preisoptimierung ohne Qualitätsmessung, automatische
Modellwahl ohne Protokoll.

---

### Schnitt S5 — Ein Sprachbefehl startet den Workflow

**Ziel**: Der Nutzer beschreibt eine Idee. LittleDevTeam erkennt, dass
Planung nötig ist, stellt gezielte Fragen, koordiniert die Recherche, zeigt
die Projektübersicht und bittet um die Startfreigabe — ohne dass der Nutzer
die Python-Befehle kennt.

**Umfang**
- **Projektlokale Aktivierungsregel**: eine kurze `AGENTS.md`-/`CLAUDE.md`-
  Ergänzung im Zielprojekt, die auf den Skill verweist und die
  Startabsicht beschreibt. **Kein** globaler Default, keine Änderung
  stillschweigend vorgenommener Harness-Einstellungen.
- **Ein einziger Einstiegspunkt** `ldt start` (Skill-Seite), der die
  vorhandenen Einzelbefehle in einer Reihenfolge aufruft:
  `intake → arch-team decompose → research → arch-team integrate →
   task-contracts → project-view → [Startfreigabe] → pair-exec → integration`
- **Planmodus**: Solange die Startfreigabe fehlt, arbeitet der Ablauf im
  Planmodus. Ob der Harness den Planmodus technisch erzwwingt, ist eine
  **Laufzeiteigenschaft**: wird sie nicht angeboten, bleibt die Umsetzung
  aus und der Skill sagt das einmal klar.
- **Harness-Adapter**: eine dünne Schicht, die den Ablauf an OpenCode bindet.
  Codex nutzt denselben Kern, aber eine eigene Ausdrucksform.
- **Ergebnisdarstellung**: die Projektübersicht ist die einzige
  Nutzerinteraktion vor der Startfreigabe.

**Betroffene Dateien**
```
scripts/ldt_core/orchestrator.py   (neu: der Einstiegspunkt und die Reihenfolge)
scripts/validate.py                (Befehl "start")
references/implementation.md       (Ablaufreihenfolge)
references/intake.md
SKILL.md                           (Aktivierungsregel)
assets/project-view.template.md    (um die offenen Entscheidungen ergänzt)
```

**Benötigte Laufzeitfähigkeiten**: OpenCode-Skill-Erkennung (bereits
vorhanden: `.agents/skills/…`), native Subagenten, Planmodus **optional**.

**Abnahmekriterien**
1. Eine vage Nutzeranweisung im Zielprojekt erzeugt einen Projektbrief und
   **keinen** Anwendungscode.
2. Der Ablauf stoppt nach der Projektübersicht und stellt die Startfrage.
3. Ohne die Startfreigabe wird kein Implementierungsauftrag gestartet.
4. Nach der Freigabe läuft die Sequenz ohne weitere Python-Aufrufe des
   Nutzers bis zum Integrationsbericht.
5. Eine präzise Kleinänderung überspringt Intake und Recherche (Lean-Pfad).
6. Die Reihenfolge ist in beiden Harness-Varianten identisch; nur die
   Auslösung des Einstiegspunkts unterscheidet sich.

**E2E-Tests**: Skript, das nur die Nutzeranweisung simuliert und die
erzeugten Artefakte prüft.

**Sicherheit**: Die Startfreigabe bleibt eine menschliche Entscheidung im
Zustand. Der Ablauf kann sie nicht erzeugen.

**Kompatibilität**: Codex-Kompatibilität über den gemeinsamen Kern; der
Skill bleibt Agent-Skills-konform unter `.agents/skills/architect-dev-team/`.

**Ausgeschlossen**: eine eigene CLI-Anwendung (M4), Hintergrunddienste,
globale Harness-Umkonfiguration.

---

### Schnitt S6 — Skill-Bibliothek-Schnittstelle (nur Schnittstelle)

**Ziel**: Die spätere automatische Skill-Auswahl anschlussfähig machen, ohne
M3/M4/M5 vorwegzunehmen.

**Umfang** — ein reines Lese-Interface, das der Kern bereits heute kennt:

```python
def capability_needs(inventory) -> list[Need]      # aus M1c-Inventar
def discover_candidates(need, registry) -> list[Skill]   # aus M1b-Registry
def trust_status(skill) -> str                      # candidate/reviewed/…
def runtime_compatible(skill, runtime) -> bool     # Codex/OpenCode/Agent Skills
def skill_to_role(skill) -> list[str]              # Rollenzuordnung
def recommend(needs, candidates, limit=5) -> list[Recommendation]
```

**Betroffene Dateien**
```
scripts/ldt_core/skills_api.py     (neu: reine Lesefunktionen)
references/external-skills.md      (Zuordnung der Verantwortlichkeiten)
```

**Abnahmekriterien**
1. Jede Funktion liest nur vorhandene M1b/M1c-Daten und führt nichts aus.
2. Ein Kandidat mit `trust: "candidate"` wird als solcher ausgewiesen und
   nie als installiert oder vertrauenswürdig.
3. Die Empfehlung trägt Begründung, Quelle, Trust-Status,
   Installationsstatus und Risiken.
4. Die Schnittstelle installiert, aktiviert und erteilt keine Einwilligung.

**E2E-Tests**: nur deterministisch, gegen Registry-Fixtures.

**Sicherheit**: reine Leseoperationen; keine Netzwerk-, Installations- oder
Ausführungspfade.

**Kompatibilität**: M1b/M1b-Verträge bleiben unverändert.

**Ausgeschlossen**: die eigentliche Empfehlungslogik, die Installations-
adapter (M5), die CLI-Ausgabe (M4), der Discovery-Katalog.

---

## 4. Bereichsleads-Verträge (Entwurf)

### 4.1 `LeadContract`

```json
{
  "task_id": "lead-backend",
  "role": "Department Lead",
  "goal": "Deliver the approved registration vertical slice",
  "architecture_version": "<sha>",
  "milestone_id": "M1-Slice-1",
  "base_revision": "<sha>",
  "contract_refs": ["contract-api-001"],
  "input_paths": ["src/**", "tests/**", "specs/openapi.yaml"],
  "dependencies": ["research-001"],
  "allowed_actions": ["read:**", "write:.architect-dev-team/lead/**"],
  "file_ownership": {"src/users.py": "impl-001", "tests/test_users.py": "impl-001"},
  "acceptance": [
    "Both specialist results satisfy their acceptance criteria",
    "The integrated result passes the approved checks",
    "No unresolved blocker remains"
  ],
  "required_checks": ["unit-tests", "pair-review", "integration-tests"],
  "skill_pins": [],
  "model_profile": "medium",
  "resource_budget": {"tokens": 60000, "time_seconds": 900, "max_specialists": 3},
  "review_assignment": "critic-lead-001",
  "escalation": ["scope_change", "missing_decision", "security_risk", "budget_exceeded"]
}
```

### 4.2 Die zehn Schritte des Bereichsleiters

| # | Schritt | Ergebnis | Grenze |
|---|---------|----------|--------|
| 1 | Zielauftrag empfangen | Ziel, Scope, Milestone | Keine eigene Scope-Auslegung |
| 2 | Scope und Architektur-Abhängigkeiten prüfen | bestätigt / begründete Ablehnung | Bei Ablehnung: Eskalation |
| 3 | Fehlende Informationen benennen | Liste offener Punkte | Nicht erfinden |
| 4 | In Spezialistenverträge zerlegen | Vertrags-IDs mit Abhängigkeiten | Keine Rekursion |
| 5 | Modelle und Skills empfehlen | Profil + Pin je Spezialist | Nur Vorschlag |
| 6 | Schnittstellen-Eigentümerschaft und Prüferwartungen festlegen | `file_ownership`, `required_checks` | Überschneidung → Eskalation |
| 7 | Spezialistenausführung koordinieren | Sessions, Status | Master startet Subagenten |
| 8 | Rückgaben prüfen | Abnahme / begrenzte Korrektur | Kein „done" ohne Nachweis |
| 9 | Begrenzte Korrekturen anfordern | Reparaturlauf mit Runden ≤ 2 | Budgetende → Eskalation |
| 10 | Integriertes Ergebnis an den Master liefern | `LeadResult` | Keine Freigabe, keine Integration |

### 4.3 `LeadResult`

```json
{
  "task_id": "lead-backend",
  "status": "completed",
  "specialist_results": [
    {"task_id": "impl-001", "status": "completed", "checks": [...], "evidence": {...}},
    {"task_id": "critic-001", "status": "completed", "findings": [...], "independence": "independent"}
  ],
  "corrections_requested": [
    {"round": 1, "target": "impl-001", "reason": "duplicate check is case-sensitive", "rounds_used": 1}
  ],
  "acceptance_met": true,
  "unresolved": [],
  "escalated": false
}
```

---

## 5. Kritik-Qualitätsanforderungen (verbindlich)

| Anforderung | Prüfbar durch |
|--------------|----------------|
| Geprüfte Anforderungen benannt | `requirements_checked` nicht leer |
| Geprüfte Dateien benannt | `files_inspected` nicht leer |
| Testevidenz geprüft | `test_evidence_reviewed` vorhanden |
| Befunde **oder** geprüfte Nichtbefunde | `defects` oder `verified_non_findings` nicht leer |
| Offene Bereiche benannt | `unchecked_areas` (darf leer sein) |
| Konfidenz mit Begründung | `confidence` ∈ {high, medium, low} |
| Empfehlung | `recommendation` ∈ {approve, approve_with_findings, reject} |
| Unabhängigkeit | Getrennte, verifizierbare Session; read-only Agent |
| Verknüpfung | `session_id` der Kritikersession im Bericht |

**Ein leerer Bericht oder ein Bericht ohne `requirements_checked` und
`files_inspected` gilt als fehlgeschlagene Kritik und blockiert die Abnahme.**

Der Kritiker bleibt read-only. Das in M2 Slice 1 zugesagte Anlegen von Tests
unter `tests/critic/` ist mit dem nativen `explore`-Agenten **nicht
ausführbar** (gemessen: 2 × `write:error`). Slice 2 entscheidet sich
ausdrücklich: entweder ein eigener, schreibberechtigter, aber
verzeichnisgebundener Kritiker-Agent oder der Verzicht auf diese Zusage.
**Empfehlung: Verzicht.** Der Kritiker liefert stattdessen den
reproduzierenden Testinhalt als Text, den der Bereichsleads in einen
genehmigten Bereich schreibt. Das hält die Unabhängigkeit schärfer.

---

## 6. Realer Reparaturlauf — Szenario

```
Fixture: src/users.py mit case-sensitiver Duplikatprüfung
         tests/test_users.py mit exaktem Duplikat
Vertrag: acceptance = "register rejects a duplicate email"   (exakter Fall)

 1. Implementierer (general, Session A)
    → behebt den exakten Fall, behält die Schreibungs-Klein/K Groß-Variante
 2. Kritiker (explore, Session B)
    → prüft Randfälle, findet: register('A@x.com') nach register('a@x.com') gelingt
    → CriticReport mit severity=major, Datei, Zeile, Reproduktion
 3. Bereichsleads (general, Session C)
    → prüft die Rückgabe, erzeugt einen begrenzten Reparaturauftrag
      (genau src/users.py, höchstens 1 Runde)
 4. Implementierer (general, Session D)
    → repariert die case-insensitive Prüfung
 5. Kritiker (explore, Session E)
    → prüft die geänderte Revision, meldet 0 offene Befunde
 6. Integration
    → pytest am Gesamtstand grün
 7. Master Lead
    → erhält die Kette A→B→C→D→E mit allen Sessions
```

**Abbruchkriterien**
- Nach 2 Runden ohne Auflösung: Eskalation an den Menschen, Status `escalated`.
- Bei jedem Agentenausfall: Status `failed`, kein gemeldeter Erfolg.
- Bei fehlender Unabhängigkeit: `unavailable`, Gate gesperrt.

**Messbare Abnahme**
Die Kette enthält 5 verifizierte Sessions, 1 Reparaturrunde, 0 offene Befunde,
grüne Integration. Das Ergebnis wird als `.architect-dev-team/`-Evidenz
abgelegt.

---

## 7. OpenCode-/Codex-Integrationsstrategie

| Ebene | OpenCode | Codex | Gemeinsamer Kern |
|-------|----------|-------|------------------|
| Skill | `.agents/skills/architect-dev-team/` | `.agents/skills/architect-dev-team/` | identisch |
| Ablaufsteuerung | Skill-Referenz + `ldt start` | Skill-Referenz + `ldt start` | `ldt_core/orchestrator.py` |
| Agenten | `opencode run --agent …` | Codex-eigener Aufruf | `ldt_core/runtime.py` (Adapter-Schnittstelle) |
| Modelle | `opencode models` | Codex-Konfiguration | `model_candidates()` |
| Planmodus | nativ verfügbar, **optional** erzwingt | nativ verfügbar | Kern prüft nur, ob der Modus aktiv ist |
| Berechtigungen | native Agenten-Berechtigungen | Codex-Berechtigungen | Kern erzwingt nichts selbst |
| Zustand | `.architect-dev-team/state.json` | identisch | `ldt_core/state.py` |
| CLI | später M4 | später M4 | `ldt_core` |

**Regeln**
1. **Keine** globale Harness-Umkonfiguration. Die Aktivierung erfolgt über eine
   kurze projektlokale Regel, die der Nutzer selbst anlegt oder bestätigt.
2. **Keine** Behauptung, dass eine Skill-Anweisung den Harness-Modus wechselt.
   Ist der native Planmodus nicht verfügbar, bleibt die Umsetzung aus, und
   das wird einmal klar gesagt.
3. Der Runtime-Adapter ist die **einzige** Stelle, die den Harness kennt.
   Ein zweiter Adapter entsteht erst, wenn Codex real verfügbar ist.
4. Codex-Kompatibilität wird **strukturell** gepflegt
   (Agent-Skills-Struktur, getrennte `agents/`-Konfiguration, kein
   OpenCode-spezifischer Inhalt im Kern), **nicht** durch Behauptung.

**Neue Agentenkonfiguration** (harnessneutral, bestehendes Format):
```
.agents/skills/architect-dev-team/agents/openai.yaml   (bestehend, Codex)
.agents/skills/architect-dev-team/agents/opencode.yaml (neu, OpenCode)
```
Beide sind Darstellungen derselben Rollen; keine Laufzeitlogik.

---

## 8. Abhängigkeiten zu M3–M7 (nicht vorgezogen)

| Anforderung | Zuständig | Abhängigkeit von Slice 2 |
|--------------|-----------|--------------------------|
| Skill-Discovery, Relevanzbewertung, Trust-Status | **M3** | Schnitt S6 liefert nur die Lese-Schnittstelle |
| `ldt`-CLI mit Menüs, JSON-Modus | **M4** | Schnitt S5 liefert nur die Kern-Orchestrierung; die CLI bleibt M4 |
| Transaktionale Installation, Aktivierung, Rollback | **M5** | nicht berührt; S6 installiert nichts |
| Kompatibilitäts-/Bundle-Prüfung | **M6** | nicht berührt |
| Aktualisierungen, Vergleiche, Messung | **M7** | Schnitt S4 liefert die Messinfrastruktur, die M7 auswertet |
| Rollen- und Abteilungsmechanik | **M2 Slice 2 (S1)** | in diesem Slice |
| Kritikqualität, Reparaturlauf, Tokeneffizienz | **M2 Slice 2 (S2–S4)** | in diesem Slice |
| Natürlicher Einstieg | **M2 Slice 2 (S5)** | in diesem Slice |

**Keine Roadmap-Grenze wird stillschweigend verschoben.** Die Zuordnung in
`design/v2-roadmap-addendum.md` bleibt unverändert; Schnitt S6 ist ausdrücklich
als *Schnittstelle*, nicht als M3-Implementierung gekennzeichnet.

---

## 9. Sicherheits- und Bedrohungsmodell

| Bedrohung | Maßnahme in Slice 2 |
|------------|----------------------|
| Kritiker kompromittiert Produktionscode | native read-only-Berechtigung; die Zusage „Kritiker legt Tests an" wird entfernt (S2) |
| Bereichsleads erweitert den Scope | Vertragsgrenzen; Ablehnung und Eskalation; keine Freigabebefugnis |
| Erzwungene Zustimmung | `kind: "start"` bleibt menschlich; kein Agent erzeugt Freigaben |
| Fälschliche Unabhängigkeit | hashgebundenes Evidenzartefakt, verifizierte Sessions, getrennte IDs |
| Kontextbündel leakt Geheimnisse | nur vertraglich benannte Pfade; `.env` ausgeschlossen |
| Prompt-Injection aus Projektinhalt | Research- und Kritikaufträge behandeln Dateiinhalte als Daten, nicht als Anweisungen |
| Shell-Injektion über Testkommandos | `shell=False`, Argumentliste (bereits umgesetzt) |
| Pfadtraversal über Task-IDs | `safe_task_id` (bereits umgesetzt) |
| Endlosschleifen | Zwei-Runden-Budget; Erschöpfung eskaliert |

---

## 10. Vorgeschlagene Reihenfolge und Aufwand

| Schnitt | Abhängig von | Agenten-Sessions im Test | Geschätzter Kontextaufwand |
|---------|---------------|--------------------------|--------------------------|
| S1 Bereichsleads | – | 4 | mittel |
| S2 Kritikqualität | S1 (Lead nutzt Bericht) | 4 | niedrig |
| S3 Reparaturlauf-E2E | S1, S2 | 5 | niedrig (nur Skript) |
| S4 Tokeneffizienz | S2 (Diff-Übergabe) | 2 pro Messung | niedrig, aber **senkt** die Kosten |
| S5 Einstiegspunkt | S1–S4 | 1 | niedrig |
| S6 Skill-Schnittstelle | – | 0 | keiner |

**Reihenfolge**: S1 → S2 → S3 → S4 → S5. S6 ist unabhängig und kann
parallel oder später laufen.

**Messbare Gesamtwirkung** (Ziel, gegen die Basis aus §1):
- Implementierer-Input: 39 782 → ≤ 27 800 (−30 %)
- Kritiker-Input: 43 543 → ≤ 26 100 (−40 %)
- Gesamt-Output+Reasoning: 32 602 → ≤ 24 450 (−25 %)
- Anzahl Agentensessions für einen Durchlauf: unverändert
- **Echte Reparaturlauf**: von 0 auf ≥ 1 belegten Fall

---

## 11. Vorgeschlagene verbindliche Prüfungen (Mandatory Checks) für Slice 2

| # | Name | Umfang |
|---|------|--------|
| 1 | `regression suite and documented platform skips` | `unittest discover -s tests`, inkl. M1a-Orakel |
| 2 | `package and registry integrity` | `validate.py package`, `registry` S1+S2 |
| 3 | `runtime capability and verified sessions` | `runtime detect`, `runtime verify` |
| 4 | `department lead coordination` | Lead zerlegt, prüft, fordert Korrektur an, integriert |
| 5 | `critic report completeness gate` | Unvollständiger Bericht wird abgelehnt |
| 6 | `independent review with bound runtime evidence` | getrennte Sessions, hashgebunden |
| 7 | `real agent repair chain` | S3-Szenario: Kritiker findet, Reparatur, Re-Review, grün |
| 8 | `token efficiency measurement` | Vorher/Nachher gemessen, keine Schätzung |
| 9 | `single entrypoint orchestration` | eine Nutzeranweisung bis zur Startfrage |
| 10 | `skill api read only boundary` | keine Ausführung, keine Installation |

Die bestehenden sechs Prüfungen aus Slice 1 bleiben **unverändert** bestehen;
die neuen kommen hinzu. Der Umfang der Slice-1-Prüfungen wird nicht erweitert.

---

## 12. Was Slice 2 ausdrücklich NICHT umfasst

- Eine `ldt`-CLI (M4)
- Installation oder Aktivierung externer Skills (M5)
- Codex-Ausführung (bleibt unbestätigt, bis eine echte Laufzeit vorliegt)
- Ein Frontend-Dashboard (Markdown + Mermaid bleiben das Minimum)
- Ein Hintergrunddienst oder Scheduler
- Globale Harness-Umkonfiguration
- Ein dauerhafter Rollenbestand oder eine Abteilungsorganisation
- Automatische Trust-Hochstufung von Registry-Einträgen
- Änderungen an genehmigten Schemata ohne erneute Freigabe

---

## 13. Exakte Freigabeanforderung

Für die Umsetzung wird **eine** Freigabe benötigt, die folgendes umfasst:

**Umfang**
- Schnitt S1: `LeadContract`, `LeadResult`, Rollenzuordnung, Bereichsleads-Ablauf
- Schnitt S2: `CriticReport`, Vollständigkeits-Gate, Diff-Übergabe, Verzicht auf
  die Kritiker-Testanlage-Erlaubnis
- Schnitt S3: `tools/e2e_repair.py` und die Protokollanpassungen
- Schnitt S4: `context.py`, Ausgabeformat, Modellprofil je Rolle, Ablaufbedingungen
- Schnitt S5: `orchestrator.py`, `ldt start`, projektlokale Aktivierungsregel,
  `agents/opencode.yaml`
- Schnitt S6: `skills_api.py` (nur lesend)

**Ausdrücklich nicht autorisiert**
- Installation/Aktivierung externer Skills
- Änderung der globalen Harness-Konfiguration
- Veröffentlichung, Push, Merge, Deployment
- Änderung der genehmigten Schemata über die in §11 genannten Prüfungen hinaus
- Beginn von M2 Slice 3 oder M3

**Pflichtprüfungen**: die zehn aus §11.

**Nach Abschluss**: Stopp an der Slice-2-Abschlussfreigabe. Kein automatischer
Übergang zu M3.

---

## 14. Offene Punkte für die Freigabe

1. **Kritiker-Testanlage**: Verzicht empfohlen (nur Textlieferung). Alternative:
   eigener schreibberechtigter, verzeichnisgebundener Kritiker-Agent. Das
   verändert die Unabhängigkeitsarchitektur und braucht eine eigene Bewertung.
2. **Profil des Kritikers**: `medium` als Standard mit `high` bei
   `confidence: "low"` — oder `high` dauerhaft (Kosten).
3. **Maximale Spezialisten je Bereichsleads**: Vorschlag 3, wie in der
   Slice-1-Empfehlung.
4. **Ausgabeformat des Kritikers**: verbindliches JSON ohne Erzähltext —
   oder JSON mit kurzem Fließtext für Lesbarkeit.

---

## Anhang A — Belegte Messwerte (Slice 1, 20.10.2026)

| Kennzahl | Implementierer | Kritiker |
|----------|----------------|----------|
| Session | `ses_ea7d24e62ffe2km7bNrHe468PR` | `ses_ea7cc0c40ffe4n4d1yf58nWVMK` |
| Agent / Modell | `general` / `opencode/minimax-m3.1-flash-free` | `explore` / `opencode/nemotron-3.5-super-vl-free` |
| Modellschritte | 27 | 12 |
| Werkzeugaufrufe | 41 (26 shell, 8 read, 3 write, 2 edit, 2 edit:error) | 25 (15 read, 8 shell, 2 write:error) |
| Input-Tokens | 39 782 | 43 543 |
| Output-Tokens | 10 375 | 6 098 |
| Reasoning-Tokens | 14 444 | 3 685 |
| Cache-Reads | 721 014 | 91 056 |
| Antwortumfang | 2 952 Zeichen | 13 632 Zeichen |

E2E-Lauf vom 20.10.2026 08:53–09:14 (78 Dateien, Digest
`8e82438ae68db5259cffc4ac32b63d46cb7686943a13210fa7dd8315ea7684ee`):
Implementierer `ses_ea7db393dffeqlSgbgUPOkUNuG` (Input 67 144 / Output 11 692),
Kritiker `ses_ea7d70a31ffe9KBjQmLaWmfiQ9` (Input 2 196 / Output 135,
`read_only_agent: true`).

## Anhang B — Unabhängige Reviewer

| Runde | Session | Ergebnis | Befunde |
|-------|---------|-----------|---------|
| 1 | `ses_ea80d5420ffeDXxEF6VkZfh8Qh` | reject | 19 (1 Blocker) |
| 2 | `ses_ea7e8737effebvYg7NpOe8I7o6` | approve_with_findings | 10 (2 behauptungsrelevant) |

Beide Runden: natives `explore`-Subagent, eigener Kontext, keine
Dateiänderung, kein `opencode run`.
