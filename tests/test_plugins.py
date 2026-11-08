import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from importlib.metadata import EntryPoint
from unittest.mock import Mock, patch

from monopolpy_companion.controller import SessionController
from monopolpy_companion.plugins import ENTRY_POINT_GROUP, PluginManager, PluginMetadata


class Probe:
    metadata = PluginMetadata('Probe', 1, 1)
    events = []
    fail = False

    def start(self, context):
        context.subscribe(self.events.append)
        if context.has_ui:
            context.add_action('Probe', lambda: None)
        if self.fail:
            raise RuntimeError('startup failure')

    def stop(self):
        pass


class PluginTests(unittest.TestCase):
    def setUp(self):
        Probe.events.clear()
        self.controller = SessionController(logger=Mock(), autosave=False)
        self.entry = EntryPoint('probe', f'{__name__}:Probe', ENTRY_POINT_GROUP)

    def test_entry_point_lifecycle(self):
        manager = PluginManager(self.controller, [self.entry])
        self.assertTrue(manager.enable('probe'))
        self.assertTrue(manager.enable('probe'))
        self.controller.set_session(self.controller_session())
        self.assertEqual([event.name for event in Probe.events], ['session_changed'])
        manager.close()
        self.controller.set_session(self.controller_session())
        self.assertEqual(len(Probe.events), 1)

    def test_conflicts_and_incompatible_plugins(self):
        manager = PluginManager(self.controller, [self.entry, self.entry])
        self.assertFalse(manager.enable('probe'))
        self.assertIn('same identifier', manager.errors['probe'])
        with patch.object(Probe, 'metadata', PluginMetadata('Probe', 2, 3)):
            manager = PluginManager(self.controller, [self.entry])
            self.assertFalse(manager.enable('probe'))
            self.assertIn('outside supported range', manager.errors['probe'])

    def test_failed_start_removes_registrations(self):
        remove = Mock()
        register = Mock(return_value=remove)
        manager = PluginManager(self.controller, [self.entry], register)
        with patch.object(Probe, 'fail', True):
            self.assertFalse(manager.enable('probe'))
        remove.assert_called_once_with()
        self.controller.set_session(self.controller_session())
        self.assertEqual(Probe.events, [])
        self.assertEqual(manager.errors['probe'], 'startup failure')

    def test_discovery_reads_distribution_registration(self):
        with TemporaryDirectory() as directory:
            metadata = Path(directory) / 'plugin_probe-1.0.dist-info'
            metadata.mkdir()
            (metadata / 'entry_points.txt').write_text(
                f'[{ENTRY_POINT_GROUP}]\nprobe = {__name__}:Probe\n',
                encoding='utf-8',
            )
            with patch.object(sys, 'path', [directory, *sys.path]):
                manager = PluginManager(self.controller)
                self.assertTrue(manager.enable('probe'))
                manager.close()

    def test_snapshot_is_detached_and_excludes_pin_credentials(self):
        snapshots = []

        class SnapshotProbe(Probe):
            def start(self, context):
                snapshots.append(context.current_game())

        session = self.controller_session()
        session.players[0].pin_hash = 'secret'
        session.players[0].pin_salt = 'salt'
        self.controller.set_session(session)
        entry = Mock(name='entry point')
        entry.name = 'snapshot'
        entry.load.return_value = SnapshotProbe
        manager = PluginManager(self.controller, [entry])
        self.assertTrue(manager.enable('snapshot'))
        manager.close()
        player = snapshots[0]['players'][0]
        self.assertNotIn('pin_hash', player)
        self.assertNotIn('pin_salt', player)
        player['name'] = 'Changed'
        self.assertEqual(session.players[0].name, 'Alice')

    @staticmethod
    def controller_session():
        from monopolpy_companion import create_standard_session

        return create_standard_session('Plugin test', ['Alice', 'Bob'])
