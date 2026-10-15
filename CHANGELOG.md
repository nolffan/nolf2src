# Changelog

What the modern build changes from the retail game: _No One Lives Forever 2:
A Spy in H.A.R.M.'s Way_, version 1.3.

The release build is the retail game rebuilt from source, unchanged, bugs
included; none of this applies to it. [`docs/MODERN.md`](docs/MODERN.md)
covers each change in detail, under its item number (M-E1, M-G2 and so on).
[`docs/RETAIL_BUGS.md`](docs/RETAIL_BUGS.md) describes the retail bugs.

## Unreleased

- **Out of the water at high frame rates** the player floats and jumps as
  high as at 60 frames a second. (M-E4)
- **The frame-rate limit's default is 240** (it was 300). The Display
  screen's choices are unchanged, and multiplayer stays at 60. (M-E4)
- **Documentation** moves to `docs/`, with new
  [`docs/INSTALL.md`](docs/INSTALL.md), [`docs/CONSOLE.md`](docs/CONSOLE.md)
  and [`docs/VARIABLES.md`](docs/VARIABLES.md).

## The modern build, compared with retail

### Graphics and display

- **Wide screens.** Every resolution at least as wide as 4:3 is offered,
  including wide ones, in the game and in the launcher. The field of view
  widens with the screen instead of stretching (Hor+), and the weapon's
  effects keep their shape. (M-E1, M-G1, M-E15)
- **A field-of-view slider** on the Display screen, 50 to 100 degrees
  vertical (78 in retail). (M-G4)
- **Menus and the HUD at any resolution.** On a wide screen the menus keep
  their 4:3 layout, centred, with their 3D art beside them, and the HUD keeps
  to the screen's edges. Retail stretched them, and at 16:9 the menus ran off
  the bottom of the screen. (M-G2)
- **Scopes and camera overlays** black out the sides of a wide screen
  instead of showing the world past them. (M-G34)
- **Cinematics** can be limited to 4:3 with side bars ("4:3 cinematics" on
  the Display screen). (M-G36)
- **Window mode:** full screen, a window, or a borderless window at the
  desktop's resolution, on the Display screen and in the launcher. A change
  applies at once. A window can be any size, a framed window keeps its whole
  picture, and the window opens on the primary monitor. (M-E2, M-G40, M-G42,
  M-E30, M-G70, M-L5)
- **Run in background:** in a window, the game no longer goes black and
  reloads when it loses the focus, and can play on behind other windows
  (Display screen). (M-G41)
- **No crash at 3840x2160**, and none leaving the Display screen when no
  resolution is listed. (M-E31)
- **Antialiasing** (2x, 4x or 8x), full screen or in a window, on the
  Display screen. (M-E13)
- **Anisotropic filtering** at 2x, 4x, 8x or 16x. Retail's "On" was no
  better than bilinear. (M-G45)
- **A frame-rate counter** (`ShowFramerate 1`). (M-G44)

### Frame rate and timing

- **A frame-rate limit.** Retail had none and ran as fast as it could. The
  limit is 240 frames a second by default; the Display screen offers 30 to
  300, or none; multiplayer stays at 60 at most. (M-E4)
- **The game behaves the same at high frame rates.** In retail, at high
  frame rates the AIs slowed down (a third of their speed at 300), the player
  walked slower and crouch-walked barely at all, snow and rain stopped
  falling, weapon inaccuracy, fire sparks and debris changed with the frame
  rate, and the player floated lower in water and jumped out of it lower.
  (M-E4)
- **The music** no longer drops out of its warning and combat themes above
  100 frames a second. (M-G30)

### Controls

- **Mouse look fixed.** Retail counted each mouse movement two to four
  times, unevenly, and more at high frame rates, which made aim jumpy and hard
  to control. Each movement now counts once. The sensitivity slider reaches
  lower for today's mice, and the "Input rate" slider, which no longer does
  anything for the mouse, is gone. (M-E3)
- **The mouse wheel** moves through the menus as the arrow keys do. (M-G43)

