ComicReader
===========

A Plex Media Server channel.

Browse and view locally stored CBZ, CBR, CB7 comic book archives. It currently acts like a file browser, starting at the directory specified in the channels preferences.

Format Support
--------------

* .CB**Z** - the ideal format for the channel. Consider converting archives to zip, it's much easier to work with.
* .CB**R** - requires [unrar](http://www.rarlab.com/download.htm).
* .CB**7** - requires [7-Zip](http://www.7-zip.org/download.html) (windows). or [p7zip](http://p7zip.sourceforge.net) (linux, osx).


.zip, .rar, and .7z should also work.

#### Windows

 * [unrar](http://www.rarlab.com/rar/unrarw32.exe)
 * [7-Zip](http://www.7-zip.org/download.html)
 * set channel preferences paths:
   * `C:\Program Files (x86)\WinRAR\unrar.exe` if you installed WinRAR, or `C:\wherever\unrar.exe`
   * `C:\Program Files (x86)\7-Zip\7z.exe` if you installed 7-Zip.


#### Ubuntu

    sudo apt-get install unrar p7zip


#### OSX

use [Homebrew](http://brew.sh/)

    brew install p7zip
    brew install unrar


Plex Client Support
-------------------

**working**: OpenPHT, PMP, Plex Web, Android, iOS


Channel Preferences
-------------------

 * **Comics Path:** path to the root directory of where comic archives are stored.
 * **Enable resume feature:** add a 'resume' option to the main menu. This makes an attempt at remembering the last page that was viewed and allowing you to get back easier. Because of the way Plex works this isn't 100% reliable, so this is disabled by default.
 * **Unrar Executable Path:** path to `unrar` binary. leave blank if `unrar` is in `$PATH`.
 * **7-Zip Executable Path:** path to `7z` binary. leave blank if `7z` is in `$PATH`.
