opts_win_active = False
pm_win_active = False

nyi_active = False
pm_active = False


class ActiveWindows(object):
    def __init__(self):
        self.__options_win = False
        self.__player_man_win = False


class ActivePopUps(object):
    def __init__(self):
        self.__popups = {}

    @property
    def popups(self):
        return self.__popups

    @popups.deleter
    def popups(self):
        self.__popups.clear()

    @property
    def number_registered(self):
        return len(self.__popups)

    @property
    def number_active(self):
        acc = 0
        for popup in self.__popups:
            if popup.active:
                acc += 1

        return acc

    def register(self, name):
        self.__popups[name] = self.PopUp(name)

    class PopUp(object):
        def __init__(self, name, register_as_active=False):
            self.__name = name

            if not isinstance(register_as_active, bool):
                raise TypeError(f'Argument "register_as_active" must be a boolean not "{type(register_as_active)}"!')

            self.__active = register_as_active

        @property
        def name(self):
            return self.__name

        @property
        def active(self):
            return self.__active

        @active.setter
        def active(self, new_value):
            if not isinstance(new_value, bool):
                raise TypeError('Invalid new value for the active property.')
            self.__active = new_value

        def toggle_active(self):
            self.__active = not self.__active
