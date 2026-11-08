# Plugin API v1

A plugin is an independently installed distribution. Register a zero-argument
factory in the `monopolpy_companion.plugins` entry point group. The entry point
name is the plugin identifier. Duplicate identifiers are rejected.

```toml
[project.entry-points."monopolpy_companion.plugins"]
example = "monopolpy_plugins.example:ExamplePlugin"

[tool.poetry]
packages = [{ include = "monopolpy_plugins", from = "src" }]
```

Leave `src/monopolpy_plugins/__init__.py` absent so distributions can share the
PEP 420 namespace.

```python
from monopolpy_companion.plugins import PluginMetadata

class ExamplePlugin:
    metadata = PluginMetadata("Example", min_api=1, max_api=1)

    def start(self, context):
        context.subscribe(self.on_event)

    def stop(self):
        pass

    def on_event(self, event):
        print(event.name)
```

The inclusive compatibility range applies to the host API version independently
of either distribution's version. Metadata lives on the factory and is checked
after import but before construction. Listing entry points does not import them.
Plugins execute in-process with the host's privileges. Install and enable
plugins from publishers you trust.

A host calls `start(context)` once per enable and calls `stop()` on disable,
shutdown, or failed startup. Write `stop()` to tolerate partial initialization.
The host removes actions and subscriptions when a plugin stops. Register and
invoke extensions on the host thread. Embedded hosts can use
`PluginManager.enable()`, `disable()`, and `close()` and inspect `errors`.

The context exposes controller notifications as detached `GameEvent` objects.
They have a name, details, and UTC timestamp. These are live notifications,
including `session_changed`, rather than a replayable ledger or a guarantee of
a successful disk write. `current_game()` returns a detached snapshot of the
shared game with PIN hashes and salts removed. Game saves already persist
transactions, dice rolls, and movement where recorded. Older saves may lack
those histories. Treat missing data as unavailable. Callbacks and snapshots
share the permissions of the running host. Plugin views that show private
account analytics must enforce account authorization separately.

Check `context.has_ui` before using `context.add_action(label, callback)`.
The Qt dashboard puts these commands on a Plugins toolbar. The callback runs
on the UI thread. A plugin can use it to open its own PySide6 dialog.

## Installation and integration

For development, keep both Git checkouts as siblings and open both folders
in the editor. Install the host with `poetry install -E gui`. Once the plugin
has a distribution, add it to a disposable integration environment or use
`poetry add --editable ../monopolpy-companion-stats` in a disposable host checkout.
The latter changes that checkout's Poetry files. Keep the path dependency out
of commits so releases stay independent.

For an installed host, use its exact Python interpreter to run
`python -m pip install monopolpy-companion-stats` once the distribution is
available. Use `--upgrade` for upgrades and `python -m pip uninstall
monopolpy-companion-stats` for removal. Pip reports dependency resolution
failures. Restart the host after modifying the environment. The current desktop
launcher uses the installed Python package and its optional GUI extra. A future
frozen build needs an explicit extension environment and discovery strategy.

List registrations with `monopolpy-companion --list-plugins` and opt in for a
GUI launch with `monopolpy-companion --gui --enable-plugin stats`. Without the
enable flag, the desktop starts with plugins disabled.
