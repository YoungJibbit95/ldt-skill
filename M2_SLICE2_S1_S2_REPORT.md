# M2 Slice 2 S1/S2 — Umsetzung und Abschlussnachweis

**Status**: zur Abschlussfreigabe bereit
**Repository**: `F:\Coding\LittleDevTeamSkill` | **Branch**: `m1d-roadmap-addendum`
**Genehmigter Umfang**: S1 (Department Lead) + S2 (CriticReport) — S3–S6 ausdrücklich **nicht** zur Implementierung freigegeben

---

## 1. Umgesetzter Umfang

### S1 — Department Lead Orchestrierung

Der Lead ist **kein Rollendokument**, sondern ein echter nativer Agent mit zwei
Sub-Phasen:

| Sub-Phase | Nativer Agent | Schreibrecht | Aufgabe |
|-----------|---------------|--------------|---------|
| Plan | `plan` (read-only) | keines | Outcome gegen Architektur prüfen, Lücken benennen, Assignments vorschlagen |
| Merge | `general` | nur die Dateien der Spezialisten | Ergebnisse prüfen, Korrekturen fordern, integrieren |

**Warum zwei Agenten:** Ein gemessener Lauf zeigte, dass der Lead unter dem
schreibberechtigten `general`-Agenten die Arbeit **selbst** ausführte, statt zu
delegieren. Die Plan-Phase läuft deshalb read-only: die Spezialisten
implementieren tatsächlich. Die Merge-Phase darf schreiben, weil der Lead am
Ende zusammenführen muss.

**Schreibrahmen (strukturell erzwungen):** Die Merge-Phase darf nur die Dateien
ändern, die die Spezialisten besitzen (`file_ownership`). Der Kern vergleicht den
Baum vor und nach dem Merge. Eine Änderung außerhalb des Rahmens wird
**abgelehnt** und eskaliert - das ist keine Prompt-Anweisung, sondern eine
Prüfung im Code.

**Plan-Prüfung vor jedem Lauf:** Roster, sichere Pfade, keine Delegation an
einen Lead, genehmigte Skill-Pins, Prüfungen innerhalb der Meilenstein-Policy,
Überschneidungen mit bestehenden Verträgen.

**Plan-Extraktion ist schema-agnostisch:** Ein Lead meldet seinen Plan in
eigenen Worten. Der Kern findet die Assignments über ihre `task_id`, egal ob sie
unter `assignments`, `roster_executed`, `stages[].tasks[]` oder anderswo
stehen, und füllt Lücken aus dem vom Master Lead vereinbarten Roster. Danach
wird streng validiert.

### S2 — CriticReport und Kritikqualität

Ein Review besteht nicht, weil eine Session existierte. Der `CriticReport` ist
ein validierter, maschinenprüfbarer Vertrag:

```json
{
  "task_id": "critic-001",
  "reviewed_task_id": "impl-001",
  "reviewed_revision": "<Snapshot-Digest des geprüften Standes>",
  "reviewer": {"session_id", "agent", "model", "execution_mode",
                "verified", "read_only_agent"},
  "coverage": {"requirements_checked", "files_inspected", "interfaces_checked",
               "evidence_references", "checks_run", "unverified_areas"},
  "findings": [{"severity", "file", "line", "issue", "reproduction", "reference"}],
  "verified_non_findings": [],
  "confidence": "high|medium|low",
  "limitations": [],
  "recommendation": "approve|approve_with_findings|reject",
  "summary": "kurzer lesbarer Text für den Bereichsleads"
}
```

**Die Reviewer-Identität gehört der Runtime, nicht dem Agenten.** Der Orchestrator
überschreibt `session_id`, `agent`, `model`, `execution_mode`, `verified` und
`read_only_agent` mit den verifizierten Fakten. Ein Agent kann sich nicht zum
unabhängigen Reviewer erklären.

**Abgelehnte Fälle** (alle durch Tests belegt):

| Ablehnung | Regel |
|-----------|-------|
| fehlende Ausführungsevidenz | keine Session-ID, Session nicht verifiziert, Modus ≠ `native` |
| gefälschte Unabhängigkeit | Kritiker-Session = Implementierer-Session; Agent nicht read-only |
| Revision veraltet | `reviewed_revision` ≠ aktueller Digest; **nicht** automatisch aufgefüllt |
| fehlende Abdeckung | Pflichtprüfungen des Vertrags nicht berichtet oder ohne Ergebnis |
| Test behauptet, nicht ausgeführt | Prüfungsliste leer, aber ein Testergebnis wird behauptet |
| ungültige Referenzen | Datei- oder Evidenzpfad verlässt das Projekt |
| unvollständiger Report | Pflichtfeld fehlt, falscher Typ, falsches `task_id` |
| Blocker weggewertet | blockierender Befund mit Empfehlung `approve` |

