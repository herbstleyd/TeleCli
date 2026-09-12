# Telecli

Terminal-basierter Telegram-Client für Linux (aarch64/Debian und alle anderen Architekturen).

Layout der originalen Telegram-App: Chatliste links, Nachrichten rechts, Eingabe unten. Navigation mit Pfeiltasten. Farben für farbige Konsolen.

## Voraussetzungen

- Python 3.10 oder neuer
- Ein Terminal mit Farbunterstützung (empfohlen: 256-Farben)
- Telegram-API-Zugangsdaten (api_id und api_hash)

## Installation

### 1. Python-Abhängigkeiten installieren

```bash
cd telecli
pip install -r requirements.txt
```

### 2. Telegram-API-Daten einrichten

Du benötigst eine `api_id` und einen `api_hash` von Telegram:

1. Gehe zu https://my.telegram.org
2. Melde dich mit deiner Telefonnummer an
3. Klicke auf **API development tools**
4. Erstelle eine neue App (Name und Kurzname beliebig)
5. Kopiere `api_id` und `api_hash`

Trage sie als Umgebungsvariablen ein:

```bash
export TG_API_ID='deine_api_id'
export TG_API_HASH='dein_api_hash'
```

Für dauerhafte Speicherung in `~/.bashrc` oder `~/.zshrc`:

```bash
echo 'export TG_API_ID="deine_api_id"' >> ~/.bashrc
echo 'export TG_API_HASH="dein_api_hash"' >> ~/.bashrc
source ~/.bashrc
```

### 3. Erster Start (Login)

```bash
python3 telecli.py
```

Beim ersten Start wirst du nach deiner Telefonnummer und dem Bestätigungscode gefragt. Optional auch nach dem Zwei-Faktor-Passwort. Danach wird eine Session-Datei unter `~/.config/telecli/session.session` gespeichert.

## Bedienung

### Tasten

| Taste | Funktion |
|---|---|
| Pfeil hoch/runter | In Chatliste navigieren |
| Enter | Chat öffnen / Nachricht senden |
| Strg+R | Chatliste und Nachrichten aktualisieren |
| Strg+L | Fokus auf Chatliste |
| Strg+I | Fokus auf Eingabefeld |
| Strg+U | Upload-Befehl vorbereiten |
| Strg+D | Letztes Medium herunterladen |
| Strg+C | Beenden |

### Befehle (im Eingabefeld)

| Befehl | Funktion |
|---|---|
| `/upload <pfad> [caption]` | Datei/Bild in den aktuellen Chat senden |
| `/download [nr]` | Medium herunterladen (Nr. aus Nachrichtenliste) |
| `/media` | Alle Medien im aktuellen Chat auflisten |
| `/refresh` | Chatliste und Nachrichten aktualisieren |
| `/help` | Hilfe anzeigen |
| `/quit` | Beenden |

### Medien-Upload

```
/upload ~/Bilder/urlaub.jpg Schöner Sonnenuntergang!
```

- Dateien mit Leerzeichen im Pfad müssen in Anführungszeichen gesetzt werden: `/upload "~/Meine Dateien/dokument.pdf"`
- Bilder werden als Foto gesendet, alle anderen Dateien als Dokument
- Der Fortschritt wird in der Statusleiste angezeigt

### Medien-Download

Nachrichten mit Medien werden mit einer Nummer markiert:

```
▸ Jens (14:30)
  [3] 🖼️ photo.jpg (2.4 MB) — /download 3
```

Herunterladen:

```
/download 3          # Bestimmtes Medium
/download            # Letztes Medium im Chat
/media               # Alle Medien auflisten
```

Heruntergeladene Dateien werden gespeichert unter:

- Standard: `~/Downloads/telecli/`
- Eigener Ordner: `export TG_DOWNLOAD_DIR='/pfad/zum/ordner'`

## Layout

