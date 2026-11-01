# Lizenzen der Fremdkomponenten

*Deutsch – [English below](#licenses-of-third-party-components)*

Diese Datei gilt für die veröffentlichte `WetterWidget.exe`. Wer stattdessen
`wetter_widget.py` mit einem eigenen Python laufen lässt, bündelt nichts und
braucht hier nur die Zeile zu pywebview.

## Das Wichtigste in vier Sätzen

Das Wetter Widget selbst steht unter der MIT-Lizenz, und das bleibt auch für
die gebündelte EXE so. Darin liegen aber fremde Bestandteile – die
Python-Laufzeit, pywebview, pythonnet und die WebView2-Komponenten von
Microsoft –, deren Bedingungen unverändert weitergelten. Keiner dieser
Bestandteile verlangt, dass das Gesamtwerk unter eine andere Lizenz gestellt
wird. Vollständige Lizenztexte liegen jedem Release als
`WetterWidget-lizenztexte.zip` bei.

### Warum bleibt alles MIT?

Weil in diesem Bündel kein Copyleft steckt, das nach außen greift:

- **Kein GPL-Teil ohne Ausnahme.** Der einzige GPL-Bestandteil ist der
  Bootloader von PyInstaller, und dessen Lizenz enthält ausdrücklich eine
  Ausnahme für die damit gepackten Programme.
- **Die übrigen Pakete** stehen unter MIT, BSD, Apache 2.0 oder der
  PSF-Lizenz. Alle verlangen Namensnennung und den Lizenztext – genau dafür
  gibt es diese Datei und das beiliegende ZIP –, nicht aber eine bestimmte
  Lizenz für das Gesamtwerk.
- **Die WebView2-Teile von Microsoft** bleiben unter Microsofts Bedingungen.
  Sie erlauben die Weitergabe zusammen mit einer Anwendung; auf die Lizenz
  dieser Anwendung wirken sie nicht ein.

Die MIT-Lizenz in `LICENSE` gilt also für den Code dieses Projekts, und für
jeden fremden Bestandteil gilt zusätzlich seine eigene Lizenz.

## Was in der Windows-EXE steckt

Nachgesehen an der fertigen Datei und an der Stückliste, die PyInstaller beim
Bauen schreibt – nicht angenommen. Geprüft wird das bei jedem Release von
`buendel_pruefen.py`.

| Bestandteil | Lizenz | Lizenztext und Quelle |
|---|---|---|
| **Python 3.14** – Laufzeit und Standardbibliothek (`python314.dll`) | PSF License 2.0 | [docs.python.org](https://docs.python.org/3/license.html) |
| **pywebview** – zeigt die Seite im nativen Fenster (`WebBrowserInterop.*.dll`) | BSD 3-Clause | [LICENSE](https://github.com/r0x0r/pywebview/blob/master/LICENSE) |
| **pythonnet** – Brücke von Python nach .NET (`Python.Runtime.dll`) | MIT | [LICENSE](https://github.com/pythonnet/pythonnet/blob/master/LICENSE) |
| **clr_loader** – lädt die .NET-Laufzeit (`ClrLoader.dll`) | MIT | [LICENSE](https://github.com/pythonnet/clr-loader/blob/master/LICENSE) |
| **Microsoft WebView2 SDK 1.0.3856.49** – `Microsoft.Web.WebView2.Core.dll`, `.WinForms.dll`, `WebView2Loader.dll` | Microsoft Software License Terms | [Lizenz auf NuGet](https://www.nuget.org/packages/Microsoft.Web.WebView2), [Weitergabe](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution) |
| **.NET-Laufzeitteile** – `netstandard.dll` und die `System.*.dll`, von pythonnet mitgebracht | MIT | [LICENSE.TXT](https://github.com/dotnet/runtime/blob/main/LICENSE.TXT) |
| **bottle** – Webserver-Gerüst, das pywebview mitbringt | MIT | [LICENSE](https://github.com/bottlepy/bottle/blob/master/LICENSE) |
| **proxy_tools** – verzögerte Objekte in pywebview | MIT (das Paket legt keinen Lizenztext bei) | [Projektseite](https://github.com/jtushman/proxy_tools) |
| **cffi** – ruft C-Funktionen auf, von clr_loader gebraucht (`_cffi_backend.pyd`) | MIT | [LICENSE](https://github.com/python-cffi/cffi/blob/main/LICENSE) |
| **pycparser** – liest C-Deklarationen für cffi | BSD 3-Clause | [LICENSE](https://github.com/eliben/pycparser/blob/main/LICENSE) |
| **typing_extensions** – Typangaben für ältere Python-Fassungen | PSF License 2.0 | [LICENSE](https://github.com/python/typing_extensions/blob/main/LICENSE) |
| **setuptools** – samt eigener Kopien von jaraco.text, more_itertools, tomli, wheel und packaging | MIT (die Kopien MIT bzw. Apache-2.0/BSD-2) | [LICENSE](https://github.com/pypa/setuptools/blob/main/LICENSE) |
| **packaging** – Versionsvergleiche, von setuptools und PyInstaller gebraucht | Apache 2.0 **oder** BSD 2-Clause | [LICENSE](https://github.com/pypa/packaging/blob/main/LICENSE) |
| **OpenSSL** (`libssl-3.dll`, `libcrypto-3.dll`) – Teil der Python-Laufzeit | Apache License 2.0 | [openssl-library.org](https://openssl-library.org/source/license/) |
| **libffi** (`libffi-8.dll`) – Teil der Python-Laufzeit | MIT | [LICENSE](https://github.com/libffi/libffi/blob/master/LICENSE) |
| **Expat** (`pyexpat.pyd`) – XML-Leser der Standardbibliothek | MIT | [COPYING](https://github.com/libexpat/libexpat/blob/master/expat/COPYING) |
| **bzip2** (`_bz2.pyd`) – Teil der Python-Laufzeit | BSD-artig | [sourceware.org](https://sourceware.org/bzip2/) |
| **XZ Utils / liblzma** (`_lzma.pyd`) – Teil der Python-Laufzeit | 0BSD (Kernteil gemeinfrei) | [COPYING](https://github.com/tukaani-project/xz/blob/master/COPYING) |
| **Zstandard** (`_zstd.pyd`) – Teil der Python-Laufzeit ab 3.14 | BSD 3-Clause | [LICENSE](https://github.com/facebook/zstd/blob/dev/LICENSE) |
| **PyInstaller** – dessen Bootloader startet die gepackte Anwendung | GPLv2 **mit** Ausnahme für damit erzeugte Programme | [Lizenzhinweis](https://pyinstaller.org/en/stable/license.html) |

### Nicht in der EXE: die WebView2-Laufzeit selbst

Die Darstellung übernimmt die **Evergreen-Laufzeit** von Microsoft, die auf
Windows 10 und 11 bereits vorhanden ist und über Windows Update gepflegt wird.
In der EXE liegt nur der schmale Teil, der sie anspricht: die beiden
`Microsoft.Web.WebView2`-Assemblies und `WebView2Loader.dll`. Das Widget
bringt also keinen Browser mit und aktualisiert auch keinen.

### Vollständige Lizenztexte

MIT, BSD und die PSF-Lizenz verlangen bei der Weitergabe eines Binärbündels
den Lizenztext selbst, nicht nur einen Verweis. Die Texte liegen deshalb jedem
Release als `WetterWidget-lizenztexte.zip` bei. Sie werden beim Bauen von
`lizenztexte_sammeln.py` aus den Paketen geholt, die dafür installiert waren –
so passen sie zu genau dieser EXE, und es liegt keine Kopie im Repository, die
beim nächsten Versionssprung still veraltet.

Was dort nicht als Text, sondern als Verweis steht, ist in der Übersicht des
ZIP genannt: die WebView2-Bedingungen, die .NET-Teile und die Bestandteile des
Windows-Builds von Python.

### Der Bootloader von PyInstaller

PyInstaller steht unter der GPLv2 – mit einer Ausnahme, die ausdrücklich
erlaubt, damit gepackte Programme unter jeder Lizenz weiterzugeben,
einschließlich kommerzieller. In der EXE steckt nur der Bootloader, nicht
PyInstaller selbst. Ohne diese Ausnahme müsste das Bündel unter die GPL
gestellt werden; mit ihr bleibt es bei MIT.

### Was setuptools mitbringt

PyInstaller braucht setuptools, und setuptools nimmt eigene Kopien fremder
Pakete mit. Im Bündel landen davon `jaraco.text`, `jaraco.context`,
`jaraco.functools`, `more_itertools`, `backports.tarfile`, `tomli`, `wheel`
und eine zweite Fassung von `packaging` – alle unter MIT, packaging unter
Apache 2.0 oder BSD 2-Clause. Ihre Lizenztexte sind im ZIP enthalten und am
Dateinamen als Kopien aus `setuptools/_vendor` zu erkennen.

### Nicht aufgeführt: Systembibliotheken von Windows

`VCRUNTIME140.dll`, `ucrtbase.dll` und die `api-ms-win-*.dll` gehören zum
Betriebssystem beziehungsweise zu dessen Laufzeitpaket. Sie werden von Python
mitgebracht, sind aber keine Fremdkomponenten dieses Projekts im Sinne einer
eigenen Lizenzpflicht.

## Pflege dieser Datei

Die Liste wird nicht von Hand nachgeführt, sondern nach jedem Bau geprüft:

```bash
python buendel_pruefen.py build/WetterWidget --streng
```

Das Skript liest die Stückliste von PyInstaller und bricht ab, sobald im
Bündel ein Paket liegt, das hier nicht steht. Im Release-Workflow läuft es mit
`--streng` – ein Release entsteht also nicht, solange die Liste unvollständig
ist. Beim Bau von Hand meldet es nur; eine Python-Installation mit vielen
Paketen bringt sonst Teile mit, die in der veröffentlichten EXE nicht liegen.

Was es prüft, und was nicht: Es erkennt die Posten aus `site-packages`, also
die Python-Pakete samt der Dateien, die sie mitbringen – dort liegen auch die
DLLs von WebView2 und .NET. Die Bestandteile des Windows-Builds von Python
(OpenSSL, libffi, Expat, bzip2, XZ Utils, Zstandard) kommen nicht von dort und
stehen in der Tabelle von Hand; sie ändern sich nur mit der Python-Reihe, mit
der gebaut wird, und die hält der Release-Workflow fest. Die Fassung des
WebView2-SDK vergleicht er beim Bauen mit dieser Datei: Hebt Dependabot
pywebview an und bringt das eine neue Fassung mit, wird der Lauf rot, bis die
Zahl hier stimmt.

---

# Licenses of third-party components

*English – [Deutsch oben](#lizenzen-der-fremdkomponenten)*

This file is about the published `WetterWidget.exe`. If you run
`wetter_widget.py` with your own Python instead, nothing is bundled and only
the pywebview row applies to you.

## The short version

Wetter Widget itself is MIT-licensed, and the bundled executable stays that
way. It does contain third-party parts – the Python runtime, pywebview,
pythonnet and Microsoft's WebView2 components – whose terms continue to apply
unchanged. None of them requires the work as a whole to be placed under a
different license. Full license texts are attached to every release as
`WetterWidget-lizenztexte.zip`.

### Why does everything stay MIT?

Because this bundle contains no copyleft that reaches outwards:

- **No GPL part without an exception.** The only GPL component is
  PyInstaller's bootloader, and its license explicitly carries an exception
  for the programs it packages.
- **The remaining packages** are MIT, BSD, Apache 2.0 or PSF licensed. They
  all require attribution and the license text – which is what this file and
  the attached ZIP are for – but not a particular license for the whole work.
- **Microsoft's WebView2 parts** remain under Microsoft's terms. Those terms
  permit redistribution alongside an application and do not affect that
  application's own license.

So the MIT license in `LICENSE` covers this project's code, and every
third-party part additionally keeps its own license.

## What is inside the Windows executable

Checked against the finished file and against the inventory PyInstaller writes
while building – not assumed. `buendel_pruefen.py` verifies it on every
release.

| Component | License | License text and source |
|---|---|---|
| **Python 3.14** – runtime and standard library (`python314.dll`) | PSF License 2.0 | [docs.python.org](https://docs.python.org/3/license.html) |
| **pywebview** – shows the page in a native window (`WebBrowserInterop.*.dll`) | BSD 3-Clause | [LICENSE](https://github.com/r0x0r/pywebview/blob/master/LICENSE) |
| **pythonnet** – bridge from Python to .NET (`Python.Runtime.dll`) | MIT | [LICENSE](https://github.com/pythonnet/pythonnet/blob/master/LICENSE) |
| **clr_loader** – loads the .NET runtime (`ClrLoader.dll`) | MIT | [LICENSE](https://github.com/pythonnet/clr-loader/blob/master/LICENSE) |
| **Microsoft WebView2 SDK 1.0.3856.49** – `Microsoft.Web.WebView2.Core.dll`, `.WinForms.dll`, `WebView2Loader.dll` | Microsoft Software License Terms | [license on NuGet](https://www.nuget.org/packages/Microsoft.Web.WebView2), [distribution](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution) |
| **.NET runtime parts** – `netstandard.dll` and the `System.*.dll`, brought along by pythonnet | MIT | [LICENSE.TXT](https://github.com/dotnet/runtime/blob/main/LICENSE.TXT) |
| **bottle** – web server scaffolding that pywebview brings along | MIT | [LICENSE](https://github.com/bottlepy/bottle/blob/master/LICENSE) |
| **proxy_tools** – lazy objects used by pywebview | MIT (the package ships no license text) | [project page](https://github.com/jtushman/proxy_tools) |
| **cffi** – calls C functions, needed by clr_loader (`_cffi_backend.pyd`) | MIT | [LICENSE](https://github.com/python-cffi/cffi/blob/main/LICENSE) |
| **pycparser** – reads C declarations for cffi | BSD 3-Clause | [LICENSE](https://github.com/eliben/pycparser/blob/main/LICENSE) |
| **typing_extensions** – typing backports for older Python versions | PSF License 2.0 | [LICENSE](https://github.com/python/typing_extensions/blob/main/LICENSE) |
| **setuptools** – including its own copies of jaraco.text, more_itertools, tomli, wheel and packaging | MIT (the copies MIT or Apache-2.0/BSD-2) | [LICENSE](https://github.com/pypa/setuptools/blob/main/LICENSE) |
| **packaging** – version comparisons, needed by setuptools and PyInstaller | Apache 2.0 **or** BSD 2-Clause | [LICENSE](https://github.com/pypa/packaging/blob/main/LICENSE) |
| **OpenSSL** (`libssl-3.dll`, `libcrypto-3.dll`) – part of the Python runtime | Apache License 2.0 | [openssl-library.org](https://openssl-library.org/source/license/) |
| **libffi** (`libffi-8.dll`) – part of the Python runtime | MIT | [LICENSE](https://github.com/libffi/libffi/blob/master/LICENSE) |
| **Expat** (`pyexpat.pyd`) – the standard library's XML parser | MIT | [COPYING](https://github.com/libexpat/libexpat/blob/master/expat/COPYING) |
| **bzip2** (`_bz2.pyd`) – part of the Python runtime | BSD-style | [sourceware.org](https://sourceware.org/bzip2/) |
| **XZ Utils / liblzma** (`_lzma.pyd`) – part of the Python runtime | 0BSD (core in the public domain) | [COPYING](https://github.com/tukaani-project/xz/blob/master/COPYING) |
| **Zstandard** (`_zstd.pyd`) – part of the Python runtime from 3.14 on | BSD 3-Clause | [LICENSE](https://github.com/facebook/zstd/blob/dev/LICENSE) |
| **PyInstaller** – its bootloader starts the packaged application | GPLv2 **with** an exception for the programs it builds | [license notice](https://pyinstaller.org/en/stable/license.html) |

### Not inside the executable: the WebView2 runtime itself

Rendering is done by Microsoft's **Evergreen runtime**, which is already
present on Windows 10 and 11 and is maintained through Windows Update. The
executable only contains the thin part that talks to it: the two
`Microsoft.Web.WebView2` assemblies and `WebView2Loader.dll`. The widget
therefore neither ships nor updates a browser.

### Full license texts

MIT, BSD and the PSF license require the license text itself to accompany a
binary distribution, not merely a link. The texts are therefore attached to
every release as `WetterWidget-lizenztexte.zip`. They are gathered at build
time by `lizenztexte_sammeln.py` from the packages that were installed for the
build – so they match this exact executable, and no copy sits in the
repository growing quietly out of date.

Whatever is linked rather than included as text is named in the ZIP's
overview: the WebView2 terms, the .NET parts and the components of the Windows
build of Python.

### PyInstaller's bootloader

PyInstaller is GPLv2 – with an exception that explicitly permits distributing
the programs it packages under any license, commercial ones included. Only the
bootloader ends up in the executable, not PyInstaller itself. Without that
exception the bundle would have to be placed under the GPL; with it, MIT
remains.

### What setuptools brings along

PyInstaller needs setuptools, and setuptools carries its own copies of
third-party packages. Of those, `jaraco.text`, `jaraco.context`,
`jaraco.functools`, `more_itertools`, `backports.tarfile`, `tomli`, `wheel`
and a second copy of `packaging` end up in the bundle – all MIT, packaging
under Apache 2.0 or BSD 2-Clause. Their license texts are in the ZIP and can
be recognised by their file names as copies from `setuptools/_vendor`.

### Not listed: Windows system libraries

`VCRUNTIME140.dll`, `ucrtbase.dll` and the `api-ms-win-*.dll` belong to the
operating system and its runtime package. Python brings them along, but they
are not third-party components of this project in the sense of a separate
licensing duty.

## Keeping this file current

The list is not maintained by hand but verified after every build:

```bash
python buendel_pruefen.py build/WetterWidget --streng
```

The script reads PyInstaller's inventory and stops as soon as the bundle
contains a package that is not listed here. The release workflow runs it with
`--streng`, so no release is produced while the list is incomplete. A manual
build only gets a report: a Python installation with many packages would
otherwise pull in parts that are not in the published executable.

What it checks, and what it does not: it recognises entries from
`site-packages`, that is the Python packages and the files they bring along –
the WebView2 and .NET DLLs among them. The components of the Windows build of
Python (OpenSSL, libffi, Expat, bzip2, XZ Utils, Zstandard) do not come from
there and are listed by hand; they only change with the Python series used for
the build, which the release workflow pins. The WebView2 SDK version is
compared against this file during the build: if Dependabot bumps pywebview and
that brings a new SDK, the run turns red until the number here matches.
