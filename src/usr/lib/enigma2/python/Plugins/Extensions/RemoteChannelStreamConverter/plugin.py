# -*- coding: utf-8 -*-
#
# Remote channel stream converter for DreamOS - https://www.youtube.com/@SetTvBox4U
# Copyright (C) the original authors of the Enigma2 plugin "Remote channel stream converter"
#   (OpenPLi / E2OpenPlugins / OE-Alliance contributors)
# Modifications for DreamOS 4.5 / 5.0 (versions 1.1 - 1.6, since 21.10.2026):
#   Copyright (C) 2026 Mardo22 (SetTvBox4U)
#
# This program is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, version 3.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details: https://www.gnu.org/licenses/gpl-3.0.html
#
# Remote channel stream converter 1.6 for DreamOS 4.5 and 5.0 (one package, the system is detected at runtime)
# Based on the OpenPLi plugin "Remote channel stream converter" (GPL).
# 1.1: Full HD screen in the style of the DreamOS skin, menu in Service Searching (like "Tuners & Scanning"
#      on OpenPLi/OE-A), OpenWebif download without password or FTP with password, update/delete of converted
#      bouquets, bouquet with the same name is replaced (others stay), lamedb merge without duplicates,
#      optional backup, server status (standby / busy tuners), channel count and satellites per bouquet, en/sk/cs.
# 1.2 (22.10.2026): list via template - converted bouquets green, divider between channels and satellites,
#      yellow summary and key hint, About with "Updated by Mardo22 since 21.10.2026" and version + date.
# 1.3 (22.10.2026): IPTV channels of the server copied with their internet links (option), "converted" moved left,
#      About with the YouTube channel SetTvBox4U.
# 1.4 (22.10.2026): QR code of the YouTube channel SetTvBox4U in the bottom bar and in an own About screen.
# 1.5 (22.10.2026): one package for DreamOS 4.5 and 5.0 - system detected from the enigma2 package version (title, About).
# 1.6 (22.10.2026): StreamRelay - channels in the whitelist_streamrelay of the server (OE-A) are streamed on port 17999
#      (decrypted by the server), option in the settings. Public release under GPL-3.0.
from __future__ import absolute_import
import os
import re
import time
import json
import base64
import tarfile
from collections import OrderedDict
from urllib import quote
import urllib2

from enigma import eDVBDB, eServiceReference, eListboxPythonMultiContent, gFont, \
	RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaBlend
from Components.Sources.StaticText import StaticText
from Components.config import config, configfile, ConfigSubsection, ConfigText, ConfigPassword, ConfigInteger, \
	ConfigYesNo, ConfigIP, ConfigSelection, getConfigListEntry
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN
from Tools.LoadPixmap import LoadPixmap
from twisted.internet import threads

from . import _
from .FTPDownloader import FTPDownloader

VERSION = "1.6"
VERSION_DATE = "22.10.2026"
UPDATED_SINCE = "21.10.2026"
UPDATED_BY = "Mardo22"
YOUTUBE = "youtube.com/@SetTvBox4U"
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
QR_SMALL = os.path.join(PLUGIN_DIR, "qr_youtube_small.png")
QR_BIG = os.path.join(PLUGIN_DIR, "qr_youtube_big.png")


def detectDreamOS():
	"""1.5: one package for DreamOS 4.5 and 5.0 - the system is taken from the version of the installed enigma2 package
	(4.5.1r11 = DreamOS 4.5, 5.0.0r2 = DreamOS 5.0)."""
	try:
		f = open("/var/lib/dpkg/status")
		try:
			data = f.read()
		finally:
			f.close()
		for block in data.split("\n\n"):
			if block.startswith("Package: enigma2\n"):
				m = re.search(r"^Version: (\d+)\.(\d+)", block, re.M)
				if m:
					return "DreamOS %s.%s" % (m.group(1), m.group(2))
	except Exception:
		pass
	return "DreamOS"

DREAMOS = detectDreamOS()
DIR_ENIGMA2 = "/etc/enigma2/"
REMOTE_DIR = "/etc/enigma2/"
DIR_WORK = "/tmp/rcsc/"
RCSC_PREFIX = "userbouquet.rcsc."
BACKUP_DIR = "/media/hdd/rcsc-backup/"
BACKUP_KEEP = 3

FLAG_MUST_DESCENT = 2
FLAG_MARKER = 64
FLAG_GROUP = 128
try:
	FLAG_MUST_DESCENT = eServiceReference.mustDescent
	FLAG_MARKER = eServiceReference.isMarker
	FLAG_GROUP = eServiceReference.isGroup
except Exception:
	pass

# ---------------------------------------------------------------- config (keys of 1.0 kept: ip, username, password, port, passive)
config.plugins.RemoteStreamConverter = ConfigSubsection()
cfg = config.plugins.RemoteStreamConverter
cfg.language = ConfigSelection(default="auto", choices=[("auto", "auto"), ("en", "English"), ("sk", "Slovenčina"), ("cs", "Čeština")])
cfg.address = ConfigText(default="", fixed_size=False)
cfg.ip = ConfigIP(default=[0, 0, 0, 0])
cfg.mode = ConfigSelection(default="webif", choices=[("webif", "OpenWebif"), ("ftp", "FTP")])
cfg.webif_port = ConfigInteger(80, (1, 65535))
cfg.webif_user = ConfigText(default="", fixed_size=False)
cfg.webif_password = ConfigPassword(default="", fixed_size=False)
cfg.username = ConfigText(default="root", fixed_size=False)
cfg.password = ConfigPassword(default="", fixed_size=False)
cfg.port = ConfigInteger(21, (0, 65535))
cfg.passive = ConfigYesNo(False)
cfg.telnetport = ConfigInteger(23, (0, 65535))
cfg.stream_port = ConfigInteger(8001, (1, 65535))
cfg.backup = ConfigYesNo(False)
cfg.merge_lamedb = ConfigYesNo(True)
cfg.copy_iptv = ConfigYesNo(True)
cfg.streamrelay = ConfigYesNo(True)
cfg.streamrelay_port = ConfigInteger(17999, (1, 65535))



