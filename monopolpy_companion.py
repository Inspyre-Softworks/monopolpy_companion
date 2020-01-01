import argparse

import lib.gui.run as app

parser = argparse.ArgumentParser(description='Start the Monopolpy Companion program', prog='monopolpy_companion')
gui_help = 'Start the program in graphical user interface mode, using PySimpleGUIQt (a port of tkinter).'

parser.add_argument('--gui', dest='gui', help=gui_help, required=False, default=False, action='store_true')

parser.add_argument('--dev-mode')

args = parser.parse_args()
print(args)

if args.gui:
    print(args.gui)

app.run()
