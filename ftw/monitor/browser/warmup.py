from ftw.monitor.interfaces import IWarmupPerformer
from ftw.monitor.warmup import instance_warmup_state
from Products.CMFPlone.interfaces import IPloneSiteRoot
from Products.Five.browser import BrowserView
from zope.component import getMultiAdapter
from zope.component.hooks import setSite
import logging
import transaction


log = logging.getLogger('ftw.monitor')


class WarmupView(BrowserView):
    """Warm up a single Plone site or all Plone sites in a Zope instance.
    """

    def __call__(self):
        instance_warmup_state['in_progress'] = True

        try:
            transaction.doom()
            log.info('Warming up instance...')
            result = self.warmup()

        finally:
            instance_warmup_state['in_progress'] = False
            instance_warmup_state['done'] = True

        log.info('Done warming up.')
        return result

    def warmup(self):
        if IPloneSiteRoot.providedBy(self.context):
            # Invoked on Plone Site
            self.warmup_plone(self.context)
        else:
            # Invoked on Zope Application root
            app = self.context
            for obj in app.objectValues():
                if IPloneSiteRoot.providedBy(obj):
                    setSite(obj)
                    self.warmup_plone(obj)
        return 'Warmup successful'

    def warmup_plone(self, site):
        warmup_performer = getMultiAdapter(
            (site, site.REQUEST), IWarmupPerformer)
        warmup_performer.perform()