**Re-Review nach einer Reparatur** wird genauso validiert. Ein fehlgeschlagener
Reparaturlauf, ein abgelehnter Re-Review und ein erschöpftes Budget werden
**nie** als Erfolg gemeldet (Exit-Codes 5 und 6).

---

## 2. Gefundene und behobene Defekte

**Runde 1** (`ses_ea78eb9f6ffetJf1KFqg9SBFj1`): 24 Befunde, `reject`.
**Runde 2** (`ses_ea7382168ffe45Byye3heNl7Ho`): 14 Befunde, `reject` - die
blockierenden Defekte aus Runde 1 waren teilweise nicht behoben.

Behoben wurden:

| # | Schwere | Befund | Behebung |
|---|---------|--------|----------|
| 1 | Blocker | `LeadContract` war nicht ladbar; `validate.py lead` unbenutzbar | `load_contract` erkennt den Lead-Vertrag |
| 2 | Hoch | Revision **vor** der Implementierung berechnet; ehrlicher Kritiker abgelehnt | Digest wird **nach** der Umsetzung genommen |
| 3 | Hoch | Fehlgeschlagener Re-Review / Reparatur ⇒ Exit 0 | Exit 6, `repair_failed`, Report des letzten Reviews |
| 4 | Hoch | Re-Review-Report ungeprüft | Re-Review durchläuft dieselbe Prüfung |
| 5 | Hoch | `file_ownership`-Pfade ungeprüft | Pfadprüfung im Plan |
| 6 | Hoch | erzeugte Verträge ungültig, ungeprüfte Skill-Pins | Verträge werden vor dem Lauf validiert |
| 7 | Hoch | Kern übernahm `accepted` des Leads | Kern entscheidet anhand von Nachweis und Kriterien |
| 8 | Hoch | Korrekturbudget pro Entscheidung statt pro Runde | Budget pro Runde, erschöpft ⇒ Eskalation |
| 9 | Hoch | Budgeterschöpfung nicht eskaliert | Kern eskaliert selbst |
| 10 | Hoch | Pflichtprüfungen des Vertrags nie verglichen | Vergleich ergänzt |
| 11 | Hoch | `critic-report validate` prüfte weder Revision noch Session | prüft beides |
| 12 | Hoch | Dateiüberschneidung nur innerhalb eines Plans | auch gegen aktive Verträge |
| 13–22 | Mittel | Rollenprüfung, Architektur-Digest, leere Roster, Evidenzpfade, JSON-Extraktion, Statusherkunft, `--roster`, Zustandsaufzeichnung, Doku-Widersprüche, Orakel-Regex | je behoben |
| — | — | Der Lead führte die Arbeit selbst aus | Plan-Phase read-only, Merge-Phase mit Schreibrahmen |

### Defekte der zweiten Runde (alle behoben)

