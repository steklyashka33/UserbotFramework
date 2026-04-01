from telethon import TelegramClient
from telethon import utils, helpers, errors, password as pwd_mod
from pathlib import Path

# MVP Adaptation: The library no longer depends on the database and receives data via arguments.
import inspect
import sys
import warnings
import typing
import getpass
import logging

# Return the silencer for spam logs (they are only scary, but we already figured it out)
logging.getLogger('telethon').setLevel(logging.CRITICAL)

# Add MVP root to sys.path to import 'shared'
BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# We keep the IDENTICAL name and structure of the class from the original project
class TelegramClientForBot(TelegramClient):

    def start(
            self: 'TelegramClient',
            phone: str = None,
            code: str = None,
            password: str = None,
            phone_code_hash=None,
            *,
            bot_token: str = None) -> 'TelegramClient':
        """
        Starts the client (connects and logs in if necessary).
        
        Original Docstring preserved.
        """
        if not type(code) is str:
            raise ValueError(
                'The code parameter needs to be a str '
                'the code you received by Telegram.'
            )

        if not phone and not bot_token:
            raise ValueError('No phone number or bot token provided.')

        if phone and bot_token and not callable(phone):
            raise ValueError('Both a phone and a bot token provided, '
                             'must only provide one of either')

        coro = self._start(
            phone=phone,
            code=code,
            password=password,
            phone_code_hash=phone_code_hash,
            bot_token=bot_token
        )
        return (
            coro if self.loop.is_running()
            else self.loop.run_until_complete(coro)
        )
    
    async def _start(
            self: 'TelegramClient', phone, password, bot_token, code, phone_code_hash):
        if not self.is_connected():
            await self.connect()

        me = await self.get_me()
        if me is not None:
            if bot_token:
                if bot_token[:bot_token.find(':')] != str(me.id):
                    warnings.warn(
                        'the session already had an authorized user so it did '
                        'not login to the bot account using the provided '
                        'bot_token (it may not be using the user you expect)'
                    )
            elif phone and not callable(phone) and utils.parse_phone(phone) != me.phone:
                warnings.warn(
                    'the session already had an authorized user so it did '
                    'not login to the user account using the provided '
                    'phone (it may not be using the user you expect)'
                )

            return self

        # MVP Adaptation: Get phone_code_hash from arguments, not from the DB
        # phone_code_hash = await db.account.get_phone_hash(phone)

        if bot_token:
            await self.sign_in(bot_token=bot_token, phone_code_hash=phone_code_hash)
            return self

        me = None
        two_step_detected = False

        # await self.send_code_request(phone, force_sms=force_sms)
        try:
            if not code:
                raise errors.PhoneCodeEmptyError(request=None)

            me = await self.sign_in(phone, code=code, phone_code_hash=phone_code_hash)
        except errors.SessionPasswordNeededError:
            two_step_detected = True

        if two_step_detected:
            try:
                if not password:
                    raise errors.SessionPasswordNeededError(
                        "Two-step verification is enabled for this account. "
                        "Please provide the 'password' argument to 'start()'."
                    )

                me = await self.sign_in(phone=phone, password=password)
            except errors.PasswordHashInvalidError:
                raise errors.PasswordHashInvalidError(request=None)

        return self
