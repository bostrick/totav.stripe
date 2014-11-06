
from datetime import datetime
import json

# stripe API
import stripe

import transaction
from plone import api

from Acquisition import aq_base
from Acquisition import aq_inner
from Acquisition import aq_parent

from five import grok

from plone.autoform.interfaces import IFormFieldProvider
from plone.autoform import directives as form
from plone.dexterity.interfaces import IDexterityContent
from plone.supermodel import model

from plone.app.layout.viewlets.interfaces import IBelowContentBody
from plone.app.layout.viewlets.interfaces import IBelowContent

from zope import schema
from zope.component import adapts
from zope.interface import alsoProvides, implements
from zope.interface import Interface
from zope.container.interfaces import INameChooser

from zope.lifecycleevent.interfaces import IObjectAddedEvent
from zope.lifecycleevent.interfaces import IObjectRemovedEvent
from zope.lifecycleevent.interfaces import IObjectModifiedEvent

from totav.stripe import MessageFactory as _

from totav.stripe.interfaces import IStripeProxy
from totav.stripe.interfaces import IStripeProxyManager

#######################################################################
#
# Stripe Poxy Behavior
#
#######################################################################


class IStripeProxyBehavior(model.Schema):

    """IStripeProxyBehavior: used to define common attributes
       
    """

    stripe_id = schema.TextLine(
        title = u"Stripe Id",
        required = False,
    )

    stripe_last_update = schema.Datetime(
        title = u"Last Stripe Update",
        required = False,
    )

    stripe_data = schema.Text (
        title = u"Stripe Data",
        required = False,
    )

    stripe_status = schema._field.Choice(
        ( u'unknown', u'clean', u'dirty', u'missing', ),
        title=_(u"Stripe Proxy Status"),
        default=u"unknown",
        required = False,
    )

    model.fieldset(
        'stripe',
        label=_(u"Stripe"),
        fields=[
            'stripe_id', 'stripe_data', 'stripe_status', 
            'stripe_last_update', 
        ], 
    )

alsoProvides(IStripeProxyBehavior, IFormFieldProvider)

def context_property(name):
    def getter(self):
        return getattr(self.context, name)
    def setter(self, value):
        setattr(self.context, name, value)
    def deleter(self):
        delattr(self.context, name)
    return property(getter, setter, deleter)


class StripeProxyBehavior(object):
    """
       Adapter for Stripe Proxy
    """

    def __init__(self,context):
        self.context = context

    stripe_id = context_property('stripe_id')
    stripe_last_update = context_property('stripe_last_update')
    stripe_data = context_property('stripe_data')
    stripe_status = context_property('stripe_status')

############################################################################
#
# Stipe Proxy Manager: manager for IStripeProxy marker class
#
############################################################################

@grok.subscribe(IStripeProxy, IObjectAddedEvent)
def add_proxy(item, event): 
    print "add %s event" % item
    IStripeProxyManager(item).handle_add()

@grok.subscribe(IStripeProxy, IObjectRemovedEvent)
def remove_proxy(item, event): 
    print "remove %s event" % item
    IStripeProxyManager(item).handle_remove()

@grok.subscribe(IStripeProxy, IObjectModifiedEvent)
def modify_proxy(item, event): 
    print "modify %s event" % item
    IStripeProxyManager(item).handle_modify()


from transaction.interfaces import IDataManager
from uuid import uuid4

class FinishOnlyDataManager(object):

    implements(IDataManager)

    def __init__(self, callback, args=None, kwargs=None): 

        self.cb = callback
        self.args = [] if args is None else args
        self.kwargs = {} if kwargs is None else kwargs

        self.transaction_manager = transaction.manager
        self.key = str(uuid4())

    def sortKey(self): return self.key
    abort = commit = tpc_begin = tpc_vote = tpc_abort = lambda x,y: None

    def tpc_finish(self, tx): 

        # transaction.interfaces implies that exceptions are 
        # a bad thing.  assuming non-dire repercussions, and that
        # we're not dealing with remote (non-zodb) objects,  
        # swallow exceptions.

        try:
            self.cb(*self.args, **self.kwargs)
        except Exception, e:
            pass


class DataFilter(object):

    def __call__(self, data, filter_map):

        for k,v in filter_map.items():

            try:
                stub_key, base = self._resolve_key_base(data, k)
                f = getattr(self, v)
                base[stub_key] = f(data, k, base[stub_key])
            except KeyError, e:
                pass

        return data
            
    def _resolve_key_base(self, data, key):

        parts = key.split(".")
        current = data

        while parts:

            if len(parts) == 1:

                if parts[0] in current:
                    return parts[0], current

                raise KeyError("could not resolve key %s" % key)

            next_key = parts.pop(0)
            current = current.get(next_key, None)
            if not isinstance(current, dict):
                raise KeyError("could not resolve key %s" % key)

        raise KeyError("could not resolve key %s" % key)

    def cents_to_us_dollar(self, data, key, value):
        return "$%.02f" % (float(value)/100.0)

    def timestamp_to_formatted_date(self, data, key, value):
        d = datetime.fromtimestamp(value)
        return str(d)