CROSS_PNG = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/selectioncross.png"))


# ---------------------------------------------------------------- helpers (no enigma calls - also used in threads)
def utf8(x):
	if isinstance(x, unicode):
		return x.encode("utf-8")
	return str(x)


def serverAddress():
	if cfg.address.value.strip():
		return cfg.address.value.strip()
	return "%d.%d.%d.%d" % tuple(cfg.ip.value)


def isServerSet():
	return serverAddress() not in ("", "0.0.0.0")


def localPrefix(address):
	return "%s%s." % (RCSC_PREFIX, address.replace(".", "_"))


def readLines(path):
	f = open(path)
	try:
		return f.read().replace("\r", "").split("\n")
	finally:
		f.close()


def writeFileAtomic(path, data):
	tmp = path + ".rcsc_tmp"
	f = open(tmp, "w")
	try:
		f.write(data)
	finally:
		f.close()
	os.rename(tmp, path)


def readBouquetName(path):
	try:
		for line in readLines(path):
			if line.startswith("#NAME "):
				return line[6:].strip()
	except Exception:
		pass
	return ""


def stripRemoteSuffix(name):
	return re.sub(r"\s*\(remote of [^)]*\)\s*$", "", name).strip()


def satName(pos):
	if pos == -1:
		return "IPTV"
	if pos == 0xeeee:
		return "DVB-T"
	if pos == 0xffff:
		return "DVB-C"
	if pos > 1800:
		return "%.1f°W" % ((3600 - pos) / 10.0)
	return "%.1f°E" % (pos / 10.0)


def parseRef(line):
	"""'#SERVICE x:y:...' -> list of fields or None"""
	ref = line[9:].strip()
	fields = ref.split(":")
	if len(fields) < 10:
		return None
	try:
		int(fields[1])
	except ValueError:
		return None
	return fields


def analyseBouquet(path):
	count = 0
	sats = {}
	try:
		lines = readLines(path)
	except Exception:
		return 0, []
	for line in lines:
		if not line.startswith("#SERVICE "):
			continue
		f = parseRef(line)
		if f is None:
			continue
		flags = int(f[1])
		if flags & FLAG_MARKER:
			continue
		if "http" in line or f[0] != "1":  # IPTV / media (4097, 5001, 5002 ...)
			count += 1
			sats[-1] = sats.get(-1, 0) + 1
			continue
		count += 1
		if flags & FLAG_MUST_DESCENT:
			continue
		try:
			pos = (int(f[6], 16) >> 16) & 0xffff
		except ValueError:
			continue
		sats[pos] = sats.get(pos, 0) + 1
	return count, sorted(sats.items(), key=lambda x: -x[1])


def satsText(sats, maxitems=2):
	if not sats:
		return ""
	txt = ", ".join([satName(p) for p, c in sats[:maxitems]])
	if len(sats) > maxitems:
		txt += " +%d" % (len(sats) - maxitems)
	return txt


def parseBouquetsIndex(path):
	"""bouquets.tv/radio -> list of bouquet file names"""
	result = []
	try:
		lines = readLines(path)
	except Exception:
		return result
	for line in lines:
		m = re.search(r'FROM BOUQUET "([^"]+)"', line)
		if m and line.startswith("#SERVICE"):
			f = parseRef(line)
			if f and (int(f[1]) & 512):  # isInvisible
				continue
			name = m.group(1)
			if name not in result:
				result.append(name)
	return result


def findAlternativeFiles(path):
	result = []
	try:
		lines = readLines(path)
	except Exception:
		return result
	for line in lines:
		if line.startswith("#SERVICE "):
			f = parseRef(line)
			if f and int(f[1]) & FLAG_MUST_DESCENT and not int(f[1]) & FLAG_MARKER:
				m = re.search(r'FROM BOUQUET "([^"]+)"', line)
				if m:
					result.append(m.group(1))
	return result


# ---------------------------------------------------------------- lamedb (format /4/)
def lamedbKey4(key):
	parts = key.split(":")
	try:
		return tuple([int(x, 16) for x in parts[:4]])
	except ValueError:
		return key.lower()


def readLamedb(path):
	lines = readLines(path)
	if not lines or not lines[0].startswith("eDVB services /4/"):
		return None
	transponders = OrderedDict()
	services = OrderedDict()
	i = 1
	n = len(lines)
	while i < n and lines[i] != "transponders":
		i += 1
	i += 1
	while i < n and lines[i] != "end":
		key = lines[i]
		data = []
		i += 1
		while i < n and lines[i] != "/" and lines[i] != "end":
			data.append(lines[i])
			i += 1
		if i < n and lines[i] == "/":
			i += 1
		k = lamedbKey4(key)
		if k not in transponders:
			transponders[k] = (key, data)
	i += 1
	while i < n and lines[i] != "services":
		i += 1
	i += 1
	while i + 2 < n and lines[i] != "end":
		k = lamedbKey4(lines[i])
		if k not in services:
			services[k] = (lines[i], lines[i + 1], lines[i + 2])
		i += 3
	tail = [x for x in lines[i + 1:] if x != ""]
	return lines[0], transponders, services, tail


def writeLamedb(path, db):
	header, transponders, services, tail = db
	out = [header, "transponders"]
	for key, data in transponders.values():
		out.append(key)
		out.extend(data)
		out.append("/")
	out.append("end")
	out.append("services")
	for entry in services.values():
		out.extend(entry)
	out.append("end")
	out.extend(tail)
	writeFileAtomic(path, "\n".join(out) + "\n")


def serviceNames(db):
	"""(sid, ns, tsid, onid) -> name"""
	names = {}
	if db:
		for k, entry in db[2].items():
			if isinstance(k, tuple):
				names[k] = entry[1]
	return names