```
┌─────────────────┬──────────────────────────────┐
│     Chats       │        Nachrichten           │
│                 │                              │
│ ▸ Max Mustermann│ ◂ Anna  (14:30)              │
│   Hallo!  14:30 │   Hey, wie geht's?           │
│                 │                              │
│ ◂ Anna Schmidt  │ ◂ Anna  (14:31)              │
│   🖼️ 14:25     │   [1] 🖼️ foto.jpg (1.2 MB)  │
│                 │     — /download 1            │
├─────────────────┴──────────────────────────────┤
│ Nachricht senden (/help für Hilfe)             │
├────────────────────────────────────────────────┤
│ Eingeloggt als: Jens | Chat: Anna | Upload: 42%│
└────────────────────────────────────────────────┘
```

## Funktionen

### Textnachrichten
- [x] Login mit Telefonnummer + Bestätigungscode
- [x] Zwei-Faktor-Authentifizierung (Passwort)
- [x] Chatliste mit Vorschau und Zeitstempel
- [x] Nachrichtenverlauf anzeigen
- [x] Textnachrichten senden
- [x] Eingehende Nachrichten (Live-Update)
- [x] Farbiges Layout für farbige Konsolen
- [x] Session-Speicherung (kein wiederholter Login)

### Medien
- [x] Dateien und Bilder hochladen (`/upload`)
- [x] Medien herunterladen (`/download`)
- [x] Medienliste anzeigen (`/media`)
- [x] Fortschrittsanzeige für Upload/Download (Statusleiste)
- [x] Medientyp-Erkennung (Foto, Video, Sticker, Sprachnachricht, Dokument)
- [x] Konfigurierbarer Download-Ordner (`TG_DOWNLOAD_DIR`)
- [x] Datei- und Größenanzeige in Nachrichten

## Konfiguration

| Umgebungsvariable | Standard | Beschreibung |
|---|---|---|
| `TG_API_ID` | — | Telegram API-ID (Pflicht) |
| `TG_API_HASH` | — | Telegram API-Hash (Pflicht) |
| `TG_DOWNLOAD_DIR` | `~/Downloads/telecli/` | Ordner für heruntergeladene Medien |

## Systemweite Installation (optional)

```bash
chmod +x telecli.py
sudo cp telecli.py /usr/local/bin/telecli
```

Danach kannst du `telecli` von überall starten.

## Fehlerbehebung

**"TG_API_ID und TG_API_HASH sind nicht gesetzt"**
→ Siehe Schritt 2 der Installation.

**Login schlägt fehl**
→ Stelle sicher, dass die Telefonnummer mit Ländervorwahl angegeben wird (z.B. `+491701234567`).

**Farben werden nicht angezeigt**
→ Verwende einen Terminal-Emulator mit 256-Farben-Unterstützung (z.B. `gnome-terminal`, `konsole`, `kitty`, `alacritty`). Setze `export TERM=xterm-256color`.

**Upload schlägt fehl**
→ Prüfe, ob die Datei existiert und lesbar ist. Bei großen Dateien kann der Upload länger dauern — der Fortschritt wird in der Statusleiste angezeigt.

**Download nicht gefunden**
→ Die Datei wird unter `~/Downloads/telecli/` gespeichert (oder im konfigurierten `TG_DOWNLOAD_DIR`).

**Session abgelaufen**
→ Lösche die Session-Datei und melde dich neu an:
```bash
rm ~/.config/telecli/session.session
```

## Lizenz

Frei zur Verwendung.

# Telecli — Anleitung: Installation mit Python venv

Diese Anleitung zeigt, wie du Telecli in einer virtuellen Python-Umgebung (venv) einrichtest und startest. So bleiben die Abhängigkeiten sauber vom restlichen System getrennt.

## 1. Archiv entpacken

```bash
tar xzf telecli.tar.gz -C ~/telecli
cd ~/telecli
```

## 2. Virtuelle Umgebung erstellen

```bash
python3 -m venv .venv
```

Das erstellt einen Ordner `.venv/` mit einer isolierten Python-Installation.

## 3. Virtuelle Umgebung aktivieren

```bash
source .venv/bin/activate
```

Du erkennst die Aktivierung am Prompt — er beginnt dann mit `(.venv)`.

## 4. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

## 5. API-Daten einrichten

Du benötigst `api_id` und `api_hash` von https://my.telegram.org:

