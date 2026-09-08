# Agenten-Anbindung fuer Statik

Plan fuer den Weg von "Mensch klickt Systeme in der Web-UI" zu
"Agent bekommt ein Bild und laesst es hier rechnen".

**Grundsatzentscheidung:** Das Sehen macht der Agent, nicht das
YOLO-Modell. Statik stellt keine Erkennung bereit, sondern eine
*Werkbank*: bauen, zeichnen, pruefen, rechnen.

---

## 1. Ist-Zustand

**Backend** (Flask, Plugin-Architektur, 5 Blueprints in `backend/src/__init__.py`):

| Plugin | Endpunkt | Zustand |
|---|---|---|
| `analyze` | `/api/analyze/{kinematics,simplify,solution,dynamics}` | fertig, **stateless** |
| `management` | `/api/systems_management/{save,list,load,delete}` | fertig, slug-basiert |
| `generator` | `/api/generation/*` | synthetische Datensaetze (Bild + Wahrheit) |
| `models` | `/api/models/{train,status,list}` | YOLO-Training |
| `labeling` | `/api/labeling/*` | Handlabeln der Realbilder |
| `vision` | — | kein Blueprint, **bleibt vorerst so** |

**Was schon passt und man nicht anfassen muss:**

- Die Analyse-API ist bereits genau richtig geschnitten fuer Agenten:
  ein POST mit dem vollstaendigen System-JSON, eine Antwort. Kein
  Session-State, kein Klickpfad.
- `src/models/image_models.py` hat `ImageSystem.convert_to_real_system()`
  und `render_structure_to_image(system)` (aus `generator/image/renderer.py`).
  Die Richtung Pixel -> Statik existiert also schon; fuer den Plan
  brauchen wir die Umkehrung.
- `SystemManager` mit Slugs ist bereits die Ablage, in die ein Agent
  etwas legen kann.

**Was fehlt:**

- Kein kompaktes Eingabeformat — das jetzige ist fuer die UI gemacht.
- Kein Weg, ein gebautes System als Bild zurueckzubekommen.
- Das Frontend hat genau eine Route (`index("routes/home.tsx")`). Ein
  System laesst sich nicht per URL oeffnen — der Agent kann also auf
  nichts zeigen.

---

## 2. Warum der Agent selbst sieht

Das YOLO-Modell ist auf Symbole trainiert (Lager, Lasten, Gelenke), nicht
auf Staebe. Selbst mit perfektem Modell fehlte die Topologie: welcher Stab
verbindet welche Knoten, was ist Bemassung, was Tragwerk. Diese Luecke
muesste ohnehin ein semantischer Schritt schliessen.

Wenn der Agent ohnehin die Semantik liefert, kann er auch gleich sehen.
Und fuer Baustatik-Zeichnungen ist das guenstiger, als es klingt:

**Uebungsblaetter sind bemasst.** Auf einem Blatt steht `l = 6,00 m`,
`4,00 m`, `q = 10 kN/m`. Der Agent *liest die Zahlen* statt Pixel zu
messen — das ist genauer als jede Detektion und loest nebenbei das
Massstabsproblem, das im alten Plan noch offen war. Pixelkoordinaten
braucht man nur dort, wo nichts bemasst ist.

**Konsequenzen, die den Bau vereinfachen:**

- Das Bild muss das Backend nie erreichen. Der Nutzer legt es in den
  Chat, der Agent sieht es nativ. Kein Upload-Endpunkt, keine
  Bilderablage, keine YOLO-Inferenz pro Request — und damit auch keine
  offene Rechenlast am oeffentlichen Gateway.
- `requirements.txt`, Torch, Worker-Speicher: alles unveraendert.
- Etappe 1 wird deutlich kleiner.

**Was dafuer schwerer wiegt:** Es gibt keine zweite Meinung mehr. Ohne
Detektionen ist die Rueckkopplung (Abschnitt 4) nicht mehr Kuer, sondern
das tragende Element. Wenn der Agent falsch liest, faellt es nur dort auf.

---

## 3. Architektur: drei Schichten

