"""Local reusable identities with authenticated, password-encrypted writes."""
import base64
import hashlib
import json
import os
import tempfile
from pathlib import Path
from uuid import uuid4

from .models import Player
from .security import PlayerAccount


class AccountStore:
    """Keep derived encryption keys in memory until this store is discarded."""

    def __init__(self, directory):
        self.directory = Path(directory)
        self._keys = {}

    def entries(self):
        if not self.directory.exists():
            return []
        return sorted([json.loads(p.read_text(encoding='utf-8'))
                       for p in self.directory.glob('*.json')], key=lambda a: a['username'].casefold())

    def available(self, username):
        username = username.strip()
        return bool(username) and ',' not in username and not any(
            a['username'].casefold() == username.casefold() for a in self.entries())

    @staticmethod
    def _key(password, salt):
        return hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)

    def create(self, username, password='', pin=''):
        username = username.strip()
        if not self.available(username):
            raise ValueError('Choose a unique, nonempty username without commas')
        player = Player(name=username)
        if pin:
            PlayerAccount(player).set_pin(pin)
        record = {'id': uuid4().hex, 'username': username, 'salt': '',
                  'data': {'pin_salt': player.pin_salt, 'pin_hash': player.pin_hash}}
        if password:
            salt = os.urandom(16)
            record['salt'] = salt.hex()
            self._keys[record['id']] = self._key(password, salt)
        self.write(record)
        return record

    def unlock(self, entry, password=None):
        if not entry['salt']:
            return dict(entry)
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        key = self._keys.get(entry['id'])
        if key is None:
            if password is None:
                raise PermissionError('Account password required')
            key = self._key(password, bytes.fromhex(entry['salt']))
        try:
            raw = base64.b64decode(entry['payload'])
            data = json.loads(AESGCM(key).decrypt(raw[:12], raw[12:],
                              (entry['id'] + entry['username']).encode()))
        except Exception as exc:
            raise PermissionError('Incorrect password or damaged account file') from exc
        self._keys[entry['id']] = key
        return {**entry, 'data': data}

    def write(self, record):
        output = dict(record)
        if record['salt']:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            key = self._keys.get(record['id'])
            if key is None:
                raise PermissionError('Unlock the account before writing')
            nonce = os.urandom(12)
            output['payload'] = base64.b64encode(nonce + AESGCM(key).encrypt(
                nonce, json.dumps(output.pop('data')).encode(),
                (record['id'] + record['username']).encode())).decode()
        self.directory.mkdir(parents=True, exist_ok=True)
        temp = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                    dir=self.directory, delete=False) as handle:
                temp = Path(handle.name)
                json.dump(output, handle)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self.directory / (record['id'] + '.json'))
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)