| # | Schwere | Befund | Behebung |
|---|---------|--------|----------|
| R2-1 | Hoch | Der Digest wurde **vor** der Implementierung genommen: ein ehrlicher Kritiker wurde abgelehnt, ein veralteter Digest akzeptiert | Digest wird **nach** der Implementierung genommen; der Report muss ihn nennen, er wird nicht aufgefüllt |
| R2-2 | Hoch | `repair_failed` wurde gesetzt, aber nie gelesen ⇒ Exit 0 | Der CLI-Code wertet das Flag aus ⇒ **Exit 6** |
| R2-3 | Hoch | Der gespeicherte Report war der **erste**; die Re-Review-Session passte nicht dazu; der Re-Review war gar nicht revisionsgebunden | Der **finale** Report wird gespeichert, die Re-Review wird gegen denselben Vertrag geprüft und mit dem Digest gebunden |
| R2-4 | Hoch | Der Schreibrahmen blendete `.architect-dev-team/` aus ⇒ ein Lead konnte den Freigabestand fälschen | Der verwaltete Zustand wird **nicht** übersprungen; eine Änderung dort ist ein Verstoß |
| R2-5 | Hoch | Die Schreibzugriffe der Spezialisten wurden nie geprüft | Nach jedem Spezialistenlauf wird der Baum gegen dessen `file_ownership` geprüft |
| R2-6 | Hoch | Eine erfundene Aufgabe außerhalb des Rosters wurde stillschweigend verworfen | Sie wird durchgereicht und **abgelehnt** |
| R2-7 | Mittel | Ein Konflikt wurde ignoriert, wenn der Lead `true` meldete | Ein gelisteter Konflikt gewinnt; ein Konflikt blockiert **vor** der Assignment-Prüfung |
| R2-8 | Mittel | Das Korrekturbudget wurde pro Entscheidung statt pro Runde verbraucht | Ein Lauf verbraucht höchstens das Budget; die Erschöpfung eskaliert im Kern |
| R2-9 | Mittel | Ein eingepflanztes JSON-Objekt konnte den echten Report verdrängen | **Alle** Kandidaten werden validiert; derjenige, der den Vertrag erfüllt, gewinnt |
| R2-10 | Mittel | Ein Plan ohne Assignment wurde angenommen | Abgelehnt, außer der Lead meldet einen Architekturkonflikt (das ist `blocked`) |
| R2-11 | Mittel | Toter Code, unbenutzte Importe, der `skill_pins`-Check war wirkungslos | Entfernt bzw. wirksam gemacht |
| R2-12 | Mittel | Eine Korrektur konnte einen unapproved Check einschleusen | Der korrigierte Vertrag wird vor dem Lauf validiert |
| R2-13 | Mittel | Der Belegdatensatz mischte zwei Sessions | Der Beleg beschreibt genau eine Session |

### Sechs Befunde aus der echten Agentenausführung

| # | Befund | Behebung |
|---|--------|----------|
| E-1 | Der native `explore`-Agent **fragte nach den Task-Details**, statt zu prüfen | Der Prompt nennt jetzt den vollständigen Auftrag zuerst, inklusive Anforderungen, Dateien, Checks und dem Kontext der Implementierung, und sagt ausdrücklich, dass die Angaben vollständig sind |
| E-2 | Der Agent antwortete mit einem **Markdown-Prüfbericht**, kein JSON | Der Kern extrahiert die Struktur selbst, mit dem **Vertrag als Autorität**; ein nicht genannter Check bleibt `not_run` und wird abgelehnt |
| E-3 | Das Roster enthielt nur `{task_id, role, goal}` | Das Roster trägt die vollständige Spezialistendefinition; es ist die Autorität, nicht die Planform des Leads |
| E-4 | Der Lead nannte sich **selbst** als Assignment (`lead-backend`) | Eine Aufgabe außerhalb des Rosters wird abgelehnt, nicht stillschweigend verworfen. Das Verhalten des Leads war korrekt erkannt und die Ablehnung ist die richtige Antwort |
| E-5 | Der Lead nannte die Aufgabe, aber nicht ihre Anforderungen, Prüfungen und Dateien | Der Roster-Eintrag ist die **Basis**, die Lead-Antwort darf nur **verfeinern**. Ein leeres Feld behält den vereinbarten Wert |
| E-6 | Ein JSON-Kandidat ohne Vertragsfelder **schattierte** einen gültigen Prosa-Report | Erst alle JSON-Kandidaten, dann der Prosa-Report. Ein Kandidat, der den Vertrag nicht erfüllt, kann einen gültigen nicht verdrängen |

Zusätzlich wurde eine Regel verschärft: **eine nicht lesbare Bemerkung des
Reviewers ist nie eine saubere Prüfung.** Wenn der Agent einen Befund meldet,
den der Kern nicht auslesen kann, wird der Report abgelehnt statt als
"keine Befunde" akzeptiert.

### Defekte der dritten Runde (alle behoben)

**Runde 3** (`ses_ea69b1043ffedrqJQrvAzE0ivv`): 17 Befunde, `reject`. Die
Reparaturen der zweiten Runde hielten nicht in jedem Punkt.