```
   Agent (Claude Code / Desktop) ── sieht das Bild selbst
      |
      |  MCP (stdio, spaeter optional HTTP)
      v
   mcp/  ── duenner Server, keine Statik-Logik
      |
      |  HTTP
      v
   /api/agent/*        <── auch von der Web-UI nutzbar
      |
      v
   bestehende Plugins (analyze, management, generator/renderer)
```

**Regel: in `mcp/` steht keine Fachlogik.** Jedes MCP-Tool ist ein
HTTP-Aufruf. Sonst hat man die Statik-Regeln zweimal und die Web-UI
bekommt nichts von der neuen Faehigkeit ab.

---

## 4. Der Loop — jetzt das Kernstueck

Ohne Detektionen ist die Sichtkontrolle die einzige Fehlerkorrektur.
Deshalb muss sie gut sein, nicht nur vorhanden:

```
  Bild (im Chat, der Agent sieht es direkt)
   |
   v
 build_system   ──> Agent baut das kompakte System
   |                 Masse aus der Bemassung, nicht aus Pixeln
   v
 render         ──> PNG zurueck an den Agenten
   |                 "sieht das aus wie das Eingangsbild?"
   |<─────────────────────────── korrigieren (update_system)
   v
 validate       ──> Kinematik: DOF, Mechanismen, Doppelgelenke
   |                 "ist das ueberhaupt rechenbar?"
   |<─────────────────────────── korrigieren
   v
 analyze        ──> Schnittgroessen / Dynamik
```

Zwei Dinge sind hier technisch wichtig:

**Das Render-Ergebnis muss als Bild zurueck, nicht als Pfad.** MCP-Tools
duerfen Bildinhalte liefern (base64 + mimeType); Claude Code und Desktop
reichen die ans Modell weiter. Ein Dateipfad im Antworttext waere
wertlos — der Agent muss das Ergebnis *ansehen* koennen.

**Der Renderer spricht dieselbe Bildsprache wie die Vorlage.** Der
Stanli-Renderer zeichnet genau die Symbole, die auch auf dem
Uebungsblatt stehen. Genau das macht den Vergleich ueberhaupt
aussagekraeftig — ein generischer Plot waere hier viel schwaecher.

`validate` ist der zweite Haltepunkt: die Kinematik sagt bereits `dof`,
Mechanismen und Doppelgelenk-Situationen. Bei `dof > 0` ist die
FEM-Rechnung sinnlos (steht so in der README unter *Current
Limitations*) — das muss der Agent erfahren, bevor er rechnet, nicht als
Traceback danach.

---

## 5. Kompaktes Agenten-Schema

Das aktuelle Payload-Format ist fuer die UI gemacht: camelCase, UUIDs,
`E`/`A`/`I` an jedem Stab, verschachtelte `releases.start.mz`. Ein Modell,
das das von Hand schreibt, macht Fehler — systematisch bei den UUIDs und
den verschachtelten Releases.

Deshalb ein zweites, kompaktes Eingabeformat mit sprechenden IDs und
Defaults, das serverseitig expandiert wird:

```json
{
  "nodes": [
    {"id": "A", "x": 0,  "y": 0, "support": "festlager"},
    {"id": "B", "x": 6,  "y": 0, "support": "loslager"},
    {"id": "C", "x": 6,  "y": 4}
  ],
  "members": [
    {"start": "A", "end": "B"},
    {"start": "B", "end": "C", "hinge_start": "vollgelenk"}
  ],
  "loads": [
    {"on": "A-B", "type": "distributed", "q": -10},
    {"on": "C", "type": "point", "value": 25, "angle": -90}
  ]
}
```

- IDs sind frei waehlbare Namen, keine UUIDs. Die Expansion vergibt UUIDs.
- Stab-Referenz ueber `"A-B"` statt Member-UUID.
- `E`/`A`/`I` optional mit Default, `support`/`hinge` in den Begriffen,
  die Frontend und `stanli_symbols` ohnehin schon benutzen.

Ort: `backend/src/plugins/agent/schema.py`, mit `expand()` und `compact()`.
`compact()` braucht man fuer den Rueckweg — damit der Agent ein bestehendes
System lesen kann, ohne 4 kB UUIDs durch den Kontext zu schieben.

---