# ---------------------------------------------------------------- downloads
class WebifFetcher(object):
	def __init__(self, address):
		self.address = address

	def _open(self, path, timeout=20):
		url = "http://%s:%d%s" % (self.address, cfg.webif_port.value, path)
		req = urllib2.Request(url)
		if cfg.webif_user.value:
			auth = base64.b64encode("%s:%s" % (cfg.webif_user.value, cfg.webif_password.value))
			req.add_header("Authorization", "Basic %s" % auth)
		return urllib2.urlopen(req, timeout=timeout).read()

	def _get(self, remote, local):
		data = self._open("/file?file=%s" % quote(REMOTE_DIR + remote))
		head = data[:300]
		if head.startswith("File '") and "not found" in head:
			raise IOError("not found: %s" % remote)
		if remote == "lamedb":
			if not head.startswith("eDVB services"):
				raise IOError("invalid lamedb")
		elif head.lstrip().startswith("<"):
			raise IOError("invalid answer for %s" % remote)
		f = open(local, "w")
		try:
			f.write(data)
		finally:
			f.close()
		return remote

	def get(self, remote, local):
		return threads.deferToThread(self._get, remote, local)

	def _json(self, path):
		return json.loads(self._open(path, timeout=6))

	def status(self):
		def work():
			info = {}
			try:
				info["status"] = self._json("/api/statusinfo")
			except Exception:
				pass
			try:
				info["device"] = self._json("/api/deviceinfo")
			except Exception:
				pass
			return info
		return threads.deferToThread(work)


class FtpFetcher(WebifFetcher):
	def get(self, remote, local):
		return FTPDownloader(self.address, cfg.port.value, REMOTE_DIR + remote, local,
			cfg.username.value, cfg.password.value, cfg.passive.value).deferred


def makeFetcher():
	if cfg.mode.value == "ftp":
		return FtpFetcher(serverAddress())
	return WebifFetcher(serverAddress())


# ---------------------------------------------------------------- conversion worker (runs in a thread)
def makeBackup():
	if not os.path.isdir("/media/hdd"):
		raise IOError("/media/hdd")
	if not os.path.isdir(BACKUP_DIR):
		os.makedirs(BACKUP_DIR)
	name = BACKUP_DIR + "enigma2_" + time.strftime("%Y-%m-%d_%H%M%S") + ".tar.gz"
	tar = tarfile.open(name, "w:gz")
	try:
		tar.add("/etc/enigma2", arcname="enigma2")
	finally:
		tar.close()
	old = sorted([x for x in os.listdir(BACKUP_DIR) if x.startswith("enigma2_") and x.endswith(".tar.gz")])
	for x in old[:-BACKUP_KEEP]:
		try:
			os.remove(BACKUP_DIR + x)
		except OSError:
			pass
	return name


def refKey(fields):
	"""first 10 fields of a service reference -> comparable key (hex, case and leading zeros ignored)"""
	try:
		return tuple([int(x, 16) for x in fields[:10]])
	except ValueError:
		return tuple([x.lower() for x in fields[:10]])


def readStreamRelay():
	"""1.6: /etc/enigma2/whitelist_streamrelay of the server (OE-A StreamRelay) - these channels are decrypted
	by the server and streamed on the StreamRelay port (17999) instead of the normal stream port"""
	relay = set()
	if not cfg.streamrelay.value or not os.path.exists(DIR_WORK + "whitelist_streamrelay"):
		return relay
	try:
		for line in readLines(DIR_WORK + "whitelist_streamrelay"):
			fields = line.strip().split(":")
			if len(fields) >= 10:
				relay.add(refKey(fields))
	except Exception:
		pass
	return relay


def convertLine(line, address, names, alternatives, relay=None):
	"""one #SERVICE line of the server bouquet -> local line, or None to skip"""
	f = parseRef(line)
	if f is None:
		return line
	flags = int(f[1])
	if flags & FLAG_MARKER:
		return line
	if "http" in line or f[0] != "1":  # IPTV / media (4097, 5001, 5002 ...)
		# IPTV of the server: internet link copied unchanged (1.3), or skipped when the option is off
		if not cfg.copy_iptv.value:
			return None
		# a proxy on the server itself (127.0.0.1 / localhost) is reached via the server address
		return re.sub(r"(?i)(%3a//|://)(127\.0\.0\.1|localhost)(?=[%:/])", r"\g<1>" + address, line)
	if flags & FLAG_MUST_DESCENT:
		m = re.search(r'FROM BOUQUET "([^"]+)"', line)
		alt = m and alternatives.get(m.group(1))
		if not alt:
			return None
		return convertLine(alt, address, names, {}, relay)
	base = ":".join(f[:10])
	name = ""
	try:
		name = names.get((int(f[3], 16), int(f[6], 16), int(f[4], 16), int(f[5], 16)), "")
	except ValueError:
		pass
	if not name and len(f) > 11:
		name = ":".join(f[11:]).strip()
	port = cfg.stream_port.value
	if relay and refKey(f) in relay:
		port = cfg.streamrelay_port.value
	url = "http://%s:%d/%s" % (address, port, base)
	return "#SERVICE %s:%s:%s" % (base, quote(url), name)


def readAlternatives():
	alternatives = {}
	if os.path.isdir(DIR_WORK):
		for fn in os.listdir(DIR_WORK):
			if fn.startswith("alternatives."):
				try:
					for line in readLines(DIR_WORK + fn):
						if line.startswith("#SERVICE "):
							alternatives[fn] = line
							break
				except Exception:
					pass
	return alternatives


def updateIndex(btype, add, remove):
	path = DIR_ENIGMA2 + "bouquets." + btype
	try:
		lines = readLines(path)
	except Exception:
		lines = ["#NAME User - Bouquets (%s)" % ("TV" if btype == "tv" else "Radio")]
	while lines and lines[-1] == "":
		lines.pop()
	out = []
	present = []
	for line in lines:
		m = re.search(r'FROM BOUQUET "([^"]+)"', line)
		if m and m.group(1) in remove:
			continue
		if m:
			present.append(m.group(1))
		out.append(line)
	t = "1" if btype == "tv" else "2"
	for fn in add:
		if fn not in present:
			out.append('#SERVICE 1:7:%s:0:0:0:0:0:0:0:FROM BOUQUET "%s" ORDER BY bouquet' % (t, fn))
	writeFileAtomic(path, "\n".join(out) + "\n")


