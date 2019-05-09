from ftw.monitor.interfaces import IWarmupPerformer
from plone import api
from Products.CMFPlone.interfaces import IPloneSiteRoot
from Products.Five.browser import BrowserView
from zope.component import adapter
from zope.component import getMultiAdapter
from zope.component.hooks import setSite
from zope.interface import implementer
from zope.publisher.interfaces.browser import IBrowserRequest
import logging
import transaction


log = logging.getLogger('ftw.monitor')

warmup_in_progress = False


@implementer(IWarmupPerformer)
@adapter(IPloneSiteRoot, IBrowserRequest)
class DefaultWarmupPerformer(object):
    """Load catalog BTrees and forward index BTrees of the most used indexes
    """

    WARMUP_INDEXES = [
        'allowedRolesAndUsers',
        'object_provides',
    ]

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def perform(self):

        def load_btree(node, level=0, maxlevel=2):
            if level >= maxlevel:
                return
            bucket = getattr(node, '_firstbucket', None)
            while bucket is not None:
                for key in bucket.keys():
                    load_btree(key, level + 1, maxlevel)
                if hasattr(bucket, 'values'):
                    for value in bucket.values():
                        load_btree(value, level + 1, maxlevel)
                bucket = bucket._next

        catalog = api.portal.get_tool('portal_catalog')
        load_btree(catalog._catalog.uids)
        load_btree(catalog._catalog.paths)
        load_btree(catalog._catalog.data)

        for index_name in self.WARMUP_INDEXES:
            index = catalog._catalog.indexes.get(index_name)
            if index is None:
                log.warn('Index %r not found, skipping' % index_name)
                continue
            load_btree(index._index)


class WarmupView(BrowserView):
    """Warm up a single Plone site or all Plone sites in a Zope instance.
    """

    def __call__(self):
        global warmup_in_progress
        warmup_in_progress = True

        try:
            transaction.doom()
            log.info('Warming up instance...')
            result = self.warmup()

        finally:
            warmup_in_progress = False

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
        return 'OK'

    def warmup_plone(self, site):
        warmup_performer = getMultiAdapter(
            (site, site.REQUEST), IWarmupPerformer)
        warmup_performer.perform()
