
from datetime import datetime

from Acquisition import aq_inner

#from zope.component import getMultiAdapter
#from Products.CMFCore.utils import getToolByName

from plone import api

from five import grok
from z3c.form import group, field
from zope import schema

from plone.directives import dexterity, form
from plone.dexterity.content import Container
from plone.dexterity.utils import createContentInContainer
from plone.supermodel import model
from zope import schema


from totav.stripe import MessageFactory as _

from totav.stripe.proxy import IStripeProxy
from totav.stripe.proxy import StripeProxyManager
from totav.stripe.proxy import IStripeProxyManager

# Interface class; used to define content-type schema.

class IDomain(model.Schema):
    """
    Domain for managing Stripe Payments
    """

    testing_key = schema.TextLine(
        title=_(u"API Test Publishable Key"),
    )

    testing_secret = schema.TextLine(
        title=_(u"API Test Secret Key"),
    )
    
    production_key = schema.TextLine(
        title=_(u"API Production Publishable Key"),
    )
    
    production_secret = schema.TextLine(
        title=_(u"API Production Secret Key"),
    )
    
    mode = schema._field.Choice(
        ( u'testing', u'production', ),
        title=_(u"Mode"),
    )

    last_update = schema.Datetime(
        title=_(u"Last Update"),
    )

    form.omitted('last_update')
    form.omitted('production_key')
    form.omitted('testing_key')

class Domain(Container): 

    grok.implements(IDomain, IStripeProxy)

    def update_from_stripe_acct(self):

        if self.mode == "testing":
            print "mode test"
            stripe.api_key = self.testing_secret
        elif self.mode == "production":
            print "mode production"
            stripe.api_key = self.production_secret

        h = {
            'customers': self.update_customers(),
            #'plans': self.update_plans(),
        }

    def update_customers(self):

        res = stripe.Customer.all()

        discovered = dict([ (c.stripe_id, c) for c in res.get("data") ])
        discovered_keys = set(discovered)

        existing = dict([ (c.id, c) for c in self.values() ])
        existing_keys = set(existing)

        print discovered_keys
        print existing_keys

        nadded = nremoved = nupdated = 0

        for k in discovered_keys - existing_keys:

            c = self._create_proxy("customer", discovered[k])
            IStripeProxy(c).sync_from_stripe(discovered[k])
            nadded += 1

        return nadded, nremoved, nupdated

    def _create_proxy(self, what, stripe_object):

        return createContentInContainer(
            self, 
            "totav.stripe.%s" % what,
            id=stripe_object.stripe_id,
        )

    def _get_ptype_brains(self, ptype):

        cat = api.portal.get_tool(name='portal_catalog')

        q = { 
            'portal_type': ptype,
            'path': { 'query': "/".join(self.getPhysicalPath()), }
        }
        return cat.searchResults(q)

    def get_plan_brains(self): 
        return self._get_ptype_brains("totav.stripe.plan")

class DomainStripeManager(StripeProxyManager):

    grok.context(IDomain)

    @property
    def domain(self):
        return self.context

    def handle_add(self): 

        api.content.create(
            container=self.context, 
            type="Collection",
            title="Plans",
            query=[
                { u'i': u'portal_type',
                  u'o': u'plone.app.querystring.operation.selection.is',
                  u'v':[ u'totav.stripe.plan'], 
                },
            ]
        )

        api.content.create(
            container=self.context, 
            type="Collection",
            title="Customers",
            query=[
                { u'i': u'portal_type',
                  u'o': u'plone.app.querystring.operation.selection.is',
                  u'v':[ u'totav.stripe.customer'], 
                },
            ]
        )

        self.update_from_stripe_object()

    def handle_modify(self): pass
    def handle_remove(self): pass

    def update_from_stripe_object(self, object=None):

        #import pdb; pdb.set_trace()

        b = self.api_base
        data = getattr(b, "Account").retrieve()
        data["balance"] = getattr(b, "Balance").retrieve()
        self._update_stripe_attrs(data)

    def customer_brains(self):

        return self.decendents(portal_type="totav.stripe.customer")

class View(grok.View):

    grok.context(IDomain)
    grok.require('zope2.View')

    def domain_info(self):

        m = IStripeProxyManager(self.context)
        
        h = {
            'ncustomers': len(m.customer_brains()),
            'nplans': len(m.plan_brains()),
            'stripe_data': m.stripe_data_dict,
        }

        return h


class UpdateView(grok.View):
    """ update view """

    grok.context(IDomain)
    grok.require('zope2.View')
    grok.name('update')

    def do_update(self):

        m = IStripeProxyManager(self.context)
        data = m.update_from_stripe_object()
        return data

