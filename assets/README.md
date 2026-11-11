# The 1.3 update's data

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
`nolf2-eu-1.3` install, `rez/README.md`); the files are unchanged. They are
Monolith's and Fox's, as the rest of the game's data is
(`docs/LICENSE-NOTES.md`).
