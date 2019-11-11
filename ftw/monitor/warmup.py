from ftw.monitor.interfaces import IWarmupPerformer
from plone import api
from Products.CMFPlone.interfaces import IPloneSiteRoot
from zope.component import adapter
from zope.interface import implementer
from zope.publisher.interfaces.browser import IBrowserRequest
import logging

log = logging.getLogger('ftw.monitor')

# Keep track of the instance's warmup state.
#
# These two flags are not "thread-safe" in the sense that they are global,
# interpreter-wide state. For Zope instances with more than one thread they
# therefore don't track state accurately: If warmup happens in multiple
# threads, the first thread that finishes will set the flags to the "done"
# state, even though other threads are still warming up.

instance_warmup_state = {
    'done': False,
    'in_progress': False,
}


def warmup_state(connection):
    r"""Get instance warmup state.

    IZ3MonitorPlugin to report the warmup state of the instance in a machine
    readable form.

    Usage: Send the message 'warmup_state\r\n' to the zc.monitor TCP port.
    The plugin will then respond with a single line containing two
    space-delimited integers:

    - done (whether a warmup has been performed at least once)
    - in_progress (whether a warmup is currently being performed)
    """
    state = "%s %s\n" % (
        int(instance_warmup_state['done']),
        int(instance_warmup_state['in_progress']))
    connection.write(state)


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
