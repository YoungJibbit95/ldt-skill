# LittleDevTeam Website — W3-Vorschlag, Revision 1

Status: Architekturvorschlag zur menschlichen Freigabe, 18. Oktober 2026.
Profil: Balanced. Grundlage ist der [ursprüngliche Website-Plan](website-plan.md).
Dieser Vorschlag ändert den freigegebenen historischen Plan nicht.

Jetzt zur Entscheidung steht die Umsetzung des beschriebenen W3-Feinschliffs,
der Release-Vorbereitung, Tests und unabhängigen Reviews. Merge, erstmalige
Pages-/Environment-Einrichtung und Deployment benötigen später eigene Freigaben
für den konkreten Stand. Externe Skill-Installationen sind getrennte Entscheidungen.

## Ausgangspunkt und Ziel

W2 ist für `db71e831f3345767282bf12ffd47c9898ab6aca9` ausdrücklich abgeschlossen.
Der zugehörige Snapshot lautet `baf26a03b6593b074e9f2f1d580e2e94648b292549dcb88f3a74192852a4b102`.
Commit, verbindliche Prüfpolitik, Snapshot und erfolgreiche CI wurden vor der
Freigabeaufzeichnung erneut geprüft; Review- und Advance-Gate bestehen. Lokale
Nachweise sind separat archiviert und werden nicht als Website-Inhalte importiert.
W2 bleibt eine Eigenprüfung. Die nun beteiligten Planungsagenten prüfen W2 nicht
nachträglich unabhängig frei. [PR #2](https://github.com/YoungJibbit95/ltd-skill/pull/2)
ist offen; seine Freigabe erlaubt keinen Merge.

Vorhanden sind 26 statische HTML-Seiten mit deutscher und englischer Einführung,
Installation, Guide, Referenz, Suche, Simulation und Fallstudie. W2-Nachweise:
19 erfolgreiche Browsertests, 1.087 interne Link-/Asset-/Ankerprüfungen,
Typprüfung ohne Befunde, Axe ohne schwerwiegende/kritische Befunde sowie
Installations-Smokes auf Windows, macOS und Linux. Tatsächliche Codex-Erkennung
ist dadurch nicht belegt. Dokumentierter Skill-Stand bleibt
`9a062eb9de0990ce1074dd677d26e5a528ee14a0`; Website-Release und Skill-Stand sind
zwei unterschiedliche Versionsangaben.

Das ursprüngliche W3-Ziel bleibt **abschließender Review und geprüfte
GitHub-Pages-Veröffentlichung**. Es gibt keinen Ersatzmeilenstein. Die fünf
ursprünglichen Pflichtprüfungen bleiben erhalten; unabhängiger Review kommt als
verbindliche Prüfung hinzu. Der bisherige Rahmen legt weder den neuen Text- und
Designumfang noch das genaue Veröffentlichungsverfahren fest. Die neue
Nutzeranweisung erlaubt zunächst Planung; deshalb benötigt diese Revision vor
Produktänderungen eine Architekturfreigabe.

Die Repository-API meldet derzeit `has_pages: false`; es gibt keine Deployments.
Lighthouse, Release-Artefakte, Pages-Workflow und öffentliche URL-Prüfungen fehlen.
Die veröffentlichte Adresse soll `https://youngjibbit95.github.io/ltd-skill/` sein.

## Gestaltung: drei untersuchte Richtungen

| Richtung | Bewertung am vorhandenen Projekt | W3-Entscheidung |
| --- | --- | --- |
| Developer Workbench | Auftrag, Vorschlag, Entscheidung und Nachweis passen zu Mission-Fläche und Demo. Hohe Produktnähe bei kleinem Eingriff. | Empfohlene Richtung für begrenzten Feinschliff. |
| Technical Design Studio | Typografische Ruhe und redaktionelle Hierarchie helfen der Dokumentation. Ein vollständiger Layoutwechsel würde W2 unnötig ersetzen. | Lesbarkeit und Abstände übernehmen; kein neues Seitensystem. |
| Living Multi-Agent System | Agentenbeziehungen könnten Abläufe erklären, könnten aber permanente Live-Agenten suggerieren. Mehr JS, Bewegung und Prüfaufwand. | Animiertes Netzwerk und neue Diagramm-Demo für spätere gesonderte Planung zurückstellen. |

Nebula, Orbitzeichen, Space Grotesk und Inter bleiben erhalten. Die bestehende
Farbgrundlage bleibt `#090b18`, `#101225`, `#f4f1fc`, `#a4a5bb`, `#b49bfc`,
`#ed93db`. Kontrastmessungen können begrenzte Tokenkorrekturen begründen.
Der Master Lead hat vorhandene Desktop-Home- und mobile W2-Demo-Aufnahmen
gesichtet; die Design-Lead-Untersuchung war quellcodebasiert. Neue Browserabnahmen
und Vorher-/Nachher-Vergleiche gehören erst zur Umsetzung.

Der Hero behält seine Zweiteilung aus Produkteinstieg und Workflow-Beispiel.
Die Reihenfolge lautet: Was ist der Skill? → Installieren oder Demo öffnen →
Auftrag, Architekturvorschlag und menschliche Entscheidung erkennen.
Auf Mobilgeräten folgt das Beispiel dem Einstieg in normaler Lesereihenfolge.
Es entstehen keine zusätzlichen gleichförmigen Marketing-Karten. Kleine Labels
werden reduziert, wenn sie keine Information tragen. Kerninformationen im
Workflow erhalten mindestens 14 px, längerer Fließtext mindestens 16 px.
Dekorative Koordinaten sind davon ausgenommen und vermitteln keine Pflichtinformation.
Primäre Bedienelemente erhalten mindestens 44 × 44 CSS-Pixel große Ziele.
Keine neuen Bilder, Video-Loops, 3D-Szenen oder Animationsbibliotheken.

## Inhalt und fachliche Grenzen

Die Zielgruppen bleiben Einsteiger, Codex-Nutzer und erfahrene Entwicklerteams.
Die Informationsfolge ist: Skill erklären, Architektur vor Umsetzung, passende
Spezialisierung, menschliche Freigaben, Meilensteine und Review, Installation,
erster realer Auftrag und belegte Entstehung dieser Website.
Deutsch verwendet „du“; Englisch wird eigenständig und sinngleich formuliert.
Bezeichner, Befehle und Datenformate werden nicht sprachlich umgebaut.

Der Content Lead legt vor jedem Entwurf Zielgruppe, Kernbotschaft und Quellen
fest. `writing-clearly-and-concisely` ist der Standard für alle geänderten
menschlich lesbaren Texte, einschließlich Labels und Fehlermeldungen. Aktive
Verben, konkrete Aussagen, ein Thema je Absatz und konsistente Aktionsnamen
gelten in beiden Sprachen; englische Grammatikregeln werden nicht mechanisch
auf Deutsch übertragen.

Geplanter begrenzter Textumfang:

- Home: Der erste erklärende Satz benennt LittleDevTeam als Skill für Codex.
  Das Workflow-Stück erklärt an einem Beispiel, wie ein führender Agent passende
  Spezialisten beauftragt und Ergebnisse integriert. Zusätzliche Agenten werden
  nur eingesetzt, wenn ihre Aufgaben sinnvoll trennbar und ihre Werkzeuge
  verfügbar und erlaubt sind.
- Überblick: veraltete Beschreibung als bloßer W1-Einstieg auf den tatsächlichen
  W2-Inhalt aktualisieren.
- Workflow: Rollen als Verantwortlichkeiten erklären; ein Einzelagent kann
  Rollen nacheinander ausführen, das ergibt keinen unabhängigen Review.
  Externe Skills liefern wiederverwendbare Anleitung und erzeugen keine Agenten.
- Guide: Besuchern zeigen, wie sie nach tatsächlich eingesetzten Rollen,
  Ergebnissen, Prüfnachweisen und Review-Unabhängigkeit fragen.
- Fallstudie: tatsächlichen W2-Abschluss mit Commit, PR und CI verknüpfen.
  W3-Planung, spätere Umsetzung und unabhängige Reviews nur nach tatsächlicher
  Durchführung benennen. Menschliche Entscheidungen redaktionell zusammenfassen;
  lokale Freigabeprotokolle bleiben privat.
- Installation und übrige Referenz: auf Genauigkeit und Lesbarkeit prüfen;
  Änderungen nur bei konkreten Befunden. Die Registry ist nicht defekt:
  Schema 1 enthält einen Kandidaten, der Schema-2-Index drei.

Die Simulation führt keine Agenten aus und erteilt keine Projektfreigaben.
Geplante V2-Funktionen werden als Planung gekennzeichnet. Keine erfundenen
Kunden, Nutzerzahlen, Benchmarks, Sicherheits- oder Produktivitätsversprechen.

## Externe Skills: Auswahl und Freigabestatus

Recherche: Repository-Eigentümer, vollständige Revision, relevante Manifeste,
vorhandene Lizenztexte und erkennbare Abhängigkeiten; keine Sicherheitszertifizierung.
Die lokale Suche umfasste persönliche Skill-Verzeichnisse, Projekt-Skills und
Plugin-Cache. Herkunftsangaben belegen keine individuelle Autorenidentität.
Kein Kandidat wird in die Skill-Registry oder Website-Assets übernommen.

| Kandidat / geprüfter Stand | Befund und Relevanz | Verwendung / Status |
| --- | --- | --- |
| [Softaworks Writer](https://github.com/softaworks/agent-toolkit/tree/3027f20f3181758385a1bb8c022d4041dfb4de84/skills/writing-clearly-and-concisely), `3027f20f3181758385a1bb8c022d4041dfb4de84` | Textdateien; Root-MIT, Copyright Leonardo Flores. Englische Stilregeln, Strunk- und Wikipedia-bezogene Referenzen; deren vollständige Drittquellen-Rechteprüfung ist nicht behauptet. | **Einzeln vom Nutzer zur Installation freigegeben und persönlich installiert.** Acht Quelldateien am Pin verifiziert, Root-Lizenz erhalten. Standard für geänderte Texte; Referenzen nicht veröffentlichen. |
| [Anthropic Frontend Design](https://github.com/anthropics/skills/tree/dbd4588f9e1033efb41dad4bef2f7947c8993d44/skills/frontend-design), `dbd4588f9e1033efb41dad4bef2f7947c8993d44` | Eigentümer anthropics; ausgewählte Apache-2.0-Lizenz liegt beim Skill. Reine Designanleitung ohne ausführbare Begleitdateien; bestehender Brief hat Vorrang. | Empfohlener **primärer Kreativ-Skill**, falls separat zur Installation freigegeben. Nicht installiert oder ausgeführt. Ohne Freigabe arbeitet der Design Lead nativ am vorhandenen Design. |
| [Taste Skill](https://github.com/Leonxlnx/taste-skill/tree/f624f37a8c650b9cc550253104925efe4c8de246/skills/taste-skill), `f624f37a8c650b9cc550253104925efe4c8de246` | Eigentümer Leonxlnx; Root-MIT. Manifest `design-taste-frontend` verlangt mehrere Rasterbilder und viele bewegte Elemente. | Für dieses W3 wegen Konflikt mit Umfang und ruhiger Identität zurückgestellt; Begleitskripte nicht vollständig geprüft. |
| [Impeccable](https://github.com/pbakaus/impeccable/tree/2f46b7a8b059af00d20dd13b64dbe165e7c6a742/.agents/skills/impeccable), `2f46b7a8b059af00d20dd13b64dbe165e7c6a742` | Eigentümer pbakaus; Apache-2.0 und NOTICE. Version 4.6.0 verwendet Launcher/Binärdatei, gegebenenfalls mit Download; Windows-Nachweis begrenzt. | Für W3 nicht nötig; keine Installation, Ausführung oder vollständige Binärprüfung. |
| [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/tree/56ea9cf174ed86786187daa9de0e6247cb0747e4/.claude/skills/ui-ux-pro-max), `56ea9cf174ed86786187daa9de0e6247cb0747e4` | Eigentümer nextlevelbuilder; Root-MIT. Python-/CSV-Suche mit Astro-Daten; Claude-spezifische Pfade und lokale Imports müssen geprüft werden. | Optionales späteres Nachschlagewerk; kein Skript ausgeführt, keine Installation, keine vollständige Abhängigkeitsprüfung. |
| [Vercel Web Design Guidelines](https://github.com/vercel-labs/agent-skills/blob/063bee94c3f4df8453406c830b0a7df0f2860278/skills/web-design-guidelines/SKILL.md), `063bee94c3f4df8453406c830b0a7df0f2860278` | Eigentümer vercel-labs. Manifest lädt bei jedem Review Regeln aus einem weiteren Repository am beweglichen `main`. Keine Lizenzdatei im untersuchten Repository-Baum gefunden. | Nicht ausgewählt; Lizenz- und Versionsbindung der externen Regeln wären vor Einsatz zu klären. Native Qualitätsprüfung genügt. |
| [Softaworks Design System Starter](https://github.com/softaworks/agent-toolkit/tree/3027f20f3181758385a1bb8c022d4041dfb4de84/skills/design-system-starter), gleicher Softaworks-Pin | Token-/A11y-Hinweise relevant, React-, Storybook- und ThemeProvider-Vorlagen für diese Astro-Seite unverhältnismäßig. | Nicht installieren. Vorhandene CSS-Tokens gezielt prüfen. |
| [Offizielle Figma-Skills](https://github.com/openai/skills/tree/49f948faa9258a0c61caceaf225e179651397431/skills/.curated), `49f948faa9258a0c61caceaf225e179651397431` | Eigentümer openai; Figma-bezogene Skills sind auch als installierte Plugin-Fähigkeiten verfügbar. Keine Figma-Datei oder Designquelle beauftragt. | Für dieses W3 nicht relevant; kein Figma-Zugriff und keine zusätzliche Installation. Katalogdeprecation ist kein Beweis fehlender Dateien. |

`humanizer` bleibt optionaler späterer Feinschliff; `crafting-effective-readmes`
ist nur bei konkreter README-Arbeit relevant. Beide liegen am genannten
Softaworks-Pin, wurden oberflächlich auf Eignung geprüft und sind nicht installiert.
Die Humanizer-Anweisung zum Klonen eines anderen Repositories wird nicht befolgt.
Für W3 reicht der freigegebene Writer plus native Gestaltung/Prüfung; zusätzliche
Skill-Installation und Anwendung benötigen eine ausdrückliche eigene Entscheidung.
Die Lizenzen fremder Skills bestimmen keine LittleDevTeam-Projektlizenz.

## Team und detaillierte Arbeitsverträge

Der Master Lead / Engineering Director verantwortet Ziel, Architektur, Abhängigkeiten,
Freigaben und Integration. Vier Leads sind Verantwortlichkeiten, keine Pflicht zu
vier gleichzeitig aktiven Prozessen. Es gelten höchstens vier aktive Agenten
einschließlich Master. In dieser Planung wurden Design, Content und Frontend
begrenzt parallel untersucht; Quality prüft anschließend den integrierten Vorschlag.
Zusätzliche Spezialisten sind für die Planung nicht nötig.

Vor einer Spezialistenaufgabe prüft der zuständige Lead Umfang, Voraussetzungen,
Schreibbesitz und Abnahme. Jeder Vertrag nennt Ziel, Revision/Proposal, exakte
Lese- und Schreibpfade, Quellen, Nichtziele, Prüfbefehle, Rückgabeformat und
Stopps bei Konflikten oder fehlender Autorisierung. Spezialisten dürfen nicht
selbst weiterdelegieren, installieren, freigeben, mergen oder veröffentlichen.
Der zuständige Lead prüft das Ergebnis als anderer tatsächlicher Agent; der
Master prüft anschließend die Integration. Rollenwechsel desselben Agenten
werden niemals als unabhängiger Review bezeichnet.

| Verantwortung | Geplanter begrenzter Auftrag nach Freigabe | Abgabe / Prüfung |
| --- | --- | --- |
| Design Lead | Richtung und Typografie vor Entwurf festlegen; gegebenenfalls UI-Spezialist für bestehende CSS-Dateien beauftragen. | Token-/Lesbarkeitsbefunde und Render-Abnahme; Lead prüft Spezialisten-Diff und Desktop/Mobil-Aufnahmen. |
| Content Lead | Botschaft/Quellen festlegen; DE/EN-Redaktion mit Writer, höchstens ein Spezialist für den beschriebenen Dateisatz. | Bedeutungsgleiche natürliche Texte; Lead prüft Fakten, Übersetzung und Nachweislinks unabhängig vom Verfasser. |
| Frontend Lead | Bestehende Astro-Komponenten integrieren; Release-/Performance-Werkzeuge und manuelle Pages-Pipeline getrennt beauftragen. | Disjunkte Dateiverantwortung und ausführbare Prüfnachweise; Lead prüft tatsächlichen Diff und Artefaktbindung. |
| Quality Lead | Anderer Agent als jeweiliger Implementierer; finale Quellrevision, Tests, Bedienung, A11y, Performance und Release-Vertrag untersuchen. | Befunde mit Pfad/Schwere/Nachweis; Fehler nach Reparatur erneut prüfen. Fehlende Unabhängigkeit blockiert die neue Pflichtprüfung. |

Gemeinsame Home-Dateien werden nacheinander bearbeitet: Content vor Integration,
CSS parallel nur bei klarer Zuständigkeit. Planungsergebnisse sind kein bereits
durchgeführter Implementierungsreview. Reviewer-Identität, Revision, Befunde und
Auflösung werden bei der tatsächlichen Prüfung dokumentiert.

## Dateien, Schnittstellen und Abhängigkeiten

- Texte: `website/src/pages/[locale]/index.astro`,
  `built-with-littledevteam.astro`, gepaarte `docs/index.mdx`, `workflow.mdx`,
  `guide.mdx`; übrige Referenz nur bei konkretem Befund.
- Gestaltung: bestehende `src/styles/global.css`, `demo.css`; `docs.css`,
  Header und Layout nur für belegte Lesbarkeits-, Fokus- oder Integrationsprobleme.
- Release: `.github/workflows/website.yml` erweitern, manuelles `pages.yml`
  ergänzen, passende `website/scripts/` für Performance, Release-Manifest und
  öffentliche URLs; `website/README.md` und `docs/website-release.md` für Betrieb.
- Tests: vorhandene Playwright-Tests um vollständige Breiten-/Routenprüfung und
  kontrollierten öffentlichen Prüfmodus ergänzen; keine erfundenen Server-APIs.
- Werkzeuge: Lighthouse als exakt gepinnte Entwicklungsabhängigkeit; aktuell
  ermitteltes `13.5.0` erklärt Node `>=22.19` und passt damit grundsätzlich zu
  Node 24. Die konkrete Integration und Chromium-Version werden getestet und
  gelockt. Kein LHCI-Dienst und keine Runtime-UI-Abhängigkeit erforderlich.

Astro/Starlight, `/ltd-skill/`, alle DE/EN-Seitenschlüssel und lokale Fonts bleiben
erhalten. Skill-Quellcode, Registry, ursprüngliche Arbeitsstände und deren
Zustandsdateien bleiben außerhalb des Auftrags. Keine Domain, Analysewerkzeuge,
Konten, Backend, Live-Agenten oder neue Projektlizenz.
Der lokale Planungsbranch baut auf dem freigegebenen W2 auf; PR #2 bleibt unberührt.
Vor Umsetzung wird der aktuelle Remote-Stand neu abgeglichen. Ein gestapelter
Feature-Branch darf die W2-Abhängigkeit sichtbar ausweisen und keinen Merge erzwingen.

## Ein W3, getrennte Freigaben vor Veröffentlichung

Zuerst entstehen nach Architekturfreigabe die begrenzten Änderungen, alle lokal
ausführbaren Prüfungen und ein eindeutig identifizierter Release-Kandidat.
Das Ergebnis wird mit Commit, Artefakt-ID, Archiv-SHA-256, vollständigem Bericht
und unabhängigen Reviewbefunden vorgelegt. `published URL checks` bleibt dabei
`not_run`. Auch `performance` bleibt bis zur öffentlichen Messserie `not_run`,
mit gesondertem Nachweis der bestandenen lokalen Teilprüfung. Erst beide Serien
erlauben `passed`. Dieser Zwischenstand ist kein abgeschlossenes W3 und erhält
keinen bestandenen finalen Review-/Advance-Gate durch eine Ausnahme.

Es wird kein Deployment bei Push, Merge oder grünen Tests ausgelöst. Der
vorbereitete Veröffentlichungsworkflow ist ausschließlich manuell auslösbar.
Er verwendet einen angegebenen erfolgreichen Lauf dieses Repositories und prüft
Workflow-Herkunft, Quell-SHA, Manifest und Archiv-Hash. Er veröffentlicht die
geprüften Bytes, ohne sie nach Freigabe stillschweigend neu zu bauen.
PR-Artefakte unbekannter Forks sind keine veröffentlichbaren Kandidaten.
Alle Pflichtnachweise müssen zur selben Kandidatenrevision gehören. Gezielte
Negativtests müssen veränderte Archive oder Manifeste, falsche Quellrevisionen,
falsche Workflows/Repositories und fehlgeschlagene Herkunftsläufe vor Erreichen
des Deployment-Jobs abweisen. Diese Vertragsprüfungen veröffentlichen nichts.
Build-/Prüfjobs haben keine Pages-Schreibrechte. Nur der separate Deployment-Job
bekommt minimale Pages-/OIDC-Rechte und das `github-pages`-Environment.
Das entspricht der [GitHub-Trennung von Build und Deployment](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

Vor dem Auslösen sind drei konkrete Entscheidungen erforderlich: Merge des
benannten PR-/Commit-Stands, erstmaliges Einrichten von Pages/Environment soweit
nötig und Deployment des benannten Artefakts. Sie können in einer Antwort klar
getrennt erteilt werden. Die aktuelle Planungsfreigabe und eine spätere
Architekturfreigabe erteilen diese Befugnisse nicht. Der Deploy-Commit muss auf
`main` erreichbar sein. Ein Squash/Rebase mit neuer SHA verlangt aktualisierte
Prüfungen und eine passende Freigabe; alte Commitidentitäten werden nicht gleichgesetzt.

Das Kandidatenarchiv enthält die gebauten Dateien und eine Datei mit öffentlicher
Website-Quellrevision; private Freigaben oder Entwicklungsprotokolle fehlen darin.
Ein äußeres Manifest nennt Run/Workflow, Werkzeugversionen, Quellrevision,
Dateihashes und Archiv-Hash. Keine selbstreferenziellen Archivprüfsummen.
Prüfberichte und wiederherstellbares Archiv werden für 90 Tage aufbewahrt, soweit
Repository-Grenzen das erlauben; Ablaufdatum und Download-Nachweis sind Teil der
Abnahme. Kein unbegrenztes Wiederherstellungsversprechen.

Es gibt noch kein früheres Deployment. Beim ersten Release kann dasselbe
geprüfte Artefakt erneut veröffentlicht werden; eine frühere Website kann nicht
hergestellt werden. Ein Abschalten benötigt eigene Autorisierung. Sobald das erste
Release öffentlich geprüft ist, wird es die erste Wiederherstellungsbasis.
Vor späteren Releases wird das vorherige geprüfte Artefakt gesichert. Wiederherstellung
verwendet genau dieses Archiv und wiederholt die öffentlichen Prüfungen.

## Verbindliche Abnahme und Prüfplan

| Stabiler Pflichtprüfname | Bestehenskriterium / Nachweis |
| --- | --- |
| `full website checks` | Node 24, `npm ci`, Content-/Quellabgleich, Typprüfung, Produktionsbuild, interne Links und Playwright erfolgreich; DE/EN-Inhalte vollständig und ohne JS lesbar. Installations-Smokes auf allen drei Betriebssystemen bleiben erhalten. |
| `existing skill checks` | Vorhandene Paket-, beide Registry- und Regressionsprüfungen der bestehenden Linux/Windows- und Python-3.10/3.12-CI unverändert erfolgreich. |
| `accessibility` | Beide Sprachen und alle Inhaltsrouten bei 375/768/1440 ohne horizontalen Überlauf; manuelle Tastatur-/Fokusprüfung von Header, Suche, Sprachwahl, Codekopie und Demo; 200-%-Zoom und reduzierte Bewegung. WCAG-AA-Kontraste; Axe ohne schwerwiegende/kritische Befunde. Suchdialog und geänderte Demozustände mitprüfen. |
| `performance` | Tatsächlich ausgeführtes Lighthouse Mobile auf `/de/`, `/en/`, `/de/docs/install/`, `/en/docs/install/`: je drei Läufe mit kaltem Cache und festgehaltenem Lighthouse/Chromium/Runner. Median je URL mindestens 90; alle Einzelergebnisse erhalten. Gleiche Messserie nach Deployment separat auf öffentlichem Ursprung; beide Serien bestehen. Keine ausgewählten Wiederholungen bis zu einem guten Wert. |
| `published URL checks` | Erst nach autorisiertem Deployment: vollständige direkten DE/EN-Aufrufe und Reloads, tatsächliche Releaseidentität, deutsche Startweiterleitung, Assets/Fonts/Favicon und Pagefind unter `/ltd-skill/`, Canonical/Hreflang, Sprachwechsel, lokalisierte Suche samt Leerzustand, Demo, mobile Navigation, Kopieren, repräsentative Live-Axe- und No-JS-Prüfung; unbekannte URL liefert tatsächliches HTTP 404. |
| `independent_review` | Tatsächlich andere Agenten prüfen finalen Diff und Nachweise für Design, Inhalt, Frontend/Release und Qualität. Master integriert; keine offenen blockierenden Befunde. Fehlende Prüfer werden nicht als Eigenprüfung bestanden. |

Lighthouse kann abhängig von der Messumgebung schwanken; die vorgeschlagene
vorab festgelegte Medianregel macht die Abnahme nachvollziehbar. Sie ist eine
Projektentscheidung, kein behaupteter bereits gemessener Wert. Grundlage:
[Lighthouse-Leistungsbewertung](https://developer.chrome.com/docs/lighthouse/performance/performance-scoring).
Live-Prüfungen dürfen für Pages-Verteilung begrenzt wiederholen, beispielsweise
höchstens fünf Minuten mit protokollierten Versuchen. Bleibende Fehler blockieren
W3; lokale Ergebnisse ersetzen keine veröffentlichten URL-Nachweise.

Nach der Veröffentlichung werden Quellstand, Artefakt und tatsächliche URLs erneut
abgeglichen, das Review an den aktuellen Snapshot gebunden und erst dann das
vollständige W3-Ergebnis zur Abschlussfreigabe vorgelegt. Eine grüne Pipeline
authentifiziert keine menschliche Entscheidung.

## Risiken und jetzt erbetene Entscheidung

Performance ist noch nicht gemessen; Font-Subsets, große Blur-Flächen oder
deklarative Bewegung werden nur nach konkreten Befunden angepasst. Pages und
Environment sind noch nicht eingerichtet. Artefaktaufbewahrung kann durch
Repository-Grenzen beschränkt sein. Der Skill-Quellstand bleibt älter als die
Website. Tatsächliche Codex-Erkennung bleibt als nicht geprüft gekennzeichnet,
sofern kein echter Codex-Lauf in einer verfügbaren Umgebung erfolgt.

**Erbeten ist die Architekturfreigabe dieser Revision für begrenzten W3-Feinschliff,
Release-Vorbereitung, Tests und unabhängigen Review.** Sie umfasst keinen Merge,
keine Pages-/Environment-Aktivierung und kein Deployment. Die schon genehmigte
Writer-Installation ist davon getrennt. Anthropic Frontend Design bleibt eine
optionale, gesondert zu genehmigende Installation; seine Ablehnung blockiert die
native Umsetzung nicht. Ein grundlegendes Redesign braucht einen neuen Vorschlag.
