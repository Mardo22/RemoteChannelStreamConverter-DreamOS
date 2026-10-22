# Remote channel stream converter for DreamOS

**Use the tuners of another Enigma2 receiver on your Dreambox** – an Enigma2 plugin for **DreamOS 4.5 and DreamOS 5.0**
(tested on Dreambox Two). It converts the bouquets of a second receiver (the *server*, e.g. a Vu+ with OpenATV / OpenBH /
OpenPLi) into stream bouquets on the Dreambox, so the Dreambox plays the channels through the tuners of the server.

DreamOS has no "Fallback tuner" function like OpenPLi / OE-Alliance images – this plugin is the DreamOS way to do it.

YouTube channel: **[SetTvBox4U](https://www.youtube.com/@SetTvBox4U)**

| Main window | About |
|---|---|
| ![Main window](docs/images/05-main-window.jpg) | ![About](docs/images/10-about.jpg) |

## Features
- One package for **DreamOS 4.5 and 5.0** – the system is detected automatically.
- Download from the server via **OpenWebif (no password)** or **FTP (with password)**.
- Full HD window: list of the server's bouquets with number of channels and satellites, converted bouquets shown in green.
- Server status: model, image, standby / current channel, busy tuners.
- **Convert**, **update all converted** and **delete** converted bouquets; a bouquet with the same name is replaced,
  other bouquets stay.
- **IPTV channels** of the server are copied with their original internet links (option); links to a proxy on the
  server itself (`127.0.0.1`) are rewritten to the server address.
- **StreamRelay** (OE-Alliance images): channels in the server's `whitelist_streamrelay` are streamed on port 17999 –
  the server decrypts them (option).
- Server services merged into the local `lamedb` without duplicates (option), optional backup of `/etc/enigma2`.
- Languages: English, Slovak, Czech.

## Requirements
- Dreambox with **DreamOS 4.5 or 5.0** (Python 2.7) – tested on **Dreambox Two**.
- Server: an Enigma2 receiver in the same network with **OpenWebif** (port 80) or FTP, streaming on port **8001**.
- The Dreambox can only play what the server can tune: if the server has only one tuner configured, the Dreambox plays
  only channels of the transponder the server is on (or all channels while the server is in standby).

## Installation
1. Download `enigma2-plugins-remotechannelconverter-dreamos_1.6_all.deb` from [Releases](../../releases)
   (or from the `release/` folder).
2. Copy it to `/tmp` of the Dreambox (FTP / USB).
3. Install: **MENU → Setup → Software management → Install local extension** → `/tmp` → **green**,
   or via telnet/SSH: `dpkg -i /tmp/enigma2-plugins-remotechannelconverter-dreamos_1.6_all.deb`
4. Restart the GUI.

## Usage
**Full step-by-step guide with screenshots: [docs/GUIDE.md](docs/GUIDE.md)**

1. **MENU → Setup → Services and Recordings → Service Searching → Remote channel stream converter**
2. **Yellow (Settings)**: connection (OpenWebif / FTP), IP address of the server, options. Green = save.
3. Select bouquets with **OK**, then **green (Convert)**.
4. **MENU** in the plugin: update all converted bouquets, delete converted bouquets, reload, settings, About.

The converted bouquets are named `… (remote of <server IP>)` and appear in the normal channel list.

## Build the package yourself
```sh
./build.sh          # on a Linux / Enigma2 box with dpkg-deb
```

## Credits
- Original plugin **"Remote channel stream converter"** for Enigma2 – OpenPLi, E2OpenPlugins
  ([e2openplugin-RemoteChannelStreamConverter](https://github.com/E2OpenPlugins/e2openplugin-RemoteChannelStreamConverter)),
  OE-Alliance ([RemoteChannelStreamConverter](https://github.com/oe-alliance-plugins/RemoteChannelStreamConverter), GPL-3.0).
- DreamOS port 1.0 (2019) – unknown author.
- Versions 1.1 – 1.6 for DreamOS 4.5 / 5.0 (new user interface, OpenWebif, IPTV, StreamRelay, …):
  **Mardo22 (SetTvBox4U)**, 2026 – see [CHANGELOG.md](CHANGELOG.md).

## License
**GNU General Public License v3.0** – see [LICENSE](LICENSE). You may use, share and modify this plugin; modified versions
must also be released under GPL-3.0 with their source code.

## Disclaimer
This plugin only converts the channel lists of your own receivers in your own network. It contains no channel lists,
no IPTV links and no keys. Use it only with services you are entitled to receive. No warranty.

---

### Slovensky (krátko)
Plugin pre **DreamOS 4.5 a 5.0**, ktorý z buketov druhého prijímača (servera, napr. Vu+) vytvorí na Dreamboxe stream bukety –
Dreambox potom používa tunery servera (náhrada funkcie „Fallback“, ktorá v DreamOS nie je). Inštalácia: súbor `.deb` do `/tmp`,
**MENU → Setup → Software management → Install local extension**. Plugin: **MENU → Setup → Services and Recordings →
Service Searching → Remote channel stream converter**. Licencia GPL-3.0.