## 6. Der Generator wird zum Few-Shot-Korpus

Der wichtigste Punkt dieser Neuausrichtung: **die Generator-Maschinerie
verliert ihren Zweck nicht, sie wechselt ihn.**

`generator/` erzeugt Paare aus *gerendertem Bild* und *exaktem System*.
Als YOLO-Trainingsdaten sind sie zweitrangig geworden — als Beispiele fuer
den Agenten sind sie genau das Richtige:

- **Few-Shot-Material.** Drei bis fuenf Paare (Bild + kompaktes JSON),
  ueber `list_templates` bzw. als MCP-Resource abrufbar. Ein Agent, der
  einmal gesehen hat, wie ein Zweifeldtraeger mit Vollgelenk in diesem
  Schema aussieht, macht deutlich weniger Fehler als einer, der es aus
  der Schema-Beschreibung ableitet.
- **Symbol-Legende.** Ein aus `stanli_symbols` gerendertes Blatt mit
  allen Lager-, Gelenk- und Lastsymbolen und ihren Namen. Das ist genau
  das Vokabular, das der Agent im Eingangsbild wiedererkennen soll.
- Die `content/system_templates/*.json` (doppelhaus, einfeld-trager,
  double-hinge, dynamic-system) sind bereits fertige Kandidaten.

**Und als Messlatte.** Weil der Generator Bild *und* Wahrheit liefert,
kannst du beantworten, ob der Agent gut genug ist, statt es zu schaetzen:
50 Systeme generieren, rendern, den Agenten rekonstruieren lassen, Graphen
vergleichen (Knotenzahl, Topologie, Lagertypen, Lastsummen). Das ist eine
Handvoll Zeilen ueber bestehende Bausteine — und es sagt dir, ob YOLO
jemals zurueckkommen muss. Ich wuerde das *frueh* machen, nicht spaet:
das Ergebnis entscheidet ueber Etappe 3.

---

## 7. Tool-Oberflaeche

Klein halten. Sechs Tools:

| Tool | Ruft auf | Zweck |
|---|---|---|
| `statik_build_system(system, name?)` | `POST /api/agent/systems` | kompaktes System anlegen, gibt `slug` + URL |
| `statik_render(slug)` | `GET /api/agent/systems/<slug>/render` | **PNG als Bildinhalt** zur Sichtkontrolle |
| `statik_validate(slug)` | `POST /api/analyze/kinematics` | DOF, Mechanismen, Warnungen |
| `statik_analyze(slug, kind)` | `/api/analyze/{simplify,solution,dynamics}` | die eigentliche Rechnung |
| `statik_get_system(slug)` / `statik_update_system(slug, patch)` | `GET`/`PATCH /api/agent/systems/<slug>` | lesen, korrigieren ohne Neuschicken |
| `statik_list_templates()` | `GET /api/agent/templates` | Beispiele + Legende (Abschnitt 6) |

Nicht als Tool: Training, Datensatz-Generierung, Labeling. Das ist deine
Werkbank, nicht die des Agenten, und es sind teure Operationen mit
globalem Lock.

**Die Docstrings sind hier die eigentliche Arbeit** — das ist der Prompt,
den das Modell liest. Hinein gehoert:

- Koordinatensystem: mathematisch, y nach oben, `-90` Grad ist
  Schwerkraftrichtung (steht so in der README).
- Einheiten: kN, kNm, m, s.
- Die Aufforderung, Masse aus der Bemassung zu uebernehmen und nur
  ersatzweise zu schaetzen.
- Der Hinweis, dass nach `build_system` **immer** `render` und `validate`
  kommen, bevor gerechnet wird.

---

## 8. Sichtbarkeit in der Web-UI

Damit der Agent dem Menschen etwas hinlegen kann, fehlt im Frontend eine
Route:

- `routes.ts`: `route("s/:slug", "routes/system.tsx")` neben dem `index`.
- Die Route laedt beim Mount ueber `/api/systems_management/load/<slug>`
  in den Zustand-Store und setzt `shared.mode`.
- Optional spaeter: pollen, damit man dem Agenten beim Bauen zusieht.