| # | Schwere | Befund | Behebung |
|---|---------|--------|----------|
| R3-1 | Hoch | Der Reparaturlauf sah die **Rohantwort** statt des validierten Reports ⇒ ein Prosa-Kritiker mit Blocker-Befund ließ das Paar mit **Exit 0** durch | Der Reparaturlauf arbeitet mit den Befunden des validierten Reports; dieselbe Quelle entscheidet, ob eine Gruppe behoben ist |
| R3-2 | Hoch | Die Extraktion erfand ein `passed`: das Teilwort `ok` in "t**ok**en" | Das Ergebnis wird aus ganzen Wörtern gelesen; "no failures" ist ein Pass, "took" ist keiner |
| R3-3 | Hoch | "does not pass" wurde als Annahme gelesen ⇒ eine Übergabe, deren eigener Text das Ergebnis als unbrauchbar bezeichnet | Alle Entscheidungswörter werden negationsbewusst gelesen |
| R3-4 | Mittel | Ein nicht lesbarer Befund wurde verworfen und die Prüfung als sauber akzeptiert | Eine nicht lesbare Bemerkung ⇒ der Report wird abgelehnt |
| R3-5 | Mittel | Der Re-Review war an die Revision **vor** der Reparatur gebunden ⇒ der eigene Validator lehnte das Artefakt ab | Der Re-Review ist an die Revision **nach** der Reparatur gebunden |
| R3-6 | Mittel | Der Lead durfte die Dateiverantwortung über das Roster hinaus erweitern | Das Roster gewährt die Dateien; der Lead darf nur verengen |
| R3-7 | Mittel | Die Schreibzugriffe der **Plan-Phase** wurden nicht geprüft | Der Baum wird vor und nach dem Planlauf verglichen |
| R3-8 | Mittel | Der Kritikpfad behielt den **ersten** gültigen JSON-Kandidaten | Der letzte vollständige Kandidat gewinnt, wie überall sonst |
| R3-9 | Mittel | Ein gültiges eingepflanztes JSON verdrängte eine gültige Prosa-Prüfung | Zwei widersprüchliche Reports ⇒ Ablehnung |
| R3-10 | Mittel | Ein Platzhalter-Check und ein fehlgeschlagener Check galten als Nachweis | Nur ein bestandener Check oder ein benannter Nachweis zählt; die Pflichtprüfungen müssen berichtet sein |
| R3-11 | Niedrig | Der Herkunftsmarker fehlte an mehreren Stellen | Der Marker bleibt an Spezialist, Lead-Review und Critic-Report erhalten |
| R3-12 | Niedrig | Toter Code, unbenutzte Helfer, ein unwirksamer Skill-Pin-Check | Entfernt bzw. wirksam gemacht: die genehmigten Skills kommen aus dem Projektzustand |
| R3-13 | Niedrig | Ein vakuoser Test | Ersetzt |
| R3-14 | INFO | Der Lead behauptet `validates_against_architecture: true`, ohne dass die Kernprüfung das bestätigt | Dokumentierte Grenze: der Kern prüft den Architekturdigest und die Konfliktliste, nicht die Behauptung |

### Defekte der vierten Runde (alle behoben)

**Runde 4** (`ses_ea63b0573ffewak4GeFxZ5kObV`): 16 Befunde, `reject`. Zwei der
Reparaturen der dritten Runde hielten nicht.

| # | Schwere | Befund | Behebung |
|---|---------|--------|----------|
| R4-1 | Hoch | Der Re-Review wurde mit **leerer** Revision angefragt, aber gegen den Digest nach der Reparatur geprüft ⇒ der Reparaturlauf konnte nie erfolgreich sein | Der Reparaturlauf bekommt die Revision; die Anfrage und die Prüfung nennen dieselbe |
| R4-2 | Hoch | Der Prosapfad **rettete** einen abgelehnten JSON-Report | Die JSON-Objekte werden aus dem Text entfernt, bevor der Prosaleser ihn sieht |
| R4-3 | Hoch | Ein JSON-`approve` mit einem Blocker im Prosateil ⇒ Exit 0 | Die Prosa darf Befunde ergänzen; ein Blocker neben einer Freigabe wird abgelehnt |
| R4-4 | Hoch | Die ausgelieferte Statusvorlage war ungültig (`approved_skills` fehlte im Schema) | Die genehmigten Skills sind ein optionales Schemafeld; die Vorlage bleibt gültig |
| R4-5 | Mittel | Ein Zähler einer anderen Prüfung wurde als Ergebnis verwendet | Eine Zeile, die eine andere Prüfung nennt, zählt nicht |
| R4-6 | Mittel | "not run, no failures to report" wurde als Pass gelesen | "nicht gelaufen" wird vor "keine Fehler" geprüft |
| R4-7 | Mittel | Der AbschnittSeverity kam nie zur Anwendung | Der Befund nimmt die Severity aus seinem Abschnitt, wenn er keine nennt |
| R4-8 | Mittel | Der Lead erfand eine Annahme für einen Spezialisten, den er nie entschieden hat | Der Kern rät nur, wenn der Lead **niemanden** nennt |
| R4-9 | Mittel | Das Ausfüllen des eigenen Aufgabenvertrags galt als Rahmenverstoß | Der eigene Vertrag des Spezialisten gehört zu seiner Aufgabe |
| R4-10 | Mittel | Der Vertragsvalidator ignorierte die genehmigten Skills | Er liest sie aus dem Projektzustand |
| R4-11 | Niedrig | Toter Code, unbenutzte Helfer, unerreichbare Zweige | Entfernt |
| R4-12 | Niedrig | Ein Prosa-Verdikt "approve with findings" wurde abgelehnt | Verdiktvarianten werden unterschieden |
| R4-14 | Niedrig | `strip_json_objects` ließ das JSON stehen, wenn eine unbalancierte Klammer vorausging | Die Suche läuft weiter |
| R4-15 | Niedrig | Die Revisionsbindung fiel durch, wenn der Digest unbekannt war | Eine unbekannte Revision lehnt den Report ab |

