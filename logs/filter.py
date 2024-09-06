import logging

from logs.logger import file_handler, console_handler


class ContextualFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        self.ip = '-'

    def filter(self, record):
        record.ip = self.ip
        return True


contextual_filter = ContextualFilter()

file_handler.addFilter(contextual_filter)
console_handler.addFilter(contextual_filter)
