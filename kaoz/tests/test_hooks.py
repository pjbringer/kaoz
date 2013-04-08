# -*- coding: utf-8 -*-
# Copyright © 2011-2013 Binet Réseau
# See the LICENCE file for more informations

import os
import os.path
import tempfile
from time import sleep
import shutil
import signal
import sys

from .common import unittest, get_local_conf
import kaoz.hooks
from threading import Lock

class HooksTestCase(unittest.TestCase):

    def setUp(self):
        self.config = get_local_conf()

    def tearDown(self):
        pass

    def test_config(self):
        """Test default configuration"""
        self.assertTrue(self.config is not None)
        self.assertTrue(self.config.get('irc', 'hook_directory') is not None)
        self.assertEqual(self.config.get('irc', 'hook_directory') , '')

    def test_load_hook(self):
        """Test loading modules in directory, recursively"""
        class MockPublisher(object):
            def __init__(self):
                self.calls=0
                self.valid=False
                self.lock = Lock();
            def send(self, channel, message):
                with self.lock:
                    self.calls += 1
                    self.valid = (channel == '#hook1') and \
                        (message == 'hook1 pubmsg(_, None, None)' or \
                        message == 'hook1 privmsg(_, None, None)')
        # setUp
        tmp_dir_name = tempfile.mkdtemp()
        self.assertEqual(self.config.get('irc', 'hook_directory'), '')
        self.config.set('irc', 'hook_directory', tmp_dir_name)
        os.mkdir(os.path.join(tmp_dir_name, 'more'))
        hook1 = os.path.join(tmp_dir_name, 'hook1.py')
        hook2 = os.path.join(tmp_dir_name, 'hook2.pyc')
        hook3 = os.path.join(tmp_dir_name, 'hook3.sh')
        hook4 = os.path.join(tmp_dir_name, 'hook4.py')
        hook5 = os.path.join(tmp_dir_name, 'hook5.py')
        hook6 = os.path.join(tmp_dir_name, 'more', 'hook6.py')
        with open(hook1, 'w') as f:
            f.write('''
def pubmsg(publisher, connection, event):
    publisher.send('#hook1', 'hook1 pubmsg(_, %s, %s)' % (str(connection), str(event)))
''')
        with open(hook2, 'w') as f:
            f.write('''
#Not really a pyc
def pubmsg(publisher, connection, event):
    publisher.send('oops!')
''')
        with open(hook3, 'w') as f:
            f.write('''
#!/bin/sh
echo 'Fail!'
''')
        with open(hook4, 'w') as f:
            f.write('''
def pubmsg(publisher, connection, event):
    publisher.send('#hook4', str(1/0))
''')
        with open(hook5, 'w') as f:
            f.write('''
def pubmsg(publisher, connection, event):
    publisher.send('#hook5', 'syntax...
''')
        with open(hook6, 'w') as f:
            f.write('''
def pubmsg(publisher, connection, event):
    publisher.send('#hook6', 'oops!')
''')

        self.assertTrue('hook1' not in sys.modules)
        self.assertTrue('hook4' not in sys.modules)
        hooks = kaoz.hooks.Hooks(self.config)
        hooks.load_hook_modules()
        self.assertTrue('hook1' in sys.modules)
        self.assertTrue('hook2' not in sys.modules)
        self.assertTrue('hook3' not in sys.modules)
        self.assertTrue('hook4' in sys.modules)
        self.assertTrue('hook4' in hooks.modules)
        self.assertTrue('hook5' not in sys.modules)
        self.assertTrue('hook6' not in sys.modules)
        publisher = MockPublisher()
        pmret = hooks.pubmsg(publisher, None, None)
        self.assertTrue(pmret)
        pmret = hooks.privmsg(publisher, None, None)
        self.assertFalse(pmret)
        sleep(0.1) # Test is racy
        with publisher.lock:
            self.assertEqual(publisher.calls, 1)
            self.assertTrue(publisher.valid)

        # Add privmsg to one hook and reload
        with open(hook1, 'a') as f:
            f.write('''
def privmsg(publisher, connection, event):
    publisher.send('#hook1', 'hook1 privmsg(_, %s, %s)' % (str(connection), str(event)))
''')
        os.remove(hook4)
        os.kill(os.getpid(), signal.SIGUSR1)

        self.assertTrue('hook1' in sys.modules)
        self.assertTrue('hook2' not in sys.modules)
        self.assertTrue('hook3' not in sys.modules)
        # TODO; forcefully unloading a module is not strictly needed
        #self.assertTrue('hook4' not in sys.modules)
        self.assertTrue('hook4' not in hooks.modules)
        self.assertTrue('hook5' not in sys.modules)
        self.assertTrue('hook6' not in sys.modules)
        publisher = MockPublisher()
        pmret = hooks.pubmsg(publisher, None, None)
        self.assertTrue(pmret)
        pmret = hooks.privmsg(publisher, None, None)
        self.assertTrue(pmret)
        sleep(0.1) # Test is racy
        with publisher.lock:
            self.assertEqual(publisher.calls, 2)
            self.assertTrue(publisher.valid)

        # tearDown
        shutil.rmtree(tmp_dir_name)
        del sys.modules['hook1']
        del hook1
        # TODO; see above
        del sys.modules['hook4']
        del hook4

