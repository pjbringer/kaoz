# -*- coding: utf-8 -*-
# Copyright © 2011-2013 Binet Réseau
# See the LICENCE file for more informations

import os
import os.path
import tempfile
from time import sleep
import shutil
import sys

from .common import unittest, get_local_conf
import kaoz.hooks
from threading import Lock

class HooksTestCase(unittest.TestCase):

    def setUp(self):
        self.config = get_local_conf()
        self.tmp_dir_name = tempfile.mkdtemp()
        self.dummy = os.path.join(self.tmp_dir_name, 'dummy.py')
        with open(self.dummy, 'w') as f:
            f.write("def pubmsg(publisher, connection, event):\n    publisher.send('#dummy', 'dummy pubmsg(%s, %s)' % (str(connection), str(event)))\n")
        self.dolly = os.path.join(self.tmp_dir_name, 'dolly.sh')
        with open(self.dolly, 'w') as f:
            f.write("def pubmsg(publisher, connection, event):\n    print('dolly pubmsg')\n")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir_name)

    def test_config(self):
        self.assertTrue(self.config is not None)
        self.assertTrue(self.config.get('irc', 'hook_directory') is not None)
        self.assertTrue(self.config.get('irc', 'hook_directory') == '')

    def test_load_hook_empty(self):
        self.config.set('irc', 'hook_directory', '')
        hooks = kaoz.hooks.Hooks(self.config)
        hooks.load_hook_modules()
        self.assertFalse('dummy' in sys.modules)
        self.assertFalse('dolly' in sys.modules)

    def test_load_hook_modules(self):
        self.config.set('irc', 'hook_directory', self.tmp_dir_name)
        hooks = kaoz.hooks.Hooks(self.config)
        hooks.load_hook_modules()
        self.assertTrue('dummy' in sys.modules)
        self.assertFalse('dolly' in sys.modules)

    def test_pubmsg(self):
        class MockPublisher(object):
            def __init__(self):
                self.calls=0
                self.valid=False
                self.lock = Lock();
            def send(self, channel, message):
                with self.lock:
                    self.calls += 1
                    self.valid = channel == '#dummy' and message == 'dummy pubmsg(None, None)'
        self.config.set('irc', 'hook_directory', self.tmp_dir_name)
        hooks = kaoz.hooks.Hooks(self.config)
        hooks.load_hook_modules()
        publisher = MockPublisher()
        pubm = hooks.pubmsg(publisher, None, None)
        privm= hooks.privmsg(publisher, None, None)
        self.assertTrue(pubm)
        self.assertFalse(privm);
        sleep(0.1) # Test is racy
        with publisher.lock:
            self.assertTrue(publisher.calls==1)
            self.assertTrue(publisher.valid)

