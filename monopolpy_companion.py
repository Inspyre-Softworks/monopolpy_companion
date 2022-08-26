import argparse

from monopolpy_companion.lib.helpers import logger

# Name the module and set up logging for the program
name = 'MonopolPyCompanion'
log = logger.start(name, 'debug')

log.debug(f'Setting up argument parsing for {name}')
parser = argparse.ArgumentParser(description='Start the Monopolpy Companion program', prog='monopolpy_companion')

# Introduce argument that allows end-user to specify a custom/imported configuration file.
conffile_help = 'Specify (using the absolute path) where the config file that you want to import is located'\
                'unless you\'ve placed your custom configuration file in PROG/conf. **MUST BE IN YAML FORMAT!**'
parser.add_argument('--conf-file', action="store", dest='conf_file')

# Introduce the help printer and argument for the --gui flag
gui_help = 'Start the program in graphical user interface mode, using PySimpleGUIQt (a port of tkinter).'
parser.add_argument('--gui', dest='gui', help=gui_help, required=False, default=None, action='store_true')

# Introduce the --dev-mode argument
# TODO:
#  1. Tell more about the --dev-mode argument
#  2. Add real functionality to this (and other) flags
devmode_help = 'Start the program in \'Developer Mode\' which turns off internet connectivity checks, enables DEBUG'\
               'logging mode, '
parser.add_argument('--dev-mode')

log.debug(f'Setting up runtime variables for the {name} module')




args = parser.parse_args()
print(args)

if args.gui:
    import monopolpy_companion.lib.gui.run as app
    app.run()
else:
    print('You didn\'t specify that you wanted the GUI active.')

if args.conf_file:
    print('found it')
