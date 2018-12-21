
from ftw.monitor.testing import MONITOR_INTEGRATION_TESTING
from ftw.testbrowser import browsing
from unittest2 import TestCase


class TestWarmup(TestCase):

    layer = MONITOR_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']

    @browsing
    def test_warmup_view_returns_ok(self, browser):
        browser.open(view='@@warmup')
        self.assertEqual('OK', browser.contents)
