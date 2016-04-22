ComicReader
===========

A Plex Media Server channel.

Browse and view locally stored CB(Z, R, 7) comic book archives. It currently acts like a file browser, starting at the directory specified in the channels preferences.

Format Support
--------------

* .CB**Z** - the ideal format for the channel.
* .CB**R** - requires unrar. The channel will use the executables in `Contents/bin` depending on which OS your server is on.
* .CB**7** - requires 7zip. Binary not included, set it in channel preferences.
    * warning: not thoroughly tested.

Plex Client Support
-------------------

**working**: OpenPHT, PMP, Plex Web, Android, iOS

Channel Preferences
-------------------

 * **Comics Path:** path to the root directory of where CBZ, CBR archives are.
 * **7zip Executable Path:** path to `7z`. examples:
   * Windows: `C:\Program Files (x86)\7-Zip\7z.exe`
   * Linux: `/usr/bin/7z`
