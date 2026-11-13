# The 1.3 update's data, and the map packs

What Sierra's free English 1.3 update for *No One Lives Forever 2*
(`nolf2-update_1x3.exe`, SHA-256
`7e0f70806437979a39806d8aea08751e2ccfebdb50dad752eed03cac35437157`, as it
was published for download) adds to the game, other than code. It ships
with this project's releases, so installing needs only the player's two
discs.

- `rez/`: the contents of the update's `Update_v1x3.rez`, as its archive
  has them, less the five game binaries (`CSHELL.DLL`, `OBJECT.LTO`,
  `CLIENTFX.FXD`, `CRES.DLL`, `SRES.DLL`), which this project builds from
  source, and the 24 `VSSVER.scc` files (Visual SourceSafe's bookkeeping,
  packed by accident): 112 files -- three worlds (`C07`, `C10S01`,
  `CP_C02S02`), the multiplayer characters, ClientFX, textures, the HUD's
  icons, the Doomsday mode's art and sounds, and the attribute files.
  `build/all.sh` packs it into the game directory's `nolf2src.rez` with
  lithtools' `lithrez` (`build/lithrez.sh`), with a fixed time
  (1044489600, the 1.3 readme's date) so that every build makes the same
  bytes. The game loads it where the update's installer put its archive:
  after the discs' archives, before `custom/` (`build/nolf2cmds.sh`).
- `game/`: the two files the update installs outside its archive that the
  game uses: `autoexec.cfg` and `Profiles/Default.prf`, 1.3's settings and
  default profile, which the game directory starts from
  (`autoexec.cfg.retail`, `Default.prf.retail`).

The rest of the update -- its engine, launcher and dedicated server, its
readmes and Sierra's updater -- is either built from source here or not
needed. Taken out of rez/'s copy of the update (`Update_v1x3.rez` of the
`nolf2-eu-1.3` install, `ext/rez/README.md`); the files are unchanged. They
are Monolith's and Fox's, as the rest of the game's data is
(`docs/LICENSE_NOTES.md`).

## The map packs

Sierra's two free official multiplayer map packs ship with the releases
too. Each installer installed one archive into the game directory, and
registered it as content (the launcher and the dedicated server load content
after the discs' archives and before the updates):

| | Installer (SHA-256, as published) | Archive | Registry |
|---|---|---|---|
| `mappack001/` | `si_nolf2_mappack01.exe` (`bb4d0e09e127d6622ca0aa14ef0e89c2b1352635403a5783b20bd39c8522eb89`) | `MapPack001.rez`: nine deathmatch worlds, `DM_01` to `DM_09` | `ContentCommandLine0` = `-rez MapPack001.rez` |
| `mappack002/` | `si_nolf2_update_mappack2.exe` (`ae3876d57d6eeab3f11458de5a8c164ddbcc0d14a428f60402181181c85b1b1d`) | `MapPack002.rez`: seven Doomsday worlds, `DD_01` to `DD_07` | `ContentCommandLine1` = `-rez MapPack002.rez` |

Each directory is its archive's contents, as the archive has them
(`WORLDS/RETAILMULTIPLAYER/`: each world's `.DAT`, its `.CFG`, the `.TXT`
of its objects and the `.DTX` of its loading screen), less the archive's
`VSSVER.SCC`: 36 and 28 files. The archives are the same as the Mac
release's `MapPack001.rez` and `MapPack002.rez` (`ext/rez/games.sha256`,
`nolf2-mac-usa`). Taken out of `ext/rez/mappacks/` (the installers' cabinets
with `ext/rez/tools/sfxcab.py`, the archives with `ext/rez/tools/unshield`,
their files with `lithrez x`); the files are unchanged.

`build/all.sh` packs each back into its archive, `MapPack001.rez` and
`MapPack002.rez`, with `lithrez c --compat 1.10` (NOLF2's LithRez, which
writes no resource IDs) and the original archive's time (1037757884 and
1044088336), so that every build makes the same bytes. `lithrez diff --data`
against the originals: the same files, the same data, only the time of each
file differs (the original LithRez stamped each with the clock as it wrote
it). The legacy build's game scripts write the installers' registry values
(`ContentNum` 2), and its `nolf2cmds.txt` has the archives in the
launcher's order; the modern build's launcher and dedicated server load them
from the game directory when the registry has no content (`docs/MODERN.md`,
M-L6, M-G50). The map packs' installers installed no other file: the rest of
each is InstallShield's own runtime.