1. Gehe zu https://my.telegram.org
2. Melde dich mit deiner Telefonnummer an
3. Klicke auf **API development tools**
4. Erstelle eine neue App (Name beliebig)
5. Kopiere `api_id` und `api_hash`

### Option A: Umgebungsvariablen (empfohlen)

```bash
export TG_API_ID='deine_api_id'
export TG_API_HASH='dein_api_hash'
```

Dauerhaft in `~/.bashrc`:

```bash
echo 'export TG_API_ID="deine_api_id"' >> ~/.bashrc
echo 'export TG_API_HASH="dein_api_hash"' >> ~/.bashrc
source ~/.bashrc
```

### Option B: .env-Datei

```bash
mkdir -p ~/.config/telecli
cp .env.example ~/.config/telecli/.env
nano ~/.config/telecli/.env
```

Trage dort deine API-Daten ein. Verwende dann `start.sh` zum Starten (lädt die .env automatisch).

## 6. Erster Start (Login)

```bash
python3 telecli.py
```

Beim ersten Mal wirst du im Terminal nach Folgendem gefragt:

1. **Telefonnummer** — mit Ländervorwahl, z.B. `+491701234567`
2. **Bestätigungscode** — kommt per Telegram auf ein anderes Gerät
3. **Zwei-Faktor-Passwort** — nur falls du 2FA aktiviert hast

Danach wird die Session gespeichert unter `~/.config/telecli/session.session`. Bei weiteren Starts entfällt der Login.

## 7. Telecli starten (ab dem zweiten Mal)

Jedes Mal, wenn du Telecli nutzen möchtest:

```bash
cd ~/telecli
source .venv/bin/activate
python3 telecli.py
```

Oder mit dem Startskript (aktiviert venv automatisch + lädt .env):

```bash
cd ~/telecli
./start.sh
```

Dafür muss `start.sh` angepasst sein (siehe unten).

## 8. venv wieder verlassen

Wenn du fertig bist:

```bash
deactivate
```

Der Prompt ändert sich zurück — die virtuelle Umgebung ist deaktiviert.

---

## start.sh anpassen (optional)

Damit `start.sh` die venv automatisch aktiviert, ersetze den Inhalt mit:

```bash
#!/bin/bash
# Startskript für Telecli mit venv
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$HOME/.config/telecli/.env"

# .env laden falls vorhanden
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

# venv aktivieren und App starten
source "$SCRIPT_DIR/.venv/bin/activate"
python3 "$SCRIPT_DIR/telecli.py"
```

Speichern und ausführbar machen:

```bash
chmod +x start.sh
```

Dann reicht ein einfaches:

```bash
./start.sh
```

---

## Shortcut: Alias anlegen

Damit du nicht jedes Mal `cd` und `source` tippen musst:

```bash
echo 'alias telecli="cd ~/telecli && source .venv/bin/activate && python3 telecli.py"' >> ~/.bashrc
source ~/.bashrc
```

Danach startest du Telecli einfach mit:

```bash
telecli
```

---

## Übersicht: Wichtige Pfade

| Pfad | Beschreibung |
|---|---|
| `~/telecli/.venv/` | Virtuelle Python-Umgebung |
| `~/.config/telecli/` | Konfigurationsordner |
| `~/.config/telecli/session.session` | Gespeicherte Telegram-Session |
| `~/.config/telecli/.env` | API-Daten (optional) |
| `~/Downloads/telecli/` | Heruntergeladene Medien |

## Aktualisierung

Wenn es eine neue Version von Telecli gibt:

```bash
cd ~/telecli
source .venv/bin/activate
pip install -r requirements.txt --upgrade
```

Ersetze dann `telecli.py` durch die neue Version.

## Deinstallation

```bash
# Virtuelle Umgebung entfernen
rm -rf ~/telecli/.venv

# Komplette App entfernen
rm -rf ~/telecli

# Konfiguration und Session entfernen
rm -rf ~/.config/telecli

# Heruntergeladene Medien entfernen
rm -rf ~/Downloads/telecli

# Alias entfernen (falls gesetzt)
# Entferne die Zeile mit 'alias telecli=' aus ~/.bashrc
```
