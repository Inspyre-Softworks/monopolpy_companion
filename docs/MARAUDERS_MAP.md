# Marauder’s Map

The Marauder’s Map keeps developer tools unobtrusive during ordinary play and
offers a whimsical way to discover them. It is a local convenience. Anyone
who can edit the profile file or call the engine directly can activate or use
developer grants. The Map provides no authentication, authorization, or
protection against deliberate access.

## Open, unlock, and relock

1. In an unfinished game with no auction in progress, press **Ctrl+Shift+M**.
   If the Map is locked, read the parchment and choose **Continue**.
2. In the second parchment dialog, enter
   `I solemnly swear that I am up to no good.` and press **Enter** or choose
   **Reveal the Map**. The words remain visible as you type. **Cancel** or
   **Esc** dismisses either parchment without changing the developer state.
3. The **Marauder’s Map** toolbar button appears after unlocking. Click it or
   use the shortcut again to go straight to the grant dialog. Grants include
   cash, unowned deeds, houses, and hotels.
4. Choose **Mischief managed** in the grant dialog to close and relock the Map.
   Closing the dialog normally leaves developer mode enabled.

Developer mode is a profile-wide preference that survives app restarts and game
changes. The toolbar button appears at startup when the profile is unlocked. It
becomes usable in an unfinished game with no auction in progress.
State lives outside saved games.

## State and execution flow

`SessionController._dev_lock_path()` resolves `Path.home() / 'mm.lock'`.
On Windows this is typically `%USERPROFILE%\mm.lock`. The controller restores
the state when it is constructed and whenever it installs a session, including
when a new game starts or a save opens. The file is reread at those boundaries.
Edits made while a game is open take effect on the next restoration.

| Exact file contents (UTF-8) | Restored state |
| --- | --- |
| `I solemnly swear that I am up to no good.` | Enabled |
| `Mischief managed!` | Disabled |
| Missing, empty, unreadable, malformed, or any other contents | Disabled |

State comparison is byte-for-byte. A trailing newline, BOM, different case, or
missing period in the file disables developer mode. The dialog input is more
forgiving. It folds case, collapses whitespace, and accepts the phrase with or
without the final period. Successful submission writes the canonical bytes
without a newline.

`MainWindow._open_dev_tools()` is the shared handler for the toolbar button and
shortcut. It checks for an eligible game before opening a dialog. For a locked
game it calls `_introduce_map()`, then `_prompt_map_phrase()` if the player
continues. It delegates the state change to `SessionController.unlock_dev_tools()`.
That method checks the current session and submitted phrase, persists the state,
then marks developer mode enabled. A wrong phrase shows a message and leaves the
file untouched. For an enabled game the handler skips both parchment dialogs.

`DevToolsDialog` dispatches grants through `SessionController.perform()`.
The controller checks the in-memory developer flag, game completion, and auction
state before dispatch. The engine validates grants and records them in the
ledger, and the controller follows its existing autosave and notification
flow. Developer grants intentionally bypass the ordinary player PIN prompts.
`DevToolsDialog._lock()` calls `SessionController.lock_dev_tools()`, which
clears the flag immediately and persists the relock state.

The state writer creates a temporary file in the profile directory, writes and
flushes the canonical state, calls `fsync`, and replaces `mm.lock` with
`os.replace`. The same-directory replacement avoids an intermediate partially
written state. The writer cleans up the temporary file on failure. A missing
file is normal at startup. Other read errors log a warning and leave the flag
disabled. If an unlock write fails, the dashboard reports the error and leaves
the Map locked. If a relock write fails, the dialog warns and the current
controller locks immediately, but a previously enabled file can restore the
Map on restart or game change. Fix profile write access and retry the relock,
or remove `mm.lock` manually to restore the default locked state.

## Dialogs, fonts, and resources

The private builders in [map_unlock.py](../monopolpy_companion/ui/map_unlock.py)
create custom Qt dialogs with a framed parchment panel and standard widgets.
The introduction and phrase entry are separate modal steps. The phrase dialog
uses a labeled and accessible `QLineEdit` with normal echo, initial focus,
keyboard submission, and a default action. Layout managers, point-sized fonts,
and Qt's logical-pixel geometry support DPI scaling. When changing the visuals,
keep the focus indicator, text contrast, keyboard actions, and wrapping intact.

Both Map fonts are bundled under
[ui/resources](../monopolpy_companion/ui/resources). The loader reads the bytes
with `importlib.resources.files('monopolpy_companion.ui')`, registers them with
`QFontDatabase.addApplicationFontFromData()`, and caches the reported family
for the process. It checks that Qt actually registered the expected family.

