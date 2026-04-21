import argparse

from monopolpy_companion.lib.common.paths import ensure_runtime_dirs
from monopolpy_companion.lib.helpers import logger


name = "MonopolPyCompanion"
log = logger.start(name, "debug")

log.debug(f"Setting up argument parsing for {name}")
parser = argparse.ArgumentParser(
    description="Start the Monopolpy Companion program",
    prog="monopolpy_companion",
)

conffile_help = (
    "Specify the absolute path to a custom configuration file. "
    "The file must be in YAML format."
)
parser.add_argument("--conf-file", action="store", dest="conf_file", help=conffile_help)

gui_help = "Start the program in graphical user interface mode, using PySimpleGUI."
parser.add_argument("--gui", dest="gui", help=gui_help, required=False, default=None, action="store_true")

devmode_help = "Start the program in developer mode with debug logging enabled."
parser.add_argument("--dev-mode", help=devmode_help, action="store_true")

log.debug(f"Setting up runtime variables for the {name} module")
ensure_runtime_dirs()

args = parser.parse_args()

if args.gui:
    import monopolpy_companion.lib.gui.run as app

    app.run()
else:
    print("Run with --gui to launch the MonopolPy Companion desktop shell.")

if args.conf_file:
    log.info(f"Custom config file requested: {args.conf_file}")