def localConverted(address):
	"""list of (local file, name without suffix) of converted bouquets of this server"""
	prefix = localPrefix(address)
	result = []
	for fn in sorted(os.listdir(DIR_ENIGMA2)):
		if fn.startswith(prefix) and (fn.endswith(".tv") or fn.endswith(".radio")):
			result.append((fn, stripRemoteSuffix(readBouquetName(DIR_ENIGMA2 + fn))))
	return result


def convertWorker(items, address, merge):
	result = {"bouquets": 0, "channels": 0, "backup": None, "relay": 0}
	relay = readStreamRelay()
	relay_port = ":%d/" % cfg.streamrelay_port.value
	remote_db = None
	if os.path.exists(DIR_WORK + "lamedb"):
		try:
			remote_db = readLamedb(DIR_WORK + "lamedb")
		except Exception:
			remote_db = None
	names = serviceNames(remote_db)
	alternatives = readAlternatives()
	existing = localConverted(address)
	add = {"tv": [], "radio": []}
	remove = {"tv": [], "radio": []}
	for item in items:
		lines = readLines(DIR_WORK + item["remote"])
		out = []
		skip_desc = False
		for line in lines:
			if skip_desc and line.startswith("#DESCRIPTION"):
				skip_desc = False
				continue
			skip_desc = False
			if line.startswith("#NAME "):
				out.append("#NAME %s (remote of %s)" % (line[6:].strip(), address))
			elif line.startswith("#SERVICE "):
				new = convertLine(line, address, names, alternatives, relay)
				if new is None:
					skip_desc = True
					continue
				nf = parseRef(new)
				if nf and not int(nf[1]) & FLAG_MARKER:
					result["channels"] += 1
					if relay and quote(relay_port) in new:
						result["relay"] += 1
				out.append(new)
			elif line != "":
				out.append(line)
		writeFileAtomic(DIR_ENIGMA2 + item["local"], "\n".join(out) + "\n")
		result["bouquets"] += 1
		btype = item["type"]
		add[btype].append(item["local"])
		# bouquet with the same name (other file of this server) is replaced
		for fn, name in existing:
			if fn != item["local"] and name == item["name"] and fn.endswith("." + btype):
				try:
					os.remove(DIR_ENIGMA2 + fn)
				except OSError:
					pass
				remove[btype].append(fn)
	for btype in ("tv", "radio"):
		if add[btype] or remove[btype]:
			updateIndex(btype, add[btype], remove[btype])
	if merge and remote_db:
		try:
			local_db = readLamedb(DIR_ENIGMA2 + "lamedb")
			if local_db:
				for k, v in remote_db[1].items():
					if k not in local_db[1]:
						local_db[1][k] = v
				for k, v in remote_db[2].items():
					if k not in local_db[2]:
						local_db[2][k] = v
				writeLamedb(DIR_ENIGMA2 + "lamedb", local_db)
				result["lamedb"] = True
		except Exception as e:
			result["lamedb_error"] = str(e)
	return result


def deleteWorker(files):
	remove = {"tv": [], "radio": []}
	for fn in files:
		try:
			os.remove(DIR_ENIGMA2 + fn)
		except OSError:
			pass
		remove["radio" if fn.endswith(".radio") else "tv"].append(fn)
	for btype in ("tv", "radio"):
		if remove[btype]:
			updateIndex(btype, [], remove[btype])
	return len(files)


def reloadEnigmaLists(services=True):
	db = eDVBDB.getInstance()
	if services:
		db.reloadServicelist()
	db.reloadBouquets()


# ---------------------------------------------------------------- list
# DreamOS 4.5 and 5.0: colors in a MultiContent list only via a template (like the skins do) - a color directly in a row
# entry is taken as a template index and crashes enigma2 (1.1 test 2026-10-21).
# row: (item, name, name_converted_green, count, satellites, status_green, cross_png)
LIST_TEMPLATE = [
	MultiContentEntryPixmapAlphaBlend(pos=(8, 13), size=(30, 30), png=6),
	MultiContentEntryText(pos=(50, 0), size=(540, 56), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=1),
	MultiContentEntryText(pos=(50, 0), size=(540, 56), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=2, color=0x4fc02a, color_sel=0x9be87a),
	MultiContentEntryText(pos=(600, 0), size=(140, 56), font=1, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=3),
	MultiContentEntryText(pos=(758, 8), size=(2, 40), font=1, flags=RT_VALIGN_CENTER, backcolor=0xaaaaaa, backcolor_sel=0xaaaaaa),
	MultiContentEntryText(pos=(778, 0), size=(232, 56), font=1, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=4),
	MultiContentEntryText(pos=(1020, 0), size=(220, 56), font=1, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=5, color=0x4fc02a, color_sel=0x9be87a),
]