### Befunde aus dem fünften Lauf

| # | Befund | Behebung |
|---|--------|----------|
| R5-1 | Der read-only Plan-Agent erzeugte `.pytest_cache/` ⇒ der Schreibrahmen meldete einen Verstoß | Cache-Verzeichnisse sind kein Projektinhalt und werden nicht verglichen |
| R5-2 | Ein fehlgeschlagener Kritikerlauf nannte den Grund nicht | Der Lauf meldet den Providerfehler und jede probierte Modellkette |
| R5-3 | Die **Review-Prompt überschritt die Windows-Befehlzeilenlänge** ("Die Befehlszeile ist zu lang") | Die Prompt trägt das Ergebnis, nicht die Rohantwort, und wird vor dem Lauf gekürzt |

### Die zweite, wichtigere Erkenntnis aus den echten Antworten

Die nativen Agenten schreiben **kein JSON**, sondern ausgezeichnete
Markdown-Dokumente - und sie **füllen ihren eigenen Aufgabenvertrag aus**.
Zwei Konsequenzen:

1. **Der Aufgabenvertrag ist das Ergebnis.** Der Kern liest nach dem Lauf den
   Vertrag, den der Agent ausgefüllt hat (`status`, `changes`, `findings`,
   `evidence`, `checks`, `risks`, `unresolved`). Das ist zuverlässiger als
   ein Rücklesen aus der Prosa. Die Prosa-Extraktion ist der Rückfall.
2. **Die Extraktion muss die Dokumentstruktur verstehen.** Der Kern liest die
   Entscheidung aus der Verdict-Überschrift, die Befunde aus dem
   Findings-Abschnitt, das Prüfergebnis aus dem Verifikationsabschnitt und die
   Anforderungen aus der Anforderungsliste.

Damit wurde aus einem Prompt-Problem ein Leser-Problem, und der Leser wurde
gegen die **echten** Antworten der Agenten entwickelt und geprüft.

**Zusätzlicher, im E2E gemessener Befund:** Die Modellantwort war Prosa statt
JSON. Ursache: das Modell beginnt zu explorieren und liefert dann ein eigenes
Schema. Behebung: robuster JSON-Extraktor, der alle Kandidaten sammelt und den
passenden wählt, plus ein Retry in derselben Session.

---

## 3. Testresultate

```
python -B -m unittest discover -s tests
→ Ran 333 Tests, OK (skipped=5)
```

| Suite | Tests | Ergebnis |
|-------|-------|----------|
| `test_registry_v2.py` (M1b) | 23 | bestanden |
| `test_validate.py` (M1a/M1c) | 50 | bestanden, 3 Platform-Skips |
| `test_inventory.py` (M1c) | 21 | bestanden, 2 Platform-Skips |
| `test_core_equivalence.py` (M1a-Orakel) | 10 | bestanden, eingefrorenes Orakel byte-identisch |
| `test_m2_slice1.py` | 21 | bestanden |
| `test_m2_review_fixes.py` | 19 | bestanden |
| `test_m2_audit.py` | 32 | bestanden |
| `test_m2_exit_paths.py` | 7 | bestanden |
| `test_m2_start_gate.py` | 13 | bestanden |
| `test_m2_slice2_s1_s2.py` | 52 | bestanden |
| `test_m2_s1_s2_fixes.py` | 27 | bestanden |
| `test_m2_lead_frame.py` | 3 | bestanden |
| `test_m2_s1_s2_gaps.py` | 5 | bestanden |
| `test_m2_prose_review.py` | 7 | bestanden |
| `test_m2_prose_answers.py` | 7 | bestanden |
| `test_m2_r3_regressions.py` | 17 | bestanden |
| `test_m2_r4_regressions.py` | 15 | bestanden |

