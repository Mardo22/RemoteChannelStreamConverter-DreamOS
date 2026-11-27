# Changelog

All changes since version 1.0 by **Mardo22 (SetTvBox4U)**. Licensed under GPL-3.0.
YouTube channel: [SetTvBox4U](https://www.youtube.com/@SetTvBox4U)

## 2.0.5 – 27.11.2026
- **EPG from the server is imported about 1 minute later:** after "Update all converted bouquets" the plugin no longer
  starts EPGImport at once. It waits about 1 minute and starts the import only when the receiver has finished saving
  its EPG and no other EPGImport is running (otherwise it checks again every 30 s, max. 10 times). Before, EPGImport
  could start while the receiver was still saving the EPG and reloading the bouquets – on a busy image this could
  freeze the receiver. The timer runs in the main program, also when the plugin window is closed.
- MENU "Update EPG from server" and "Start EPGImport now" also wait while the EPG is being saved.
- No import of only the server EPG when EPGImport is set to "Clearing current EPG before import" – that import would
  delete the whole EPG of the receiver and keep only the few events from the server. The plugin shows a message instead.
- Settings and converted bouquets stay as they are. With 2.0.4 the plugin offers 2.0.5 by itself (online update).
- Tested on Dreambox Two with TITANIUM 2026 AIO (27.11.2026): Update all of 8 bouquets (1481 channels), EPG from the
  server 2736 events, EPG of the receiver kept, no freeze.

## 2.0.4 – 22.11.2026
- **Online update:** when the plugin is opened it asks GitHub for the latest published version. If it is newer, a
  message shows what is new – **OK** downloads and installs it and offers a GUI restart, **EXIT** keeps your version.
  The download is checked (size and checksum) before it is installed. Nothing is installed without asking.
  Option "Check for updates when opening" (default yes) and MENU "Check for updates now".
- Fix: MENU "Start EPGImport now (all sources)" and the import of the EPG from the server did not start on images
  whose EPGImport is a different version (for example TITANIUM 2026 AIO) – the log showed
  `[RCSC] EPGImport start failed: 'module' object has no attribute 'ensure_runtime_modules'`.
  Now the import starts the same way as "Manual import" in EPGImport, with every EPGImport version.
- Settings and converted bouquets stay as they are – install 2.0.4 over 2.0.2.
- Tested on Dreambox Two with TITANIUM 2026 AIO (22.11.2026): online update, EPGImport start.

## 2.0.2 – 09.11.2026
- Short tip in the server panel ("one tuner on the server = channels of one transponder only (all in standby)") –
  the longer tip was cut off at the bottom of the panel.
- While deleting, the status line shows "Deleting N bouquets ... Updating picon links and EPG mapping - please wait."
  (before, the window did not change until the deletion was finished).
- Tested with the release package on a clean DreamOS 5.0 (Dreambox Two) with a Vu+ Ultimo 4K / OpenBH 6.0 server:
  first start, settings, convert, playback 1080p, EPG, delete, convert again.

## 2.0.1 – 05.11.2026
- "Convert" no longer loads the EPG of the server. This now happens only with "Update all" and MENU
  "Update EPG from server". Before, every conversion started an EPGImport run, which kept the GUI busy while the EPG
  database was saved and could fail when EPGImport wrote into the database at the same time.
- First start without a server IP: the settings window opens on top of the main window (only once); yellow opens
  the settings, red closes the plugin.
- Yellow also works while connecting / reading – it cancels the loading and opens the settings (a wrong IP can no
  longer block the plugin). Connecting gives up after 25 s ("Could not connect … check the server IP").
- Singular texts for one bouquet ("Really delete 1 converted bouquet?", "Deleted 1 bouquet.", "Done: 1 bouquet, …").

## 2.0 – 05.11.2026
- EPG for the stream channels without changing their references or channel numbers:
  - "EPG of the Dreambox for the channels (EPGImport)" (default yes): the plugin writes its own block into
    `/etc/epgimport/custom.channels.xml` – the XMLTV ids of the enabled EPGImport sources are assigned to the stream
    channels. No dependence on the server.
  - "EPG from server (only on demand)" (default yes): MENU "Update EPG from server" (and "Update all") takes the EPG of
    the server (OpenWebif `/api/epgmulti`) for channels without EPG on the Dreambox and imports it at once with
    EPGImport (source "RCSC - EPG from server"). Nothing runs automatically.
  - MENU "Start EPGImport now (all sources)".
- New plugin icon. Shorter picon summary in the status line.

## 1.9 – 05.11.2026
- "Import missing picons from server" (option, default yes): channels without a picon get the picon of the server
  (OpenWebif); the files are listed in `/etc/enigma2/rcsc_picon_files` and removed with their bouquets.
  Existing picons are never replaced.
- Optional entries in the plugin browser (with icon), the extensions menu and the main menu (default off, active
  after a GUI restart). The plugin is always in MENU → Setup → Services and Recordings → Service Searching.

## 1.8 – 05.11.2026
- Picon links: after every conversion, "Update all" and delete, the plugin links the stream channels to the existing
  picons of the channels (symlinks in the picon directory), so the channels of the server have logos.
- Options "Create picon links for the channels" (default yes) and "Picon directory" (auto = picon directory of the
  skin / picon plugins, or /data/picon, /usr/share/enigma2/picon, /media/hdd/picon, …).
- Own picon files are never changed; only links created by the plugin (`/etc/enigma2/rcsc_picon_links`) are removed.
- MENU "Update picon links of the channels".

## 1.7 – 23.10.2026
- Bouquet counter: every local bouquet is counted for one server bouquet only (same names like "Others").
- No crash by late callbacks after the window was closed.

## 1.6 – 22.10.2026
- StreamRelay: channels in the server's `whitelist_streamrelay` (OE-Alliance) are streamed on port 17999 (decrypted by the
  server); options "Use StreamRelay of the server" and "StreamRelay port" in the settings.
- Public release under GPL-3.0 (license headers, LICENSE file).

## 1.5 – 22.10.2026
- One package for DreamOS 4.5 and 5.0 – the system is detected from the version of the installed enigma2 package
  (shown in the title and in About).

## 1.4 – 22.10.2026
- QR code of the YouTube channel SetTvBox4U in the bottom bar and in a new About window.

## 1.3 – 22.10.2026
- IPTV channels of the server are copied with their internet links (option); `127.0.0.1` / `localhost` → server address.
- "converted" moved closer to the satellites column; YouTube channel in About.

## 1.2 – 22.10.2026
- List drawn via a template: converted bouquets in green, divider between channels and satellites.
- Yellow summary and key hint; About with "Updated by Mardo22 since 21.10.2026" and version + date.

## 1.1 – 21.10.2026
- New Full HD user interface in the style of the DreamOS skin, menu entry in Service Searching.
- Download via OpenWebif without password (or FTP with password).
- Channel count and satellites per bouquet, server status (standby, current channel, busy tuners).
- Update all / delete converted bouquets; a bouquet with the same name is replaced, other bouquets stay.
- `lamedb` merge without duplicates, optional backup, English / Slovak / Czech.

## 1.0 – 2019
- DreamOS port of the OpenPLi plugin "Remote channel stream converter" (FTP only) – original, not by Mardo22.
