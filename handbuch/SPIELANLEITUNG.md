# Spielanleitung

## Ziel und Punkte

Der Held läuft automatisch. Vermeide Bodenhindernisse durch Sprünge oder Schüsse.
Flieger befinden sich über dem Boden. Jeder zerstörte Gegner gibt 25 Punkte;
zusätzlich zählt ein Punkt pro drei zurückgelegte interne Streckeneinheiten.
Die im Bildschirm angezeigten Meter entsprechen vier internen Einheiten.
Der letzte Treffer einer Runde zählt bereits im selben Spieltakt.

Ein Treffer am Helden beendet die Runde, außer Unverwundbarkeit ist aktiv.
Danach zeigt das Spiel Punkte, Kills und die persönliche Bestenliste.
Enter/Leertaste führt zurück zum Startmenü; Q beendet.

## Starten und fortsetzen

Mit `python piuu.py` oder `python -m piu` starten. Windows-Nutzer können
`PIUU.bat` verwenden. Das Spiel benötigt Python 3.10+, aber keine Bibliotheken.

Das Startmenü ist ein animiertes ASCII-Arcade-Plakat. Bei kleinen Fenstern
wechselt es auf ein kompaktes Layout. Ein vorhandener Rundenstand wird durch
**FORTSETZEN** sichtbar. Die gespeicherten Rundeneinstellungen bleiben dabei
erhalten, auch wenn du inzwischen im Menü andere Werte gewählt hast.

**NEUE RUNDE** ersetzt einen vorhandenen Stand erst nach der Bestätigung
„JA, NEUE RUNDE“. Standardmäßig ist dort die sichere Option „ZURÜCK“ ausgewählt.

## Tastatur

| Bereich | Tasten | Wirkung |
|---|---|---|
| Menü | W/S oder ↑/↓ | Auswahl verschieben; am Ende zum Anfang wechseln |
| Settings | A/D oder ←/→ | Wert ändern |
| Menü | Enter oder Leertaste | Bestätigen; Settings-Wert weiterschalten |
| Menü | Escape | Zum Startmenü zurück |
| Überall | Q oder Strg+C | Beenden; laufende Runde vorher sichern |
| Spiel | Leertaste, W oder ↑ | Springen, einmaliger Doppelsprung |
| Spiel | S oder ↓ | Duckpose am Boden, schneller fallen in der Luft |
| Spiel | Enter | Schießen, solange Munition vorhanden ist |
| Spiel | P | Pausieren und sichern |
| Pause | P, Enter oder Escape | Fortsetzen |
| Pause | Q | Mit dem bereits gesicherten Stand beenden |

Die Figur hat eine zeilenbasierte Hitbox. Ducken am Boden ist eine Pose; es
verkürzt die bereits einzeilige Hitbox nicht zusätzlich. Unter Fliegern bleibt
man sicher, solange die Figur unter deren Zeilen liegt. In der Luft wirkt Ducken
als Schnellfall. Der Doppelsprung wird nach einer Landung zurückgesetzt.

## Schwierigkeit

| Preset | Tempo | Dichte | Magazin |
|---|---|---|---|
| leicht | x0.75 | wenig | 15 |
| normal | x1.00 | normal | 10 |
| schwer | x1.35 | viele | 8 |
| irre | x1.75 | extrem | 6 |

Ein Preset setzt diese drei Werte gemeinsam, verändert aber keine Cheat-Schalter.
Einzelwerte sind möglich: Tempo x0.50–x2.00 in 0.05-Schritten, vier Dichtestufen
und 1–30 Schuss pro Magazin. Jede Einzeländerung setzt das Label auf **eigen**,
auch wenn der Wert danach zurückgestellt wird. **Zurücksetzen** stellt normal
und alle Cheats auf aus. Änderungen werden im Menü sofort gespeichert.

Das tatsächliche Lauftempo steigt mit der Strecke und schwankt leicht. Der
eingestellte Faktor multipliziert diese Grundgeschwindigkeit. Dichte verändert
die Abstände; Hindernisarten werden mit höherem Fortschritt abwechslungsreicher.

