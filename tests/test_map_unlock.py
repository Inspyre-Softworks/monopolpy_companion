"""Resource and interaction tests for the Marauder's Map parchment dialogs."""

import unittest
from importlib.resources import files
from unittest.mock import Mock, patch

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QRawFont
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QDialog, QLabel, QLineEdit, QPushButton, QWidget
    from monopolpy_companion.ui import map_unlock
except ImportError:
    QApplication = None


@unittest.skipUnless(QApplication is not None, 'PySide6 GUI extra is not installed')
class MapUnlockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.application = QApplication.instance() or QApplication([])
        self.parent = QWidget()
        self.addCleanup(self.parent.close)
        self.addCleanup(map_unlock._font_family.cache_clear)

    def test_packaged_font_renders_inscription_and_unmasked_input(self) -> None:
        resources = files('monopolpy_companion.ui').joinpath('resources')
        for font in ('Caveat', 'SourceSans3'):
            self.assertTrue(resources.joinpath(font + '.ttf').is_file())
            self.assertIn('SIL OPEN FONT LICENSE',
                          resources.joinpath(font + '-OFL.txt').read_text(encoding='utf-8'))
        map_unlock._font_family.cache_clear()
        with patch.object(map_unlock.QFontDatabase, 'addApplicationFontFromData',
                          wraps=map_unlock.QFontDatabase.addApplicationFontFromData) as register:
            intro = map_unlock._introduction(self.parent)
            dialog, editor = map_unlock._phrase_entry(self.parent)
        self.assertEqual(register.call_count, 2)
        for font in ('Caveat', 'SourceSans3'):
            register.assert_any_call(resources.joinpath(font + '.ttf').read_bytes())
        intro.ensurePolished()
        dialog.ensurePolished()
        inscription = next(label for label in intro.findChildren(QLabel)
                           if label.text().startswith('Moony'))
        for widget in (inscription, editor):
            self.assertEqual(QRawFont.fromFont(widget.font()).familyName(), 'Caveat')

        proceed = next(button for button in intro.findChildren(QPushButton)
                       if button.text() == '&Continue')
        self.assertEqual(QRawFont.fromFont(proceed.font()).familyName(), 'Source Sans 3')
        proceed.click()
        self.assertEqual(intro.result(), QDialog.DialogCode.Accepted)
        editor.setText('I solemnly swear that I am up to no good.')
        self.assertEqual(editor.echoMode(), QLineEdit.EchoMode.Normal)
        self.assertEqual(editor.displayText(), editor.text())
        QTest.keyClick(editor, Qt.Key.Key_Return)
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)

    def test_missing_and_corrupt_fonts_warn_and_keep_input_visible(self) -> None:
        for missing in (True, False):
            with self.subTest(missing=missing):
                map_unlock._font_family.cache_clear()
                resource = Mock()
                reader = resource.joinpath.return_value.read_bytes
                if missing:
                    reader.side_effect = FileNotFoundError('Caveat.ttf')
                else:
                    reader.return_value = b'invalid font data'
                with patch.object(map_unlock, 'files', return_value=resource):
                    with self.assertLogs(map_unlock.__name__, level='WARNING'):
                        dialog, editor = map_unlock._phrase_entry(self.parent)
                dialog.ensurePolished()
                editor.setText('Still readable')
                self.assertEqual(editor.displayText(), 'Still readable')
                self.assertTrue(editor.font().italic())
                dialog.close()
