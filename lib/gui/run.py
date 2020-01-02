from lib.gui.gui import win


def run():

    while True:
        event, vals = win.app_win.Read(timeout=100)
        if event is None or event == 'exit_button_main_application':
            print('user exited')
            win.app_win.Close()
            exit()

        if not win.opts_win_active and event == 'options_main_button':
            win.opts_win_active = True
            print('user entered options window')

        if win.opts_win_active:
            opt_event, opt_val = win.opts_win.Read(timeout=100)
            if opt_event is None or opt_event == 'OK':
                print('User exited the options window')
                win.opts_win_active = False
                win.opts_win.Close()
