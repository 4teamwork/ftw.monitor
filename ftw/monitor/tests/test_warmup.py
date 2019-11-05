from Acquisition import aq_parent
from ftw.monitor.testing import MONITOR_INTEGRATION_TESTING
from ftw.testbrowser import browsing
from unittest2 import TestCase


class TestWarmup(TestCase):

    layer = MONITOR_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']

    @browsing
    def test_warmup_view_on_plone_site(self, browser):
        browser.open(self.portal, view='@@warmup')
        self.assertEqual('Warmup successful', browser.contents)

    @browsing
    def test_warmup_view_on_zope_app_root(self, browser):
        app = aq_parent(self.portal)
        browser.open(app, view='@@warmup')
        self.assertEqual('Warmup successful', browser.contents)
