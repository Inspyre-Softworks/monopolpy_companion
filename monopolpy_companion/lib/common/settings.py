class Config:
    import logging
    import inspect

    FRAME_FILENAME = 1
    print("Imported from: ", inspect.getouterframes(inspect.currentframe())[-1][FRAME_FILENAME])

    def load(self, file=None):
        import logging
        import os
        import yaml

        name = 'MonopolpyCompanion.' + str(__name__)
        log = logging.getLogger(name)
        log.info(f'Logger started for {name}')

        if file is None:
            log.debug('A custom config file was not provided!')
            file = os.getcwd() + '/conf/default.yml'

        with open(file) as res:
            loaded = yaml.load(res, Loader=yaml.SafeLoader)
            data = loaded

        if data['gui_settings']['grab_anywhere'] is None:
            print('found a problem')
            data['gui_settings']['grab_anywhere'] = False

        return data

    def __init__(self, file=None):
        import yaml
        print(self.__class__)
        self.data = self.load

    def write(self, file=None):
        import yaml

        if file is None:
            import os
            print('file not found')
            file = os.getcwd() + '/conf/default.yml'

        with open(file, 'w') as outfile:
            yaml.dump(self.data, outfile, default_flow_style=False)


if __name__ == '__main__':
    print('That\'s not how you use this')
    exit()
