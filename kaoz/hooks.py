# -*- coding: utf-8 -*-
# Copyright © 2011-2013 Binet Réseau
# See the LICENCE file for more informations

from imp import reload
import logging
from os import listdir, walk
from os.path import isfile, join, isdir
from threading import Thread, RLock
import traceback
import signal
import sys

logger = logging.getLogger(__name__)

class Hooks(object):
    """A hook-based extension system

    This class forwards function calls to modules found in a directory. The
    directory is passed in the configuration at Hooks object creation time.
    The extension modules are loaded with the load_hook_modules method."""
    def __init__(self, config):
        self.directory = config.get('irc', 'hook_directory')
        if (self.directory):
            sys.path.append(self.directory);
        self._lock = RLock()
        self.modules = set()
        signal.signal(signal.SIGUSR1, self.reload)

    def reload(self, signum, stack_frame):
        logger.info("Caught hook reload signal: %s", self.directory)
        assert signum==signal.SIGUSR1
        with self._lock:
            self.modules = set()
            self.load_hook_modules()
        logger.info('Done')

    def load_hook_modules(self):
        """Loads any module in the hooks directory as hook handlers"""
        if not self.directory:
            return
        if not isdir(self.directory):
            logger.error("Hooks directory is not a directory: %s" %
                str(self.directory))
            return
        with self._lock:
            for dir in walk(self.directory):
                for filename in dir[2]:
                    if filename.endswith('.py'):
                        module = filename[:-3]
                        self.modules.add(module)
                    else:
                        logger.info("Ignoring %s" % filename)
            for m in self.modules:
                try:
                    if m in sys.modules:
                        logger.info("Reloading %s" % m)
                        reload(sys.modules[m])
                    else:
                        logger.info("Loading %s" % m)
                        __import__(m)
                except:
                    logger.error("Could not load hook: %s" % m)

    def _multiplex_method(self, method_name, *args, **kwargs):
        """Calls method_name on all modules that have it.

        Returns True iff at least one module handles the event"""
        def call_method(mod, *args, **kwargs):
            try:
                method = getattr(mod, method_name)
                method(*args, **kwargs)
            except Exception:
                logger.error("Error while running %s on hook: %s" % (str(method_name), str(mod)))
                error_msg = traceback.format_exc()
                quote_line = lambda x: '> ' + x
                logger.error('\n'.join(map(quote_line, error_msg.split('\n'))))

        ans = False
        with self._lock:
            for m in self.modules:
                mod = sys.modules[m]
                if hasattr(mod, method_name):
                    ans = True
                    Thread(None, call_method, None, (mod,)+args, kwargs).start()
        return ans

    # API methods: methods bollow this line are meant to be forwarded to the extensions 

    def join(self, publisher, connection, event):
        return self._multiplex_method("join", publisher, connection, event)

    def privmsg(self, publisher, connection, event):
        return self._multiplex_method("privmsg", publisher, connection, event)

    def pubmsg(self, publisher, connection, event):
        return self._multiplex_method("pubmsg", publisher, connection, event)