class RCSCList(MenuList):
	def __init__(self):
		MenuList.__init__(self, [], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.l.setFont(0, gFont("Regular", 30))
		self.l.setFont(1, gFont("Regular", 26))
		self.l.setTemplate(LIST_TEMPLATE)
		self.l.setItemHeight(56)


def listEntry(item):
	name = " ".join(item["name"].split())
	if item["type"] == "radio":
		name += " (Radio)"
	conv = item["converted"]
	return (item,
		"" if conv else name,
		name if conv else "",
		"%d" % item["count"],
		satsText(item["sats"]),
		_("converted") if conv else "",
		CROSS_PNG if item["selected"] else None)


BUTTONS = """
		<ePixmap pixmap="Default-FHD/skin_default/buttons/red.svg" position="10,5" size="300,70"/>
		<ePixmap pixmap="Default-FHD/skin_default/buttons/green.svg" position="310,5" size="300,70"/>
		<ePixmap pixmap="Default-FHD/skin_default/buttons/yellow.svg" position="610,5" size="300,70"/>
		<ePixmap pixmap="Default-FHD/skin_default/buttons/blue.svg" position="910,5" size="300,70"/>
		<widget backgroundColor="#9f1313" font="Regular;30" halign="center" source="key_red" render="Label" position="10,5" foregroundColor="#ffffff" shadowColor="#000000" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1"/>
		<widget backgroundColor="#1f771f" font="Regular;30" halign="center" source="key_green" render="Label" position="310,5" foregroundColor="#ffffff" shadowColor="#000000" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1"/>
		<widget backgroundColor="#a08500" font="Regular;30" halign="center" source="key_yellow" render="Label" position="610,5" foregroundColor="#ffffff" shadowColor="#000000" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1"/>
		<widget backgroundColor="#18188b" font="Regular;30" halign="center" source="key_blue" render="Label" position="910,5" foregroundColor="#ffffff" shadowColor="#000000" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1"/>
"""


# ---------------------------------------------------------------- main screen
class RCSCMain(Screen):
	skin = """
	<screen name="RCSCMain" position="center,110" size="1800,930" title="Remote channel stream converter">
		%(buttons)s
		<widget font="Regular;34" halign="right" position="1650,25" render="Label" size="120,40" source="global.CurrentTime" transparent="1">
			<convert type="ClockToText">Default</convert>
		</widget>
		<widget font="Regular;34" halign="right" position="1240,25" render="Label" size="400,40" source="global.CurrentTime" transparent="1">
			<convert type="ClockToText">Date</convert>
		</widget>
		<eLabel backgroundColor="#aaaaaa" position="10,80" size="1780,1"/>
		<widget name="list" position="10,90" size="1260,672" scrollbarMode="showOnDemand" enableWrapAround="1"/>
		<eLabel backgroundColor="#aaaaaa" position="1285,80" size="1,700"/>
		<widget source="server_title" render="Label" position="1300,90" size="480,40" font="Regular;30" foregroundColor="#e6bd00" transparent="1"/>
		<widget source="server_info" render="Label" position="1300,135" size="480,330" font="Regular;26" transparent="1"/>
		<widget source="detail_title" render="Label" position="1300,480" size="480,40" font="Regular;30" foregroundColor="#e6bd00" transparent="1"/>
		<widget source="detail" render="Label" position="1300,525" size="480,250" font="Regular;26" foregroundColor="#aaaaaa" transparent="1"/>
		<eLabel backgroundColor="#aaaaaa" position="10,790" size="1780,1"/>
		<widget source="status" render="Label" position="10,800" size="640,120" font="Regular;30" valign="center" foregroundColor="#e6bd00" transparent="1"/>
		<ePixmap pixmap="%(qr_small)s" position="700,806" size="99,99" alphatest="off"/>
		<widget source="youtube" render="Label" position="815,800" size="400,120" font="Regular;26" valign="center" transparent="1"/>
		<widget source="hint" render="Label" position="1290,800" size="490,120" font="Regular;26" halign="right" valign="center" foregroundColor="#e6bd00" transparent="1"/>
	</screen>""" % {"buttons": BUTTONS, "qr_small": QR_SMALL}

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle("%s %s  ·  %s" % (_("Remote channel stream converter"), VERSION, DREAMOS))
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText("")
		self["key_yellow"] = StaticText(_("Settings"))
		self["key_blue"] = StaticText("")
		self["list"] = RCSCList()
		self["server_title"] = StaticText(_("Server"))
		self["server_info"] = StaticText("")
		self["detail_title"] = StaticText(_("Selected bouquet"))
		self["detail"] = StaticText("")
		self["status"] = StaticText("")
		self["hint"] = StaticText(_("OK = select   MENU = options"))
		self["youtube"] = StaticText("YouTube  SetTvBox4U\n" + YOUTUBE)
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "MenuActions"], {
			"ok": self.keyOk,
			"cancel": self.keyClose,
			"red": self.keyClose,
			"green": self.keyGreen,
			"yellow": self.keySettings,
			"blue": self.keyBlue,
			"menu": self.keyMenu,
		}, -1)
		self.entries = []
		self.working = False
		self.closing = False
		self.fetcher = None
		self.serverText = ""
		self["list"].onSelectionChanged.append(self.updateDetail)
		self.onLayoutFinish.append(self.start)

	# ---- start / loading
	def start(self):
		if not isServerSet():
			self["status"].setText(_("Set the server IP first (yellow button)."))
			self.keySettings()
			return
		self.loadRemote()

	def prepareWorkDir(self):
		if not os.path.isdir(DIR_WORK):
			os.makedirs(DIR_WORK)
		for fn in os.listdir(DIR_WORK):
			try:
				os.remove(DIR_WORK + fn)
			except OSError:
				pass

	def loadRemote(self):
		self.working = True
		self.entries = []
		self["list"].setList([])
		self["key_green"].setText("")
		self["key_blue"].setText("")
		self.address = serverAddress()
		self.fetcher = makeFetcher()
		self.prepareWorkDir()
		self.updateServerInfo(None)
		self["status"].setText(_("Connecting to %s ...") % self.address)
		WebifFetcher(self.address).status().addCallback(self.statusReceived).addErrback(lambda e: None)
		self.fetchSeq(["bouquets.tv", "bouquets.radio"], None, self.indexFetched)

	def fetchSeq(self, names, fmt, done):
		self._queue = list(names)
		self._qi = 0
		self._qfmt = fmt
		self._qdone = done
		self._failed = []
		self._fetchNext()

	def _fetchNext(self, *args):
		if self.closing:
			return
		if self._qi >= len(self._queue):
			self._qdone(self._failed)
			return
		name = self._queue[self._qi]
		self._qi += 1
		if self._qfmt:
			self["status"].setText(self._qfmt % (self._qi, len(self._queue)))
		d = self.fetcher.get(name, DIR_WORK + name)
		d.addCallback(self._fetchNext)
		d.addErrback(self._fetchFailed, name)

	def _fetchFailed(self, failure, name):
		print "[RCSC] download failed:", name, failure
		self._failed.append(name)
		self._fetchNext()

	def indexFetched(self, failed):
		if "bouquets.tv" in failed:
			self.working = False
			self["status"].setText(_("Could not connect to %s") % self.address)
			return
		self.remoteIndex = []
		for btype in ("tv", "radio"):
			for fn in parseBouquetsIndex(DIR_WORK + "bouquets." + btype):
				if not fn.startswith(RCSC_PREFIX):
					self.remoteIndex.append((fn, btype))
		self.fetchSeq([x[0] for x in self.remoteIndex] + ["lamedb", "whitelist_streamrelay"], _("Reading bouquets %d of %d"), self.bouquetsFetched)

	def bouquetsFetched(self, failed):
		alternatives = []
		for fn, btype in self.remoteIndex:
			if fn not in failed:
				for alt in findAlternativeFiles(DIR_WORK + fn):
					if alt not in alternatives:
						alternatives.append(alt)
		self._bouquetFailed = failed
		if alternatives:
			self.fetchSeq(alternatives, _("Reading alternatives %d of %d"), self.allFetched)
		else:
			self.allFetched([])

	def allFetched(self, failed):
		self.working = False
		self.buildItems()
		if not self.entries:
			self["status"].setText(_("Download from server failed"))
			return
		self["key_green"].setText(_("Convert"))
		self["key_blue"].setText(_("Invert"))
		self.showSummary()

	def buildItems(self):
		prefix = localPrefix(self.address)
		converted = localConverted(self.address)
		convertedNames = dict([(name, fn) for fn, name in converted])
		self.entries = []
		for fn, btype in self.remoteIndex:
			if fn in self._bouquetFailed:
				continue
			count, sats = analyseBouquet(DIR_WORK + fn)
			name = readBouquetName(DIR_WORK + fn) or fn
			local = prefix + fn
			isConv = os.path.exists(DIR_ENIGMA2 + local) or name in convertedNames
			self.entries.append({"remote": fn, "type": btype, "name": name, "count": count, "sats": sats,
				"local": local, "converted": isConv, "selected": False})
		self.refreshList()

	def refreshList(self):
		idx = self["list"].getSelectionIndex() if self.entries else 0
		self["list"].setList([listEntry(x) for x in self.entries])
		if self.entries:
			self["list"].moveToIndex(min(idx, len(self.entries) - 1))
		self.updateDetail()

	def showSummary(self, extra=""):
		conv = len([x for x in self.entries if x["converted"]])
		txt = _("%d bouquets on server, %d converted") % (len(self.entries), conv)
		if extra:
			txt = extra + "   " + txt
		self["status"].setText(txt)

	# ---- server info
	def statusReceived(self, info):
		if not self.closing:
			self.updateServerInfo(info)

	def updateServerInfo(self, info):
		mode = _("OpenWebif (no password)") if cfg.mode.value == "webif" else _("FTP (with password)")
		lines = ["%s  ·  %s" % (serverAddress(), mode)]
		if info is None:
			pass
		elif not info:
			lines.append(_("Server status unknown (OpenWebif not reachable)."))
		else:
			dev = info.get("device") or {}
			if dev:
				lines.append("%s %s  ·  %s %s" % (utf8(dev.get("brand", "")), utf8(dev.get("model", "")),
					utf8(dev.get("friendlyimagedistro", dev.get("imagedistro", ""))), utf8(dev.get("imagever", ""))))
			st = info.get("status") or {}
			standby = utf8(st.get("inStandby", "")).lower() == "true"
			if standby:
				lines.append(_("Server is in standby - tuner is free."))
			elif st.get("currservice_name"):
				lines.append(_("Server is watching: %s") % utf8(st.get("currservice_name")))
			busy = []
			for t in dev.get("tuners", []):
				use = [x for x in ("live", "rec", "stream") if t.get(x)]
				if use:
					busy.append("%s (%s)" % (utf8(t.get("name", "")).replace("Tuner ", ""), "/".join(use)))
			if busy:
				lines.append(_("Server busy tuners: %s") % ", ".join(busy))
			lines.append("")
			lines.append(_("Tip: if the server has only one tuner configured, the Dreambox plays only channels of the transponder the server is on (or all, when the server is in standby)."))
		self["server_info"].setText("\n".join([utf8(x) for x in lines]))

	def updateDetail(self):
		item = self.currentItem()
		if not item:
			self["detail"].setText("")
			return
		sats = ", ".join(["%s (%d)" % (satName(p), c) for p, c in item["sats"][:5]])
		lines = [" ".join(item["name"].split()),
			"%d %s" % (item["count"], _("channels")),
			"%s: %s" % (_("Satellites"), sats or "-"),
			"%s: %s" % (_("Status"), _("converted") if item["converted"] else _("not converted")),
			"%s: %s" % (_("File"), item["remote"]),
			"",
			_("Bouquet with the same name is replaced, other bouquets stay.")]
		self["detail"].setText("\n".join(lines))

	def currentItem(self):
		cur = self["list"].getCurrent()
		if isinstance(cur, dict):
			return cur
		if isinstance(cur, (list, tuple)) and cur and isinstance(cur[0], dict):
			return cur[0]
		return None

	# ---- keys
	def keyClose(self):
		self.closing = True
		self.close()

	def keyOk(self):
		item = self.currentItem()
		if self.working or not item:
			return
		item["selected"] = not item["selected"]
		self.refreshList()

	def keyBlue(self):
		if self.working or not self.entries:
			return
		for x in self.entries:
			x["selected"] = not x["selected"]
		self.refreshList()

	def keySettings(self):
		if self.working:
			return
		self.session.openWithCallback(self.settingsClosed, RCSCSetup)

	def settingsClosed(self, changed=False):
		if changed or (isServerSet() and not self.entries):
			if isServerSet():
				self.loadRemote()

	def keyGreen(self):
		if self.working or not self.entries:
			return
		selected = [x for x in self.entries if x["selected"]]
		if not selected:
			self["status"].setText(_("No bouquets selected"))
			return
		self.convert(selected)

	def keyMenu(self):
		if self.working:
			return
		conv = [x for x in self.entries if x["converted"]]
		local = localConverted(serverAddress()) if isServerSet() else []
		menu = []
		if self.entries:
			menu.append((_("Update all converted bouquets (%d)") % len(conv), "update"))
			menu.append((_("Delete selected converted bouquets"), "delete_sel"))
		menu.append((_("Delete all converted bouquets of this server (%d)") % len(local), "delete_all"))
		menu.append((_("Reload list from server"), "reload"))
		menu.append((_("Server settings"), "settings"))
		menu.append((_("About"), "about"))
		self.session.openWithCallback(self.menuCallback, ChoiceBox, title=_("Options"), list=menu)

	def menuCallback(self, choice):
		if not choice:
			return
		action = choice[1]
		if action == "update":
			conv = [x for x in self.entries if x["converted"]]
			if not conv:
				self["status"].setText(_("No converted bouquets."))
				return
			missing = len(localConverted(self.address)) - len(conv)
			self.convert(conv, missing > 0 and (_("Not found on server: %d") % missing) or "")
		elif action == "delete_sel":
			files = [x["local"] for x in self.entries if x["selected"] and x["converted"] and os.path.exists(DIR_ENIGMA2 + x["local"])]
			self.askDelete(files)
		elif action == "delete_all":
			self.askDelete([fn for fn, name in localConverted(serverAddress())])
		elif action == "reload":
			if isServerSet():
				self.loadRemote()
		elif action == "settings":
			self.keySettings()
		elif action == "about":
			self.session.open(RCSCAbout)

	# ---- delete
	def askDelete(self, files):
		if not files:
			self["status"].setText(_("No converted bouquets."))
			return
		self._deleteFiles = files
		self.session.openWithCallback(self.deleteConfirmed, MessageBox, _("Really delete %d converted bouquets?") % len(files), MessageBox.TYPE_YESNO, default=False)

	def deleteConfirmed(self, answer):
		if not answer:
			return
		self.working = True
		threads.deferToThread(deleteWorker, self._deleteFiles).addCallback(self.deleteDone).addErrback(self.workerFailed)

	def deleteDone(self, count):
		self.working = False
		reloadEnigmaLists(services=False)
		if self.entries:
			self.buildItems()
		self.showSummary(_("Deleted %d bouquets.") % count)

	# ---- convert
	def convert(self, items, extra=""):
		self.working = True
		self._convertItems = items
		self._convertExtra = extra
		self._backupName = None
		if cfg.backup.value:
			self["status"].setText(_("Creating backup ..."))
			threads.deferToThread(makeBackup).addCallback(self.backupDone).addErrback(self.backupFailed)
		else:
			self.startConvert()

	def backupDone(self, name):
		self._backupName = name
		self.startConvert()

	def backupFailed(self, failure):
		self.working = False
		self.session.open(MessageBox, _("Backup failed: %s") % failure.getErrorMessage(), MessageBox.TYPE_ERROR)
		self.showSummary()

	def startConvert(self):
		self["status"].setText(_("Converting %d bouquets ...") % len(self._convertItems))
		threads.deferToThread(convertWorker, self._convertItems, self.address, cfg.merge_lamedb.value) \
			.addCallback(self.convertDone).addErrback(self.workerFailed)

	def convertDone(self, result):
		self.working = False
		reloadEnigmaLists(services=True)
		for x in self.entries:
			x["selected"] = False
		self.buildItems()
		msg = _("Done: %d bouquets, %d channels converted.") % (result["bouquets"], result["channels"])
		if result.get("relay"):
			msg += "  " + _("StreamRelay: %d channels") % result["relay"]
		if self._convertExtra:
			msg += "  " + self._convertExtra
		self.showSummary()
		self["status"].setText(msg)
		text = msg
		if self._backupName:
			text += "\n" + _("Backup: %s") % self._backupName
		self.session.open(MessageBox, text, MessageBox.TYPE_INFO, timeout=8)

	def workerFailed(self, failure):
		self.working = False
		print "[RCSC] worker failed:", failure
		self["status"].setText("%s: %s" % (_("Conversion failed"), failure.getErrorMessage()))


