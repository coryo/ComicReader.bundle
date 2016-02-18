ComicReader
===========

A Plex Media Server channel.

Browse and view locally stored CBR, CBZ comic book archives. It currently acts like a file browser, starting at the directory specified in the channels preferences.

Format Support
--------------

* **CBZ**
* **CBR** - requires unrar. The channel will use the executables in `Contents/bin` depending on which OS your server is on.

Plex Client Support
-------------------

**working**: OpenPHT, PMP, Plex Web, Android

**not working**: iOS (won't load images but will load thumbnails)

Channel Preferences
-------------------

 * **cb path:** path to the root directory of where CBZ, CBR archives are.
