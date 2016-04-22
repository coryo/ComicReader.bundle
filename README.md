ComicReader
===========

A Plex Media Server channel.

Browse and view locally stored CB(Z, R, 7) comic book archives. It currently acts like a file browser, starting at the directory specified in the channels preferences.

Format Support
--------------

* .CB**Z** - the ideal format for the channel. Consider converting archives to zip, it's much easier to work with.
* .CB**R** - requires [unrar](http://www.rarlab.com/download.htm).
* .CB**7** - requires [7zip](http://www.7-zip.org/download.html). not thoroughly tested.


#### Windows

 * [unrar](http://www.rarlab.com/rar/unrarw32.exe)
 * [7zip](http://www.7-zip.org/download.html)
 * set channel preferences paths:
   * `C:\Program Files (x86)\WinRAR\unrar.exe` if you installed WinRAR, or `C:\wherever\unrar.exe`
   * `C:\Program Files (x86)\7-Zip\7z.exe` if you installed 7-Zip.

#### Ubuntu

    sudo apt-get install unrar p7zip
    which 7z
    which unrar

#### OSX

use [Homebrew](http://brew.sh/)

    brew install p7zip
    brew install unrar
    which 7z
    which unrar


Plex Client Support
-------------------

**working**: OpenPHT, PMP, Plex Web, Android, iOS


Channel Preferences
-------------------

 * **Comics Path:** path to the root directory of where CBZ, CBR, CB7 archives are.
 * **Unrar Executable Path:** path to `unrar` binary. Leave blank to use the included copies (I may remove these at some point).
 * **7-Zip Executable Path:** path to `7z` binary.