Damit gibt `statik_build_system` eine echte URL zurueck
(`https://statik.7solomon.duckdns.org/s/<slug>`), die du im Chat anklickst.

---

## 9. Etappen

**Etappe 1 — Fundament, ohne MCP — ERLEDIGT**

1. `backend/src/plugins/agent/schema.py`: `expand()` / `compact()`,
   22 Tests in `backend/tests/test_agent_schema.py`.
2. `backend/src/plugins/agent/render.py`: Welt -> Pixel, System -> PNG.
3. `backend/src/plugins/agent/checks.py`: Plausibilitaetswarnungen.
4. `backend/src/plugins/agent/api/agent.py`: Blueprint `/api/agent/*`,
   registriert in `src/__init__.py`.
5. Frontend-Route `/s/:slug` (`app/routes/system.tsx`).

Zwei Dinge, die beim Bauen dazukamen:

* **Alle relativen `fetch('api/...')` im Frontend sind jetzt absolut.**
  Zwoelf Aufrufe benutzten einen relativen Pfad, der auf der flachen
  Route zufaellig funktionierte. Unter `/s/<slug>` waere daraus
  `/s/api/...` geworden — Speichern, Laden und jede Analyse haetten dort
  ins Leere gegriffen. Der Rest des Codes benutzte ohnehin schon `/api/`.
* **`AnnotationRenderer` wird bewusst NICHT wiederverwendet.** Er ist fuer
  Trainingsdaten gebaut und deshalb absichtlich zufaellig: er laesst 45%
  der Knotennamen weg, ersetzt Lastwerte in einem Drittel der Faelle durch
  "F1", und zeichnet eine Bemassung, deren Laenge aus einem
  Zufallsmassstab erfunden ist. Fuer eine Sichtkontrolle waere das aktiv
  irrefuehrend. `render.py` beschriftet stattdessen deterministisch —
  Knotennamen, Lastwerte, und einen Massstabsbalken, der aus der
  tatsaechlichen Projektion berechnet ist.

Der Ablauf laeuft durch: System anlegen, rendern, validieren, rechnen.
Gegengeprueft an einem Zweifeldtraeger (M = qL^2/8 und PL/4, Summe der
Auflagerkraefte) und einem Rahmen.

**API-Oberflaeche (Stand jetzt)**

| Route | Zweck |
|---|---|
| `GET /api/agent/schema` | Vokabular, Konventionen, Beispiel |
| `GET /api/agent/templates` | gespeicherte Systeme kompakt, als Few-Shot-Material |
| `GET/POST /api/agent/systems` | auflisten / anlegen (gibt `slug` + URL + Warnungen) |
| `GET/PATCH /api/agent/systems/<slug>` | lesen / abschnittsweise ersetzen |
| `GET /api/agent/systems/<slug>/render` | PNG (`?width=`, `?labels=0`) |
| `POST /api/agent/render` | PNG ohne zu speichern |
| `GET /api/agent/systems/<slug>/validate` | DOF, `ready_for_analysis`, Warnungen |
| `GET /api/agent/systems/<slug>/analyze/<kind>` | simplify / solution / dynamics, `?full=1` fuer Rohdaten |

**Etappe 2 — MCP-Server — ERLEDIGT**

`mcp/` im Repo-Root: `pyproject.toml`, `statik_mcp/server.py`, `README.md`.
stdio-Transport, `STATIK_URL` und `STATIK_TOKEN` als env. Neun Tools und
zwei Resources; `statik_render` liefert echten Bildinhalt. Keine Statik-Logik
im Server — jedes Tool ist ein Aufruf gegen `/api/agent/*`.

Zwei Dinge, die man wissen muss, bevor man daran weiterbaut:

* **Das SDK ist bei 2.x, und dort heisst `FastMCP` jetzt `MCPServer`.**
  `from mcp.server.fastmcp import FastMCP` importiert nicht mehr — das Paket
  wirft dazu eine eigene Fehlermeldung mit Migrationslink. Alles, was man
  aus aelteren Beispielen abschreibt, ist an dieser Stelle falsch.
