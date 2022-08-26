import logging

name = 'PlayerManager'


def gather(caller_name=None, player_db=None):
    global name
    chained_name = caller_name + '.' + name
    log = logging.getLogger(caller_name + '.gather()')
    log.debug('Gathering player information...')
    log.debug('Checking for player db file')