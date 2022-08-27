#  Copyright (c) 2022. Inspyre-Softworks (https://softworks.inspyre.tech)

from pathlib import Path


class Config:
    import inspect

    FRAME_FILENAME = 1
    print("Imported from: ", inspect.getouterframes(inspect.currentframe())[-1][FRAME_FILENAME])

    def load(self, file=None):
        import logging
        import yaml
        name = f'MonopolpyCompanion.{str(__name__)}'
        log = logging.getLogger(name)
        log.info(f'Logger started for {name}')
        if file is None:
            log.debug('A custom config file was not provided!')
            file = Path('monopolpy_companion/lib/common/default.yml').resolve()
        with open(file) as res:
            loaded = yaml.load(res, Loader=yaml.SafeLoader)
            data = loaded
        if data['gui_settings']['grab_anywhere'] is None:
            print('found a problem')
            data['gui_settings']['grab_anywhere'] = False
        return data

    def __init__(self, file=None):
        print(self.__class__)
        self.data = self.load

    def write(self, file=None):
        import yaml
        if file is None:
            import os
            print('file not found')
            file = f'{os.getcwd()}/conf/default.yml'
        with open(file, 'w') as outfile:
            yaml.dump(self.data, outfile, default_flow_style=False)


if __name__ == '__main__':
    print('That\'s not how you use this')
    exit()
