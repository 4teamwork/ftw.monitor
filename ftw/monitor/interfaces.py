from zope.interface import Interface


class IFtwMonitorLayer(Interface):
    """Request layer for ftw.monitor"""


class IWarmupPerformer(Interface):
    """Performs the necessary actions to warm up a Plone site.
    """

    def __init__(context, request):
        """Adapts context and request, context is usually a Plone site"""

    def perform():
        """Perform the warmup.
        """
