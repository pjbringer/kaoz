# -*- coding: utf-8 -*-
# Copyright © 2011-2013 Binet Réseau
# See the LICENCE file for more informations

import logging
import sys
from os import listdir, walk
from os.path import isfile, join, isdir
from threading import Thread

logger = logging.getLogger(__name__)

class Hooks(object):
    """A hook-based extension system

    This class forwards function calls to modules found in a directory. The
    directory is passed in the configuration at Hooks object creation time.
    The extension modules are loaded with the load_hook_modules method."""
    def __init__(self, config):
        self.directory = config.get('hooks', 'directory')
        sys.path.append(self.directory);
        self.modules = []

    def load_hook_modules(self):
        """Loads any module in the hooks directory as hook handlers"""
        if not self.directory:
            return
        if not isdir(self.directory):
            logger.error("Hooks directory is not a directory: %s" % str(self.directory))
            return
        for x in walk(self.directory):
            for filename in x[2]:
                if filename.endswith('.py'):
                    module = filename[:-3]
                    self.modules.append(module)
                else:
                    logger.info("Ignoring %s" % filename)
        for m in self.modules:
            try:
                logger.info("Loading %s" % m)
                __import__(m)
            except ImportError:
                logger.error("Could not load hook: %s" % m)

    def _multiplex_method(self, method_name, *args, **kwargs):
        """Calls method_name on all modules that have it.

        Returns True iff at least one module handles the event"""
        def call_method(mod, *args, **kwargs):
            try:
                method = getattr(mod, method_name)
                method(*args, **kwargs)
            except Exception as e:
                logger.error("Error while running pubmsg on hook: %s" % str(mod))
                logger.error(str(e))

        ans = False
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

