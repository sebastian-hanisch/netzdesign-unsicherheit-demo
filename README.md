# Netzdesign unter Nachfrageunsicherheit – Streamlit-Demo

**[→ Demo live ausprobieren](https://sebastianhanisch-netzdesign-unsicherheit-demo.streamlit.app/)**

Fall-Demo auf der Themenseite **Netzwerkdesign** für die Website "Sebastian Hanisch – Operations Research und
Machine Learning": wie teuer ist ein Fixkosten-Netzwerkdesign, das nur für eine Nachfrage-Punktschätzung geplant
wurde, verglichen mit einem Design, das mehrere Nachfrage-Szenarien von Anfang an einplant (zweistufige
stochastische Optimierung, Näherung)? Dasselbe Modell wie `fixkosten-netzdesign-demo` (Werke → Verteilzentren →
Filialen, Fixkosten je Lane/Durchsatz), hier auf K=1 Gut reduziert und um Nachfrage-Unsicherheit erweitert.

## Zwei gleichberechtigte Regler

**Nachfrage-Streuung** ist der inhaltliche Aufhänger: jede Filiale zieht ihre reale Nachfrage unabhängig
gleichverteilt um ±X % der Nominalnachfrage. **Netzauslastung** ist der versteckte Hebel: bei viel
Kapazitätsreserve ist die Streuung fast irrelevant für die Designentscheidung, erst bei knapper Kapazität zählt sie.

**Anders als die vier "starr vs. reaktiv"-Fall-Demos in diesem Portfolio** (`fahrzeugflotte-demo`,
`robuste-kaiplatz-demo`, `blockzuweisung-demo`, `hofrobust-demo`): dort ist derselbe Planungshorizont, nur
unterschiedlich schnelle Reaktion auf eine eingetretene Störung. Hier ist die Entscheidung **einmalig und
vorgelagert** — welche Lanes und Verteilzentrum-Kapazitäten überhaupt gebaut werden, eingefroren vor der
Nachfragerealisierung. Der Recourse-Mechanismus (Notfallkapazität, Fehlmengenstrafe) ist bei beiden Designs
identisch verfügbar; der Unterschied liegt einzig in der Topologie.

## Ergebnis (Zahlen aus den Tests)

Jede hier genannte Zahl ist in `tests/test_claims.py` belegt: Standardnetz 3 Werke, 3 Verteilzentren, 8 Filialen,
Dichte 60 %, Seed 155 (SplitMix64, ganzzahlig, plattformstabil). Deterministisches und stochastisches Design werden
beide mit demselben Recourse-Mechanismus berechnet (Normalkosten bis Nominalkapazität, bis zu 50 % Notfallkapazität
zum 4-fachen Preis, Fehlmenge bestraft mit dem 15-Fachen der mittleren Stückkosten) und über 120 identische
Out-of-Sample-Szenarien verglichen — der einzige Unterschied ist, ob das Design für **ein** Szenario (die
Nominalnachfrage) oder **15** repräsentative Szenarien geplant wurde.

**Standardnetz** (Auslastung 80 %, ±65 % Streuung): das deterministische Design kostet im Erwartungswert **4,4 %**
mehr als das stochastische (Worst Case **9,8 %**) und deckt im Mittel seltener die volle Nachfrage (**2,2 %** gegen
**0,1 %** Fehlmenge). Die Topologie unterscheidet sich in **2 von 27** Entwurfsgruppen.

**Streuung ist nicht der ganze Hebel.** Bei ±35 % Streuung statt ±65 % verschwindet die Lücke vollständig (**0,0 %**,
identische Topologie) — sobald beide Designs den Notfall-Mechanismus gleichermaßen kennen, lohnt sich Szenario-
Planung erst bei grober Unsicherheit, nicht schon bei moderater.

**Auslastung wirkt, aber nicht glatt.** Bei 70 % statt 80 % Auslastung (weiter ±65 % Streuung) schrumpft die Lücke
auf **1,2 %**; bei 60 % Auslastung wächst sie dagegen auf **6,4 %** (Worst Case **50,0 %**) — mehr als beim
Standardnetz, obwohl die Nominal-Auslastung niedriger ist. Der Zusammenhang ist wegen der diskreten
Kapazitätsstufen des Netzes nicht monoton; ein Sweep über die Auslastung in der App zeigt das offen (Zacken statt
einer glatten Kurve).

## Was nicht funktioniert hat / Vorab-Hypothesen

**Der wichtigste Fund entstand beim Testen, nicht in der Vorab-Messreihe.** Eine erste Fassung berechnete das
"deterministische" Design mit dem unveränderten `fixkosten-netzdesign-demo`-Löser (`solve_mip`, kennt keine
Notfallkapazität), das stochastische dagegen mit dem neuen, Recourse-bewussten Master-Löser. Ein Korrektheitstest
bei **0 % Streuung** (wo beide Designs identisch sein sollten) deckte auf: das "deterministische" Design war so
**1,3 % teurer, obwohl die Nachfrage überhaupt nicht streute** — der gemessene Unterschied kam allein daher, dass
`solve_mip` die Möglichkeit von Notfallkapazität nicht kennt und deshalb mehr Kapazität baut als nötig, nicht von
Nachfrage-Unsicherheit. **Behoben:** das deterministische Design wird jetzt mit demselben Recourse-bewussten Löser
berechnet, nur mit einem einzigen Szenario (der Nominalnachfrage) statt mehrerer — dadurch isoliert die gemessene
Lücke wirklich nur den Effekt der Streuung, nicht die Tatsache, ob ein Design den Notfall-Mechanismus überhaupt
kennt. Nach dieser Korrektur ist die gemessene Lücke bei moderater Streuung (±35 %) null statt der ursprünglich
(fälschlich) gemessenen mehreren Prozent — ein echter, spürbarer Unterschied in der Schlussfolgerung, nicht nur in
der Zahl. `tests/test_evaluation.py::test_deterministic_baseline_is_recourse_aware_not_plain_solve_mip` hält diesen
Fund als Regressionstest fest.

- **"Die Lücke wächst monoton mit der Streuung" — nicht mehr geprüft in dieser Form.** Nach der Korrektur zeigt sich
  stattdessen ein Schwelleneffekt (praktisch null unter ~50 % Streuung, spürbar darüber), kein glattes Wachstum.
- **"Mehr Auslastung heißt immer mehr Nutzen von Vorausschau" — widerlegt.** 60 % Auslastung zeigt eine größere
  Lücke als 80 %; die Beziehung hängt an diskreten Kapazitätssprüngen des jeweiligen Netzes, nicht an einer
  einfachen Regel.

## Grenzen (was die Demo nicht zeigt)

Notfallkapazität/Fehlmengenstrafe als plausibel gewählte, nicht aus echten Vertragsdaten stammende Annahme; das
Master-Design mit 15 repräsentativen Szenarien ist eine Näherung an die vollständige zweistufige stochastische
Optimierung, kein Beweis des wahren Optimums; unabhängige Nachfrage je Filiale (keine korrelierten
Nachfrageschocks); eine Güterart (K=1, das Mehrgütermodell des Vorbilds ist reduziert).

## Dateien

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Oberfläche: Vergleich, Netzkarte, Auslastungsreihe, 📐-Abschnitt |
| `ndu_scenario.py`, `ndu_model.py`, `ndu_formulation.py` | Netz, Entwurfsmodell, Formulierung (Kopie aus `fixkosten-netzdesign-demo`, K=1) |
| `ndu_uncertainty.py` | Nachfrage-Szenarien, Recourse-LP, stochastisches Master-MILP |
| `ndu_evaluation.py` | Der zentrale Vergleich: deterministisch (Recourse-bewusst, 1 Szenario) gegen stochastisch (15 Szenarien) |
| `ndu_visualization.py` | Netzkarte mit Entwurfs-Status, Balken, Auslastungsreihe |
| `ndu_presets.py`, `ndu_constants.py` | Presets, Permalink, Regler-Grenzen |
| `tests/` | Szenario/Modell (`test_copies.py`, Wache gegen Drift vom Vorbild), Recourse gegen Handrechnung, Auswertung, Presets, App, `test_claims.py` (jede README-Zahl) |

Lokal starten: `pip install -r requirements.txt`, dann `streamlit run app.py`; Tests: `pip install -r requirements-dev.txt`, dann `python -m pytest tests`.