## Munition und Cheats

Ohne Cheats füllt sich das Magazin alle 30 Sekunden Spielzeit auf. Nach dem
letzten Schuss dauert das Nachladen fünf Sekunden. Währenddessen sind keine
Schüsse möglich. Die Anzeige zeigt den verbleibenden Vorrat bzw. die Ladezeit.

| Cheat | Wirkung |
|---|---|
| Unendlich Munition | Schüsse verbrauchen nichts; kein Nachladen nötig |
| Sofort nachladen | Leeres Magazin lädt in 0,35 s statt 5 s |
| Unverwundbar | Berührte Hindernisse zerplatzen und zählen als Kills |
| Doppelte Punkte | Verdoppelt Streckenpunkte und Killpunkte |
| Mega-Sprung | Multipliziert die Anfangsgeschwindigkeit beider Sprünge mit 1,45 |

Die Simulation arbeitet mit 18 Takten pro Sekunde. Fünf Sekunden entsprechen
90 Takten; 0,35 Sekunden werden beim nächsten Takt abgeschlossen, also nach
sieben Takten (rund 0,39 s). +45 % Sprungkraft bedeutet nicht exakt +45 % Höhe:
Flughöhe und Flugzeit ergeben sich aus der Physik.

Cheats sind kombinierbar. Eine so gestartete Runde wird dauerhaft als
Cheat-Runde markiert, auch beim Speichern und Fortsetzen. Sie verändert weder
Highscore noch Laufzähler. Die Schwierigkeit, auch leicht/eigen, ist kein Cheat.

## Fenster und Zeit

Automatische Größe: mindestens 47×15 Terminalzeichen, maximal genutztes Raster
200×44. Eine Randspalte und -zeile verhindern ungewolltes Scrollen.
Wird das Fenster zu klein, pausiert die Runde automatisch. Zeit in Pause oder
bei zu kleinem Fenster wird beim Fortsetzen nicht nachgeholt.

Bei einer Größenänderung werden unsichtbare Objekte bereinigt. Ein Sprung
außerhalb des neuen Rasters wird auf den Boden gesetzt. Ein unverändert großes
Fenster ermöglicht eine exakte Fortsetzung des gespeicherten Zustands.

## Alle Optionen

| Option | Bedeutung |
|---|---|
| `--silent` | Sound aus |
| `--ascii` | Einfache ASCII-Ausgabe statt Kaomoji/Unicode |
| `--speed 0.75` | Gespeicherten Tempofaktor überschreiben; 0.5–2.0 |
| `--size 80x20` | Festes Raster; 46×14 bis 200×44 |
| `--name Alex` | Gespeicherten Spielernamen ändern; maximal 14 Zeichen |
| `--data-dir ORDNER` | Profil an einem anderen Ort lesen/schreiben |
| `--scores` | Bestenliste anzeigen und beenden |
| `--demo 400` | Ohne Tastatur und Profilzugriff simulieren, bis Tod oder Framegrenze |
| `--seed 0` | Deterministischer Zufallsstartwert nur für die Demo |
| `--diagnose` | Python, Terminal und Schreibrechte prüfen |
| `--version` | Version anzeigen |
| `--help` | Kommandozeilenhilfe anzeigen |

## Browser-Version

Die Webseite enthält eine eigene kleinere Simulation mit den vier Presets,
Doppelsprung, Schießen, Nachladen, Pause und lokaler Speicherung. Die fünf Cheats
und frei einstellbaren Einzelwerte gehören zum Python-Spiel. Browser- und
Python-Profile werden nicht miteinander synchronisiert.

Im Browser zuerst die Runde starten. Die Spieltasten wirken nur bei fokussiertem
Spielfeld; auf kleinen Bildschirmen gibt es Touch-Tasten. Wechselst du den Tab
oder das Fenster, wird pausiert. „Animationen pausieren“ stoppt die dekorativen
Animationen; ein bewusst gestartetes Spiel bleibt spielbar. Die Systemeinstellung
für reduzierte Bewegung wird berücksichtigt.