# ---------------------------------------------------------------- about (1.4: own screen with the QR code of the YouTube channel)
class RCSCAbout(Screen):
	skin = """
	<screen name="RCSCAbout" position="center,center" size="1500,620" title="About">
		<widget source="text" render="Label" position="30,30" size="1050,560" font="Regular;30" valign="center" transparent="1"/>
		<ePixmap pixmap="%(qr_big)s" position="1130,110" size="330,330" alphatest="off"/>
		<widget source="qr_label" render="Label" position="1100,450" size="390,110" font="Regular;26" halign="center" valign="top" foregroundColor="#e6bd00" transparent="1"/>
	</screen>""" % {"qr_big": QR_BIG}

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("About"))
		self["text"] = StaticText("\n".join([
			_("Remote channel stream converter for %s") % DREAMOS,
			_("Updated by %s since %s") % (UPDATED_BY, UPDATED_SINCE),
			"YouTube: SetTvBox4U  -  %s" % YOUTUBE,
			"",
			_("Updated and extended version of the open-source Enigma2 plugin \"Remote channel stream converter\" for DreamOS 4.5 and 5.0."),
			_("Original plugin published by: OpenPLi, E2OpenPlugins, OE-Alliance"),
			_("Converts bouquets of another Enigma2 receiver (server) into stream bouquets, so that the Dreambox uses the tuners of the server."),
			"",
			_("Version %s  ·  updated %s") % (VERSION, VERSION_DATE) + "  ·  " + _("License: GPL-3.0")]))
		self["qr_label"] = StaticText("YouTube  SetTvBox4U\n" + YOUTUBE)
		self["actions"] = ActionMap(["OkCancelActions"], {"ok": self.close, "cancel": self.close}, -1)