| Font | Use | Source and license |
| --- | --- | --- |
| Caveat | Parchment inscription and typed phrase | [Caveat project](https://github.com/googlefonts/caveat), Copyright 2014 The Caveat Project Authors. [SIL OFL 1.1 notice](../monopolpy_companion/ui/resources/Caveat-OFL.txt). |
| Source Sans 3 | Narrative prose, instructions, and buttons | [Adobe Source Sans](https://github.com/adobe-fonts/source-sans), Copyright 2010–2020 Adobe, reserved font name Source. [SIL OFL 1.1 notice](../monopolpy_companion/ui/resources/SourceSans3-OFL.txt). |

The font files come from the [Caveat](https://github.com/google/fonts/tree/main/ofl/caveat)
and [Source Sans 3](https://github.com/google/fonts/tree/main/ofl/sourcesans3)
directories in the Google Fonts collection. The supplied upstream notices are
kept beside the binaries. A missing or rejected resource logs a warning naming
the file. Decorative text falls back to a readable italic font, and body text
uses the application's font. The dialogs remain usable. Reinstall a complete
build and restart to restore bundled fonts after a resource failure.

Two pre-existing files under `monopolpy_companion/lib/fonts` are outside this
Map resource set. `Monopoly Regular.ttf` identifies Hyun S. Choi, and
`MONOPOLY_INLINE.ttf` identifies NimaVisual. Their embedded notices say all
rights reserved, with no redistribution license verified in this repository.
The Map loads neither file. Optional dashboard fonts described in
[GUI.md](GUI.md) are user-provided.

To replace a Map font, verify redistribution terms, keep the upstream copyright
and license notice with the binary, update the resource filename and expected
family in the loader, and update the font tests and this table. Keep the state
and grant logic in the controller and the visual changes in the dialog module.
If changing the persisted state format, retain compatibility with the two
existing canonical values or explicitly migrate them.

## Packaging

Poetry includes `monopolpy_companion/ui/resources` in both wheel and source
formats. The compatibility `setup.py` also lists the TTFs and OFL notices as
package data. Use `poetry check --lock` and `poetry build`, then inspect the
`dist` archives with `python -m zipfile -l <wheel>` and
`python -m tarfile -l <source-archive>`. Check for both TTFs and both notices
under the UI resource directory.

For a PyInstaller desktop build, install the Qt extra and PyInstaller in the
build environment, then run from the project root:

```text
python -m PyInstaller --onedir --name MonopolPy-Companion --collect-data monopolpy_companion.ui monopolpy_companion.py
```

Keep the generated resource tree alongside the executable and run it with
`--gui`. The collector preserves the package-relative layout used by the
resource loader. For other freezer configurations, explicitly collect the same
four files at `monopolpy_companion/ui/resources`. This repository does not
automatically produce frozen desktop releases.

## Verification

Install the Qt extra with `poetry install -E gui`. Run the complete suite:

```text
poetry run python -m unittest discover -s tests -v
```

Run the relevant modules individually with discovery patterns
`test_map_unlock.py`, `test_session_controller.py`, or `test_qt_gui.py`,
for example:

```text
poetry run python -m unittest discover -s tests -p test_map_unlock.py -v
```

- [Controller tests](../tests/test_session_controller.py) use temporary
  profile files and fresh controllers to check startup restore, relocking,
  invalid bytes, trailing content, and a failed atomic replacement.
- [Dashboard tests](../tests/test_qt_gui.py) check the shortcut binding and
  handler, toolbar visibility, grants, and the toolbar path that skips the
  phrase prompt after restoration.
- [Dialog tests](../tests/test_map_unlock.py) check the actual bytes passed
  to Qt, the fonts resolved by Qt's renderer, Continue, Enter, visible
  typing, and the logged fallback for missing and corrupt resources.

Set `QT_QPA_PLATFORM=offscreen` for headless testing. For visual review,
inspect both dialogs under the application stylesheet at normal and enlarged
scaling. Check the full phrase, focus indicator, readable controls, and the
inscription's resolved font.

For version `1.0.dev32`, all 104 tests passed on Windows using Qt offscreen.
Fresh Python processes restored both profile states. Visual review covered
both dialogs at 100% and 150% scaling with the application stylesheet, and
Qt resolved the expected bundled fonts. Both Poetry archives and a Windows
PyInstaller build contained the two binaries and two notices byte-for-byte.
The frozen executable was smoke-tested with `--help`. The visual review used
the Python application, and native macOS and Linux window decoration and
screen-reader behavior were not verified.