### Controller

- **Xbox-style (XInput) controllers**, including the Steam Deck's controls
  through Steam Input. Buttons are rebindable like keys, and a controller can
  be plugged in at any time. (M-G47, M-E20)
- **Analog look and movement**: the right stick looks, the left stick walks
  or runs with how far it is pushed, and both drive the snowmobile. (M-G47)
- **A default layout** for the controller in every profile. (M-G60)
- **The menus, cut-scenes and dialogue choices** work with the controller:
  the d-pad or left stick, A, B and Start; A skips cut-scenes. (M-G61)
- **A Controller screen** with look speed, invert look and dead zones, in
  place of retail's joystick set-up. (M-G62)
- DirectInput joysticks are no longer used. (M-E21)

### Sound and movies

- **No proprietary middleware.** Bink is replaced by our own FFmpeg-based
  player; the intro movies play. (M-X1)

### Multiplayer

- **No CD key.** Sierra's key servers are gone, so retail could no longer
  join an Internet server, or any server by address. The key check and the
  key field are gone. (M-G17)
- **Names and chat** with `%` in them, and over-long chat lines, can no
  longer crash clients and servers. (M-G5)
- **The server ignores** debugging and single-player commands from remote
  clients and out-of-range skill levels, and keeps player names unique.
  (M-G7, M-G8, M-G9)
- **The server list** keeps the selected server. (M-G26)
- The modern build plays with other modern builds only: the multiplayer
  handshake turns away a client whose game code differs from the server's.

### Launcher and installation

- **The launcher in the game directory**, with a script to start it under
  Wine. (M-L1)
- **No disc.** The launcher no longer probes optical drives at every start.
  (M-L4)
- **The launcher's dedicated server** starts. Retail looked for a program
  under the wrong name. (M-L2)
- **Window mode** in the launcher's Display dialog. (M-L5)

### Bug fixes

These retail bugs are fixed (details in
[`docs/RETAIL_BUGS.md`](docs/RETAIL_BUGS.md)):

- **Ones you can see:**
  - The frame-rate faults above (M-E4, M-G30) and mouse look (M-E3).
  - Grass and snow volumes could crash the game as they came into or went
    out of view. (M-G19, M-G20)
  - The zoomed view was about 7% flatter than the normal one. (M-G35)
  - A controller's buttons were bound to the wrong controls. (M-G63)
  - An AI backing away faced the wrong way; a keyframed object that did not
    move lost its rotation; a client effect's colour step set the wrong
    colour. (M-G12, M-G13, M-G15)
- **Crashes:**
  - An object's activation link broken while in use. (M-G18)
  - An AI's forced dodge, and an AI checking a body that is gone. (M-G22,
    M-G23)
  - Head and aim tracking going wrong at an extreme angle. (M-G25)
  - A radar object without a type. (M-G27)
  - Facing a zero direction, and a music mood with no levels. (M-G10,
    M-G11, M-G14)
  - Missing checks in the engine's client interface, and its console
    print. (M-E8, M-E10)
  - An endless loop stopping music. (M-E7)
- **Security:**
  - Format strings and over-long lines in names and chat. (M-G5)
  - An unbounded server message; debugging messages obeyed from any
    client; skill levels out of range. (M-G6, M-G7, M-G8)
- **Leaks and smaller errors:**
  - the launcher's path buffer and find handles (M-L3);
  - a leaked file on a stream error (M-E12);
  - a string's length (M-G16);
  - error and trace messages naming the wrong function or parameter (M-E9,
    M-E11).

### Not included

- The developer console on screen (M-E5); console commands still come from
  the command line and `autoexec.cfg` (see
  [`docs/CONSOLE.md`](docs/CONSOLE.md)).
- The Internet server list (M-E6): Sierra's servers are gone; LAN play and
  direct joins work.
- The damage flash on wide screens (M-G38), a jukebox (M-G46), the dedicated
  server without the installer's registry (M-G50), controller rumble (M-G64)
  and on-screen button prompts (M-G65).
