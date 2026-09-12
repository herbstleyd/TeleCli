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
