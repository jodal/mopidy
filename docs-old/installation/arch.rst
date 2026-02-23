<<<<<<<<<<<<<<<<<<<<<<<<<< conflict 1 of 1
%%%%%%%%%%%%%%%%%%%%%%%%%% diff from: ntuutrol 490d03bf "docs: Fix reference to default config file" (parents of rebased revision)
\\\\\\\\\\\\\\\\\\\\\\\\\\        to: ntmvmzzm 879890a6 "Merge pull request #2243 from rnestler/fix-archlinux-installation-instructions" (rebase destination)
 .. _arch-install:
 
 **********
 Arch Linux
 **********
 
 If you are running Arch Linux, you can install
-`mopidy <https://www.archlinux.org/packages/community/any/mopidy/>`_
-from the "Community" repository, as well as
+`mopidy <https://www.archlinux.org/packages/extra/any/mopidy/>`_
+from the "Extra" repository, as well as
 many extensions from AUR.
 
 
-Install from Community
-======================
+Install from Extra
+==================
 
 #. To install Mopidy with all dependencies, you can use::
 
        pacman -S mopidy
 
    To upgrade Mopidy to future releases, just upgrade your system using::
 
        pacman -Syu
 
 #. Now, you're ready to :ref:`run Mopidy <running>`.
 
 
 Installing extensions
 =====================
 
 If you want to use any Mopidy extensions, like Spotify support or Last.fm
 scrobbling, AUR has packages for many `Mopidy extensions
 <https://aur.archlinux.org/packages/?K=mopidy>`_.
 
 To install one of the listed packages, e.g. ``mopidy-mpd``, simply run::
 
    yay -S mopidy-mpd
 
 If you cannot find the extension you want in AUR, you can
 install it from PyPI using ``pip`` instead.
 Even if Mopidy itself is installed with pacman it will correctly detect and use
 extensions from PyPI installed globally on your system using::
 
    sudo python3 -m pip install ...
 
 For a comprehensive index of available Mopidy extensions,
 including those not installable from AUR,
 see the `Mopidy extension registry <https://mopidy.com/ext/>`_.
++++++++++++++++++++++++++ tpqvsnts d57e1c41 "chore: Move existing docs site to docs-old" (rebased revision)
>>>>>>>>>>>>>>>>>>>>>>>>>> conflict 1 of 1 ends
