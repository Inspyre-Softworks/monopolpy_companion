opts_win_active = False
pm_win_active = False

nyi_active = False
pm_active = False


def get_obj_id_hex(obj):
    """
    Get the object id as a hex string.
    """
    return hex(obj)


#  Copyright (c) 2022. Inspyre-Softworks (https://softworks.inspyre.tech)

class Warden(object):
    def __init__(self):
        pass


class WindowWarden(Warden):
    def __init__(self):
        self.__windows = {}

    @property
    def windows(self):
        return self.__windows

    @windows.deleter
    def windows(self):
        self.__windows.clear()

    def register(self, name, register_as_active=False):
        self.__windows[name] = self.Window(name, register_as_active)
        return self.__windows[name]

    @property
    def number_registered(self):
        return len(self.__windows)

    @property
    def number_active(self):
        return sum(bool(self.windows[window].active) for window in self.windows)

    class Window(object):
        def __init__(self, name, window_object, register_as_active=False):
            self.__window = window_object
            if isinstance(name, str):
                self.__name = name
            else:
                raise TypeError(f"Parameter 'name' must be of type 'string' not {type(name)}!")

            self.__active = False

            if register_as_active:
                if isinstance(register_as_active, bool):
                    self.__active = True
                else:
                    raise TypeError(f"Parameter 'register_as_active' must have a value that is of type 'bool', not "
                                    f"{type(register_as_active)}")

        @property
        def name(self):
            return self.__name

        @property
        def active(self):
            return self.__active

        @active.setter
        def active(self, new):
            if isinstance(new, bool):
                self.__active = new
            else:
                raise TypeError(f"The new value for 'active' must be of type 'bool' not {type(new)}!")

        @property
        def window(self):
            return self.__window

        def __repr__(self):
            return f"WindowWarden.Window:{self.name} ({id(self)}) | Active: {self.active} |" \
                   f" Window Object: {self.window} ({id(self.window)})"

        def toggle_active(self):
            """
            Toggles the 'active' flag for the window.

            :func:`WindowWarden.Window.toggle_active` changes the current :class:`bool` value of the 'active' flag to
            it's opposite,

            Returns:
                :class:`bool`:
                    A boolean indicating whether the window's 'active' flag is set.
            """
            self.__active = not self.__active
            return self.active


class PopUpWarden(object):
    def __init__(self):
        self.__popups = {}

    def __gather(self):
        pass

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
        for name in self.__popups.keys():
            if self.__popups[name].active:
                acc += 1

        return acc

    def register(self, name, callback, register_as_active=False):
        if not isinstance(name, str):
            raise TypeError(f"Parameter 'name' must be of type 'str' not {type(name)}!")
        if not callable(callback):
            raise TypeError(f"Parameter 'callback' must be of type 'callable' not {type(callback)}!")

        if register_as_active and not isinstance(register_as_active, bool):
            raise TypeError(f"Parameter 'register_as_active' must be of type 'bool' not {type(register_as_active)}!")

        if name not in self.__popups.keys():
            self.__popups[name] = self.PopUp(name, callback, register_as_active)

    class PopUp(object):
        def __init__(self, name, callback, register_as_active=False):
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
