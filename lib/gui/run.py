from lib.gui import gui as gui


def run():
    from lib.gui.windows.application import app_window as mainWin
    app_win = mainWin

    while True:
        event, vals = app_win.Read(timeout=100)
        if event is None or event == 'exit_button_main_application':
            print('user exited')
            app_win.Close()
            exit()

        if not gui.options_win_active and event == 'options_main_button':
            gui.options_win_active = True
            print('user entered options window')

        if gui.options_win_active:
            opt_event, opt_val = gui.options_win.Read(timeout=100)
            if opt_event is None or opt_event == 'OK':
                print('User exited the options window')
                gui.options_win_active = False
                gui.options_win.Close()
