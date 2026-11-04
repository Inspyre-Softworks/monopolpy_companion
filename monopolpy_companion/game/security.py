"""Per-player PIN authentication for a shared physical-game terminal.

PINs protect routine GUI actions from accidental or casual access. They are
not equivalent to encrypted storage: a person who can edit the save file can
also change game data or remove PIN credentials.
"""

from __future__ import annotations

import hashlib
import hmac
from secrets import token_bytes

from .models import Player


class PlayerAccount:
    """Facade for a player identity and its optional PIN credentials.

    Args:
        player: Session player whose hash and salt are persisted.

    Notes:
        No plaintext PIN is written to a save. New salt per set, PBKDF2-HMAC
        SHA-256, and constant-time comparison guard against casual guessing.
        SessionController implements in-memory unlock policy.
    """

    ITERATIONS = 240_000

    def __init__(self, player: Player) -> None:
        self.player = player

    @property
    def is_locked(self) -> bool:
        """Whether the account requires a PIN to authorize game actions."""
        return bool(self.player.pin_salt and self.player.pin_hash)

    def set_pin(self, pin: str) -> None:
        """Replace the PIN with a salted one-way hash.

        Args:
            pin: Four to eight decimal digits.

        Raises:
            ValueError: PIN does not meet the required format.
        """
        if not isinstance(pin, str) or not pin.isascii() or not pin.isdigit() or not 4 <= len(pin) <= 8:
            raise ValueError('PIN must contain 4 to 8 ASCII digits')
        salt = token_bytes(16)
        digest = hashlib.pbkdf2_hmac('sha256', pin.encode('ascii'), salt, self.ITERATIONS)
        self.player.pin_salt = salt.hex()
        self.player.pin_hash = digest.hex()

    def verify_pin(self, pin: str) -> bool:
        """Verify a PIN without exposing its stored digest."""
        if not self.is_locked or not isinstance(pin, str):
            return False
        try:
            salt = bytes.fromhex(self.player.pin_salt)
            expected = bytes.fromhex(self.player.pin_hash)
            actual = hashlib.pbkdf2_hmac('sha256', pin.encode('utf-8'), salt, self.ITERATIONS)
            return hmac.compare_digest(actual, expected)
        except (ValueError, UnicodeError):
            return False

    def clear_pin(self) -> None:
        """Remove PIN credentials after authorization by the controller."""
        self.player.pin_salt = ''
        self.player.pin_hash = ''