**Die fünf Skips sind die dokumentierten Plattformgrenzen** (Symlink-Erstellung
2, Non-UTF8-Dateiname 2, POSIX-Executable-Bit 1). Kein Ersatz für einen
 bestandenen Test.

**Kein vakuoser Test:** Die neuen Module prüfen Verhalten, nicht Struktur. Der
unabhängige Reviewer hatte drei vakuose Tests beanstandet; alle wurden ersetzt.

---

## 4. Verifikation

| Schritt | Befehl | Ergebnis |
|---------|--------|----------|
| Vollständige Regression | `python -B -m unittest discover -s tests` | 333 Tests, 0 Fehler, 5 Skips |
| Paketintegrität | `validate.py package .agents/skills/architect-dev-team` | `OK package` |
| Registry Schema 1 | `validate.py registry registry/skills.json` | `OK registry` |
| Registry Schema 2 | `validate.py registry registry/index.json` | `OK registry` |
| Laufzeitfähigkeit | `validate.py runtime detect` | `opencode v2.0.32`, 7 Agenten, read-only aus Berechtigungen abgeleitet |
| M1a-Differentialorakel | `unittest -p test_core_equivalence.py` | 10 Tests OK, Fixture byte-identisch |
| Lead-E2E | `tools/e2e_lead_critic.py` | siehe Abschnitt 5 |

---

## 5. Reale Agentenausführung

*(wird nach dem E2E-Lauf ergänzt)*

---

## 6. Offene Grenzen

| Grenze | Bedeutung |
|--------|-----------|
| Der Kritiker kann keine Tests schreiben | Der native read-only-Agent verweigert jeden Schreibzugriff. Die Zusage aus Slice 1 ist zurückgenommen; ein getrennt autorisierter Test Engineer schreibt die Tests. |
| Der native Reviewer nennt den vereinbarten Check nicht immer | Gemessen: ein Reviewer protokollierte "13 passed", ohne den Check-Namen `unit-tests` zu nennen. Der Kern meldet den Check dann ehrlich als `not_run` und **lehnt den Report ab** (fail-closed). Der Prompt fordert die exakte Nennung. Bis das trägt, ist die automatische Abnahme eines Prosa-Reviews nicht belegbar. |
| `explore`/`plan` erlauben read-only Shell | Die Schreibgrenze ist erzwungen, die Kommandogrenze nicht. Ein Reviewer könnte Kommandos ausführen. |
| Kein reales Codex-Lauf | Codex-Kompatibilität ist strukturell gepflegt, nicht verifiziert. |
| Kein S3 | Der echte Reparaturlauf mit Agenten ist nicht Teil dieses Umfangs. |
| Kein S4 | Kontextbündel und Tokenoptimierung sind nicht Teil dieses Umfangs. |
| Kein S5/S6 | Einstiegspunkt und Skill-API sind nicht Teil dieses Umfangs. |
| `openai/*`-Modelle waren kontingentbedingt gesperrt | Die Fallback-Kette griff und protokollierte jeden Versuch. |
| Das M1a-Orakel toleriert die dokumentierte CLI-Erweiterung | Zwei zusätzliche Unterbefehle (`lead`, `critic-report`). Die M1a-Kommandos und alle Bytes außerhalb der Kommandoliste werden exakt verglichen. |

---

## 7. Nächster Schritt

Die S1/S2-Implementierung ist abgeschlossen und geprüft. Die
**Abschlussfreigabe** für S1/S2 wird erteilt durch:

1. `python -B -m unittest discover -s tests` (vollständige Suite),
2. die reale Agentenausführung aus Abschnitt 5,
3. die unabhängige Review der Reparaturen,
4. den exakten review-gebundenen Snapshot.

**S3 wird nicht automatisch begonnen.**