* **Fehler muessen als `ToolError` geworfen werden.** Jede andere Exception
  bekommt ihre Meldung durch eine generische ersetzt, bevor sie das Modell
  erreicht. Genau die Meldungen aus `schema.py`, die dem Agenten sagen,
  *was* er stattdessen schreiben soll ("end 'Z' is not a node id. Known
  nodes: A"), waeren damit unsichtbar gewesen.

Dabei fiel noch eine Luecke auf: **`rotation` am Knoten war nirgends
dokumentiert.** Sie dreht die Achsen des Auflagers mit — `fixN` wirkt dann
entlang der gedrehten lokalen x-Achse — und ist damit nicht Kosmetik,
sondern ein schiefes Auflager. Nebenbei ist sie das, was einen Kragarm
richtig aussehen laesst: ohne sie liegt die Einspannung flach am Boden, mit
`"rotation": 90` steht sie als senkrechte Wand da, wie im Lehrbuch. Steht
jetzt in `/api/agent/schema` und im Docstring von `statik_build_system`.

Gegengeprueft mit einem echten MCP-Client ueber stdio: Tool-Liste,
Resources, Bildrueckgabe (`content types: ['text', 'image']`), beide
Fehlerpfade, und ein Kragarm mit M = 15 kN * 4 m = 60 kNm.

**Etappe 2b — Messen — ERLEDIGT (und das Ergebnis aendert Etappe 3)**

Gebaut:

* `backend/src/plugins/agent/compare.py` — vergleicht zwei Systeme. Namen,
  Massstab und Ursprung duerfen abweichen (ein gerendertes Blatt traegt keine
  Bemassung), Lastgroessen ebenfalls (die stehen nicht im Bild). Eine
  Spiegelung wird *nicht* verziehen. Knoten werden ueber ein optimales
  Matching der normierten Positionen gepaart.
* `backend/src/plugins/agent/evalset.py` — generiertes System -> kompakte
  Wahrheit, mit y nach oben.
* `backend/scripts/make_eval_set.py`, `backend/scripts/score_eval.py`
* 20 Tests in `backend/tests/test_agent_compare.py`. Selbsttest der Kette:
  Wahrheit gegen sich selbst = 100 % in allen Metriken.

**Das Messergebnis** (8 Systeme, Seed 7, von einem multimodalen Modell
ohne Kenntnis der Wahrheit rekonstruiert):

| Metrik | Wert |
|---|---|
| Topologie exakt | **6 von 8** |
| Knoten-F1 | 0,78 |
| Stab-F1 | 0,75 |
| Lagertypen | 0,71 |
| Gelenke | 0,67 |
| Lasten-F1 | 0,64 |
| mittlerer Positionsfehler | 0,016 (Anteil der Diagonale) |
| komplett korrekt | 0 von 8 |

Ein Fachwerk mit 12 Knoten und 21 Staeben kam topologisch fehlerfrei
zurueck. Die Geometrie ist also nicht das Problem — 0,016 Positionsfehler
heisst, dass getroffene Knoten sehr genau getroffen werden.

**Warum "komplett korrekt" trotzdem 0 ist — und was daran nicht am Leser
liegt:**

1. **Festlager und Loslager unterscheiden sich um 4 Pixel.** Das steht so im
   Code (`stanli_symbols.py`, Kommentar in `StanliSupport._ops`): "Festlager
   sits directly on the ground; Loslager rolls, so its ground line is offset
   by supportGap. That gap is the only discriminator between the two."
   `supportGap = 1.0` mm bei `PX_PER_MM = 4.0` — also 20 px gegen 24 px in
   einem 900x660-Bild. Das ist weder fuer einen Agenten noch fuer YOLO noch
   fuer einen Menschen lesbar. **Das trifft das YOLO-Training genauso:** der
   Datensatz verlangt dort zwei Klassen zu trennen, die sich um vier Pixel
   unterscheiden.
2. **Gleitlager wird als zwei Rollen gezeichnet.** In der ueblichen deutschen
   Konvention lesen sich Rollen als Loslager — daher kommt die Haelfte der
   Lagerverwechslungen. Entweder das Symbol anpassen oder dem Agenten das
   Vokabular explizit mitgeben (die Legende aus Abschnitt 6).
3. **Knoten werden nicht gezeichnet.** Ein Knoten mitten in einem geraden
   Stabzug, ohne Lager, Gelenk oder Last, hinterlaesst keine Spur im Bild —
   das Bild ist pixelgleich, ob er da ist oder nicht. `unobservable_nodes()`
   misst das jetzt mit: im Probelauf war genau **ein** Knoten prinzipiell
   unsichtbar, 7 von 8 Systemen waren vollstaendig rekonstruierbar. Die
   Obergrenze lag also bei 7/8, nicht bei 8/8.

**Was wirklich Lesefehler war:** bei zwei Systemen wurden Knoten an den
Raendern von Streckenlasten erfunden. Streckenlasten decken im Generator oft
nur einen Teil eines Stabes ab (`from`/`to`), und ohne gezeichnete Knoten ist
die Annahme "Lastrand = Knoten" naheliegend und falsch. Das gehoert in den
Docstring von `statik_build_system`.

**Folgerung fuer Etappe 3:** Die Zahlen sagen *noch nicht*, dass YOLO
gebraucht wird. Sie sagen zuerst, dass der Datensatz repariert gehoert —
solange zwei Lagerklassen vier Pixel auseinanderliegen, misst man die
Rendering-Schwaeche und nicht den Leser. Reihenfolge: Symbole trennbar
machen, Bemassung optional einzeichnen, dann neu messen. Erst danach ist die
Frage nach YOLO beantwortbar.

**Etappe 3 — zuerst den Datensatz reparieren, dann neu messen**

Vor allem anderen, weil es Agent *und* Detektor gleichermassen betrifft:

- `supportGap` so vergroessern, dass Festlager und Loslager sichtbar
  verschieden sind, oder das Loslager konventionell mit Rollen zeichnen und
  das Gleitlager anders.
- Knotenpunkte markieren oder eine echte Bemassung einzeichnen (die
  vorhandene in `AnnotationRenderer` ist erfunden — siehe Etappe 1).
- Danach `make_eval_set.py` + `score_eval.py` erneut laufen lassen, mit
  mehr als acht Systemen und ueber die MCP-Tools statt von Hand.

Erst wenn die Zahlen dann immer noch nicht tragen:

- YOLO als *optionale Praezisionshilfe* zurueckholen: `/api/vision/predict`
  als zusaetzliches Tool, das der Agent bei unbemassten oder
  fotografierten Vorlagen dazuziehen kann. Der Code dafuer
  (`YoloPredictor`) liegt fertig da, es fehlt nur der Blueprint — die
  Option kostet also nichts, solange man sie nicht zieht.
- MCP ueber Streamable HTTP als eigener Container im `edge`-Netz, damit
  auch nicht-lokale Clients drankommen. Dann zwingend mit Token.
- Live-Update der Seite waehrend der Agent baut.

---

## 10. Offene Punkte

**Auth.** Das Backend haengt laut `docker-compose.yml` oeffentlich unter
`statik.7solomon.duckdns.org`. Bisher ist alles harmlos. Sobald
`/api/agent/*` schreibt, gehoert mindestens ein statischer Token in einen
`before_request` des Agent-Blueprints. Weil kein Bild und kein
ML-Modell mehr im Spiel ist, bleibt die Angriffsflaeche aber klein —
Schreiben in `SystemManager`, sonst nichts.

**Ungenaue Koordinaten.** `checks.py` faengt inzwischen die drei Fehler
ab, die beim Ablesen einer Zeichnung tatsaechlich passieren: zwei Knoten
uebereinander (ein Gelenk doppelt gesehen), ein Knoten ohne Stab, ein
System ganz ohne Lager. Was noch fehlt, ist der Fluchtungshinweis
("A und C unterscheiden sich um 0,02 m in y — soll das fluchten?").
Erst bauen, wenn es in der Praxis stoert.

**Schnittgroessen zurueck an den Agenten.** `/api/analyze/solution`
liefert vollstaendige Verlaeufe — schnell tausende Zahlen. Der Agent
braucht eine Zusammenfassung (Max/Min je Stab, Auflagerkraefte), Rohdaten
nur auf Anfrage. Sonst ist der Kontext nach einer Rechnung voll.