class StripeProxyManager(grok.Adapter):

    grok.implements(IStripeProxyManager)
    grok.context(IStripeProxy)

    stripe_api_base_map = {
        'totav.stripe.domain': stripe,
        'totav.stripe.plan': stripe.Plan,
        'totav.stripe.customer': stripe.Customer,
    }

    # subclass responsibilities
    proxy_attrs = []
    proxy_attr_map = { 'stripe_id': "id" }

    stripe_data_filter = DataFilter()
    stripe_data_filter_map = {}

    @property
    def domain(self):
        return aq_parent(aq_inner(self.context))

    @property
    def api_base(self):

        # make sure correct key is registered with api
        d = self.domain
        if d.mode == "testing":
            stripe.api_key = d.testing_secret
        elif d.mode == "production":
            stripe.api_key = d.production_secret

        return self._get_apibase()

    def _get_apibase(self):
        return self.stripe_api_base_map[self.context.portal_type]

    def handle_add(self):

        create = getattr(self.api_base, "create")
        kw = self._get_add_attrdict()

        result = create(**kw)
        self._update_from_remote(result)
        self._update_stripe_attrs(result)

    def handle_modify(self):

        obj = self._retrieve_stripe_object()

        # if for some reason object is missing, add it.
        if not obj:
            self.handle_add()
            obj = self._retrieve_stripe_object()
            if not obj:
                raise ValueError("could not locate object")

        kw = self._get_update_attrdict()
        for k,v in kw.items():
            setattr(obj, k, v)

        result = obj.save()

        self._update_from_remote(result)
        self._update_stripe_attrs(result)

    def handle_remove(self):

        fdm = FinishOnlyDataManager(self._do_remove)
        transaction.get().join(fdm)

    def _do_remove(self, object=None):

        obj = self._retrieve_stripe_object() if object is None else object
        obj.delete()

    def update_from_stripe_object(self, object=None):

        obj = self._retrieve_stripe_object()
        if not obj:
            return
        
        self._update_from_remote(obj)

    def _update_stripe_attrs(self, result):

        self.context.stripe_data = str(result)
        self.context.stripe_status = "clean"
        self.context.stripe_last_update = datetime.now()

    def _get_attr(self, key): return getattr(self.context, key)
    def _set_attr(self, key, value): setattr(self.context, key, value)

    def _update_from_remote(self, obj):
        
        self.context.stripe_id = obj.id

        for k in self.proxy_attrs:  

            if k in obj:
                f = getattr(self, "_set_attr_%s" % k, self._set_attr)
                f(k, obj[k])

        for k,v in self.proxy_attr_map.items():

            f = getattr(self, "_set_attr_%s" % k, self._set_attr)
            f(k, obj[v])
        
    def _get_base_attrdict(self):

        kw = {}
        for k in self.proxy_attrs:  
            f = getattr(self, "_get_attr_%s" % k, self._get_attr)
            kw[k] = f(k)

        for k,v in self.proxy_attr_map.items():
            f = getattr(self, "_get_attr_%s" % k, self._get_attr)
            kw[v] = f(k)

        return kw

    def _get_add_attrdict(self):

        kw = self._get_base_attrdict()
        kw["id"] = self.context.id
        return kw

    def _get_update_attrdict(self):

        return self._get_base_attrdict()

    def _retrieve_stripe_object(self):

        try:
            retrieve = getattr(self.api_base, "retrieve")
            return retrieve(self.context.stripe_id)
        except stripe.StripeError:
            return 

    ################################################################
    # convinience methods
    ################################################################

    @property
    def stripe_data_dict(self):
        sd = self.context.stripe_data
        return json.loads(sd) if sd else {}

    @property
    def filtered_stripe_data_dict(self):
        raw = self.stripe_data_dict
        return self.stripe_data_filter(raw, self.stripe_data_filter_map)

    def search(self, **kw):

        cat = api.portal.get_tool(name='portal_catalog')
        return cat.searchResults(**kw)

    def decendents(self, **kw):

        kw["path"] = { 
            'query': "/".join(self.context.getPhysicalPath()), 
        }
        return self.search(**kw)

    def children(self, **kw):

        kw["path"] = { 
            'query': "/".join(self.context.getPhysicalPath()) ,
            'depth': 1,
        }
        return self.search(**kw)

    def plan_brains(self):

        q = {
            'path': { 'query': "/".join(self.domain.getPhysicalPath()) },
            'portal_type': "totav.stripe.plan",
        }
        return self.search(**q)


grok.templatedir('viewlet_templates')

class StripeInfoViewlet(grok.Viewlet):

    """ A viewlet for displaying strip internal details """

    grok.viewletmanager(IBelowContent)
    grok.context(IStripeProxy)

    def available(self):

        try:
            avail = IStripeProxy(self.context)
        except TypeError:
            return False

        return True


