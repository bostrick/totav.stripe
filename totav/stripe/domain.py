
from datetime import datetime

from Acquisition import aq_inner

#from zope.component import getMultiAdapter
#from Products.CMFCore.utils import getToolByName

from plone import api

from five import grok

from plone.directives import dexterity, form
from plone.dexterity.content import Container
from plone.supermodel import model
from zope import schema

from Products.statusmessages.interfaces import IStatusMessage
from plone.app.layout.viewlets.interfaces import IHtmlHead
from plone.app.layout.viewlets.interfaces import IBelowContentBody

from plone.dexterity.utils import createContentInContainer

from totav.stripe import MessageFactory as _

from totav.stripe.interfaces import IDonationRelated
from totav.stripe.proxy import IStripeProxy
from totav.stripe.proxy import StripeProxyManager
from totav.stripe.proxy import IStripeProxyManager

# Interface class; used to define content-type schema.

def get_stripe_domain_brain():

    cat = api.portal.get_tool("portal_catalog")
    bb = cat(portal_type="totav.stripe.domain")
    if len(bb) > 1:
        raise ValueError("more than one domain")
    elif bb:
        return bb[0]

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
    
    mode = schema.Choice(
        ( u'testing', u'production', ),
        title=_(u"Mode"),
    )

    last_update = schema.Datetime(
        title=_(u"Last Update"),
    )

    form.omitted('last_update')

class Domain(Container): 

    grok.implements(IDomain, IStripeProxy)

    def get_public_key(self):

        if self.mode == 'production':
            return self.production_key
        else:
            return self.testing_key

#    def update_from_stripe_acct(self):
#
#        if self.mode == "testing":
#            print "mode test"
#            stripe.api_key = self.testing_secret
#        elif self.mode == "production":
#            print "mode production"
#            stripe.api_key = self.production_secret
#
#        h = {
#            'customers': self.update_customers(),
#            #'plans': self.update_plans(),
#        }
#
#    def update_customers(self):
#
#        res = stripe.Customer.all()
#
#        discovered = dict([ (c.stripe_id, c) for c in res.get("data") ])
#        discovered_keys = set(discovered)
#
#        existing = dict([ (c.id, c) for c in self.values() ])
#        existing_keys = set(existing)
#
#        print discovered_keys
#        print existing_keys
#
#        nadded = nremoved = nupdated = 0
#
#        for k in discovered_keys - existing_keys:
#
#            c = self._create_proxy("customer", discovered[k])
#            IStripeProxy(c).sync_from_stripe(discovered[k])
#            nadded += 1
#
#        return nadded, nremoved, nupdated

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

        b = self.api_base
        data = getattr(b, "Account").retrieve()
        data["balance"] = getattr(b, "Balance").retrieve()
        self._update_stripe_attrs(data)

    def customer_brains(self):

        return self.decendents(portal_type="totav.stripe.customer")

    @property
    def plan_brains(self):
        return self.decendents(portal_type="totav.stripe.plan")

    def get_customer_brain(self, username):
        bb = self.decendents(
            portal_type="totav.stripe.customer",
            title=username,
        )
        return bb[0] if bb else None

    def handle_charge(self, token_id, amount, email=None):

        if not (token_id and amount):
            raise ValueError("token and amount must be provided")

        text = "at.theclubhou.se donation"
        if email:
            text += " (%s)" % email

        token = self.api_base.Charge.create(
            amount=amount,
            card=token_id,
            currency="usd",
            description=text,
        )

    def enroll_customer(self, plan, token, username=None):

        if not username:
            user = api.user.current_user().getProperty("username")
        else:
            user = api.user.get(username=username)

        username = user.getId()
        email = user.getProperty("email")

        b = self.get_customer_brain(username)
        if not b:

            cust = self.api_base.Customer.create(
                card=token,
                email=email,
                metadata={'username': username, },
                plan=plan,
            )

            custobj = createContentInContainer(
                self.context,
                "totav.stripe.customer",
                id=cust.id,
                title=username,
                stripe_id=cust.id,
                exclude_from_nav=True,
                checkConstraints=False,
            )

            cmgr = IStripeProxyManager(custobj)
            cmgr.update_from_stripe_object(cust)

class View(grok.View):

    js_template = """
        <script type="text/javascript" >
            var stripe_public_key = '%s';
        </script>
    """

    grok.context(IDomain)
    grok.require('zope2.View')

    def __call__(self, *args, **kw):

        if not self.request["REQUEST_METHOD"] == "POST":
            return super(View, self).__call__(*args, **kw)

        if str(self.request.form.get("command")) == "charge":

            self._handle_charge()
                
        else:

            plan = self.request.form.get('plan')
            token = self.request.form.get('token')
            username = self.request["AUTHENTICATED_USER"].getId()

            if token and plan:

                mgr = IStripeProxyManager(self.context)
                mgr.enroll_customer(plan, token, username)

            else:
                print "bad post."

            self.request.response.redirect(self.context.absolute_url())

    def _handle_charge(self):

        token = self.request.form.get('token[id]')
        amount = self.request.form.get('amount')
        email = self.request.form.get('token[email]', "")

        IStripeProxyManager(self.context).handle_charge(token, amount, email)

        msg = _(u"Thank you for your donation.")
        IStatusMessage(self.request).add(msg)

    def register_info(self):

        portal = api.portal.get()
        purl = portal.absolute_url()
        user = None if api.user.is_anonymous() else api.user.get_current()

        mgr = IStripeProxyManager(self.context)
        customer = mgr.get_customer_brain(user.getId()) if user else None

        h = {
            'register_url': purl + "/@@register",
            'login_url':    purl + "/login",
            'customer':     customer,
            'plans':        mgr.plan_brains,
        }
        return h

    def domain_info(self):

        m = IStripeProxyManager(self.context)
        
        h = {
            'ncustomers': len(m.customer_brains()),
            'nplans': len(m.plan_brains()),
            'stripe_data': m.stripe_data_dict,
        }

        return h

    def js_setup(self):
        return self.js_template % self.context.get_public_key()


class UpdateView(grok.View):
    """ update view """

    grok.context(IDomain)
    grok.require('zope2.View')
    grok.name('update')

    def do_update(self):

        m = IStripeProxyManager(self.context)
        data = m.update_from_stripe_object()
        return data


class DonateHeadViewlet(grok.Viewlet):

    grok.viewletmanager(IHtmlHead)
    grok.context(IDonationRelated)

    def available(self): return True

    def render(self):

        a = '<script src="https://checkout.stripe.com/checkout.js"></script>'
        return a


class DonateViewlet(grok.Viewlet):

    """ 
    """

    grok.viewletmanager(IBelowContentBody)
    grok.context(IDonationRelated)

    def available(self): return True

    def donate_info(self):

        b = get_stripe_domain_brain()
        dom = b.getObject()

        purl = api.portal.get().absolute_url()

        h = {
            'action': b.getPath(),
            'public_key': dom.get_public_key(),
            'next_url': b.getPath(),
            'image_url': purl + "/logo.png",
        }
        return h

