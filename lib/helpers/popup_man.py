#!/usr/bin/env python3
popup_active = False


def nyi(feat_name):
    global popup_active
    import logging
    from lib.gui.run import NotYetImplementedError

    name = 'MonopolPyCompanion.NotYetImplementedErrorManager'
    log = logging.getLogger(name)

    if not popup_active:
        popup_active = True

        try:
            log.warning('We haven\'t gotten there yet')

            raise NotYetImplementedError(f'{feat_name} is not a feature that has been implemented')
        except NotYetImplementedError as e:
            from lib.gui.models.popups.alerts import not_yet_implemented

            not_yet_implemented(e.message)
            popup_active = False
            log.warning(e.message)

    else:
        log.warning(f'Received another call to not yet implemented feature: {feat_name}')
        log.info('Suppressing Popup')