# ---------------------------------------------------------------- settings
class RCSCSetup(ConfigListScreen, Screen):
	skin = """
	<screen name="RCSCSetup" position="center,170" size="1200,820" title="Server settings">
		<ePixmap pixmap="Default-FHD/skin_default/buttons/red.svg" position="10,5" size="300,70"/>
		<ePixmap pixmap="Default-FHD/skin_default/buttons/green.svg" position="310,5" size="300,70"/>
		<ePixmap pixmap="Default-FHD/skin_default/buttons/blue.svg" position="610,5" size="300,70"/>
		<widget backgroundColor="#9f1313" font="Regular;30" halign="center" source="key_red" render="Label" position="10,5" foregroundColor="#ffffff" shadowColor="#000000" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1"/>
		<widget backgroundColor="#1f771f" font="Regular;30" halign="center" source="key_green" render="Label" position="310,5" foregroundColor="#ffffff" shadowColor="#000000" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1"/>
		<widget backgroundColor="#18188b" font="Regular;30" halign="center" source="key_blue" render="Label" position="610,5" foregroundColor="#ffffff" shadowColor="#000000" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1"/>
		<widget font="Regular;34" halign="right" position="1050,25" render="Label" size="120,40" source="global.CurrentTime" transparent="1">
			<convert type="ClockToText">Default</convert>
		</widget>
		<eLabel backgroundColor="#aaaaaa" position="10,80" size="1180,1"/>
		<widget enableWrapAround="1" name="config" position="10,90" scrollbarMode="showOnDemand" size="1180,600"/>
		<eLabel backgroundColor="#aaaaaa" position="10,700" size="1180,1"/>
		<widget source="description" render="Label" position="10,710" size="1180,100" font="Regular;28" halign="center" valign="center" foregroundColor="#aaaaaa" transparent="1"/>
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Server settings"))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_blue"] = StaticText(_("Keyboard"))
		self["description"] = StaticText("")
		self.list = []
		ConfigListScreen.__init__(self, self.list, session=session, on_change=self.changed)
		self["actions"] = ActionMap(["SetupActions", "ColorActions"], {
			"save": self.keySave,
			"green": self.keySave,
			"cancel": self.keyCancel,
			"red": self.keyCancel,
			"blue": self.keyKeyboard,
		}, -2)
		self.createSetup()
		self["config"].onSelectionChanged.append(self.updateDescription)
		self.onLayoutFinish.append(self.updateDescription)

	def createSetup(self):
		lst = []
		lst.append(getConfigListEntry(_("Connection"), cfg.mode, cfg.mode.value == "webif" and _("OpenWebif needs no password if web authentication on the server is off.") or _("FTP needs the root password of the server.")))
		lst.append(getConfigListEntry(_("Server IP address"), cfg.ip, ""))
		if cfg.mode.value == "webif":
			lst.append(getConfigListEntry(_("OpenWebif port"), cfg.webif_port, ""))
			lst.append(getConfigListEntry(_("OpenWebif user (optional)"), cfg.webif_user, _("OpenWebif needs no password if web authentication on the server is off.")))
			lst.append(getConfigListEntry(_("OpenWebif password (optional)"), cfg.webif_password, _("OpenWebif needs no password if web authentication on the server is off.")))
		else:
			lst.append(getConfigListEntry(_("FTP user"), cfg.username, _("FTP needs the root password of the server.")))
			lst.append(getConfigListEntry(_("FTP password"), cfg.password, _("FTP needs the root password of the server.")))
			lst.append(getConfigListEntry(_("FTP port"), cfg.port, ""))
			lst.append(getConfigListEntry(_("FTP passive mode"), cfg.passive, ""))
		lst.append(getConfigListEntry(_("Stream port"), cfg.stream_port, _("Port of the server's stream (OpenWebif/streamserver), usually 8001.")))
		lst.append(getConfigListEntry(_("Use StreamRelay of the server"), cfg.streamrelay, _("Channels in the StreamRelay list of the server (whitelist_streamrelay) are decrypted by the server and streamed on its StreamRelay port.")))
		if cfg.streamrelay.value:
			lst.append(getConfigListEntry(_("StreamRelay port"), cfg.streamrelay_port, _("StreamRelay port of the server, usually 17999.")))
		lst.append(getConfigListEntry(_("Merge server lamedb (names, providers)"), cfg.merge_lamedb, _("Adds the server's services to the local lamedb without duplicates.")))
		lst.append(getConfigListEntry(_("Copy IPTV channels (internet links)"), cfg.copy_iptv, _("IPTV channels of the server are copied with their original internet links - the Dreambox plays them directly from the internet.")))
		lst.append(getConfigListEntry(_("Backup /etc/enigma2 before converting"), cfg.backup, _("Backup to /media/hdd/rcsc-backup (last 3 are kept).")))
		lst.append(getConfigListEntry(_("Plugin language"), cfg.language, ""))
		self.list = lst
		self["config"].list = lst
		self["config"].l.setList(lst)

	def changed(self):
		cur = self["config"].getCurrent()
		if cur and cur[1] in (cfg.mode, cfg.language, cfg.streamrelay):
			self.createSetup()

	def updateDescription(self):
		cur = self["config"].getCurrent()
		self["description"].setText(cur and len(cur) > 2 and cur[2] or "")

	def keyKeyboard(self):
		cur = self["config"].getCurrent()
		if cur and isinstance(cur[1], ConfigText):
			self.KeyText()

	def keySave(self):
		changed = self["config"].isChanged()
		self.saveAll()
		cfg.mode.save()
		configfile.save()
		self.close(True if changed else False)

	def keyCancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close(False)


# ---------------------------------------------------------------- plugin
def main(session, **kwargs):
	session.open(RCSCMain)


def menu(menuid, **kwargs):
	if menuid == "scan":
		return [(_("Remote channel stream converter"), main, "streamconvert", 60)]
	return []


def Plugins(**kwargs):
	return [PluginDescriptor(name=_("Remote channel stream converter"), description=_("Convert remote channel list for streaming"),
		where=PluginDescriptor.WHERE_MENU, fnc=menu)]
