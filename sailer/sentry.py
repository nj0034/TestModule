import logging

from raven import Client, setup_logging
from raven.handlers.logging import SentryHandler


class SailerLogger:
    def __init__(self) -> None:
        self.client = Client(
            'https://b10ac0af34f347f790e3f27baff102db:66392f3e04204a24bb19a31df9608bc1@sentry.io/244780')

    def info(self, message):
        self.client.captureMessage(message, level='info')

    def error(self, message):
        self.client.captureMessage(message, level='error')

    @property
    def sentry(self):
        return self.client
