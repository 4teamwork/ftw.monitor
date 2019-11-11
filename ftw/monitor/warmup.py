from ftw.monitor.interfaces import IWarmupPerformer
from plone import api
from Products.CMFPlone.interfaces import IPloneSiteRoot
from zope.component import adapter
from zope.interface import implementer
from zope.publisher.interfaces.browser import IBrowserRequest
import logging

log = logging.getLogger('ftw.monitor')

# Keep track of the instance's warmup state.
instance_warmup_state = {
    'in_progress': False,
}


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
