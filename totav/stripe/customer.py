
from datetime import datetime

from five import grok

from z3c.form import group, field
from z3c.form import button
from z3c.form.interfaces import IEditForm, IAddForm

from plone import api
from zope import schema
from z3c.relationfield.schema import RelationChoice
from plone.dexterity.content import Container
from plone.directives import dexterity, form

from totav.stripe import MessageFactory as _

from totav.stripe.interfaces import IStripeProxy
from totav.stripe.interfaces import IStripeProxyManager
from totav.stripe.proxy import StripeProxyManager

class ICustomer(form.Schema):

    # description

    title = schema.Choice(
        title=_(u"Username"),
        required=False,
        vocabulary=u"plone.principalsource.Users",
    )

    email = schema.TextLine(
        title=_(u"Email Address"),
        description=
            _(u"Leave blank to use the user's registered email address."),
        required=False,
    )

    account_balance = schema.Int(
        title=_(u"Account Balance"),
        default=0,
    )

    currency = schema._field.Choice(
        ( u'usd', ),
        title=_(u"Currency"),
        default='usd',
    )

    default_card = schema.TextLine(
        title=_(u"Default Card"),
        required=False,
    )

    delinquent = schema.Bool(
        title=_(u"Delinquent"),
        default = False,
    )

    #discount = schema.TextLine(
    #    title=_(u"Dicount"),
    #    required=False,
    #)

    form.omitted('account_balance')
    form.omitted('currency')
    form.omitted('default_card')
    form.omitted('delinquent')

    form.no_omit(IEditForm, 'delinquent')

class Customer(Container):

    grok.implements(ICustomer, IStripeProxy)

class CustomerStripeManager(StripeProxyManager):

    grok.context(ICustomer)

    proxy_attrs = """
        email account_balance currency
        default_card delinquent
    """.split()

    @property
    def card_api_base(self):
        c = self._retrieve_stripe_object()
        return c.cards

    @property
    def invoices(self):
        c = self._retrieve_stripe_object()
        return c.invoices()

    def handle_add(self):

        super(CustomerStripeManager, self).handle_add()
        self.context.exclude_from_nav = True
        self.context.reindexObject()

    def _get_add_attrdict(self):

        kw = super(CustomerStripeManager, self)._get_add_attrdict()
        kw.pop('delinquent', None)
        kw.pop('currency', None)
        kw.pop('id', None)

        if self.context.title:

            kw["metadata"] = {'username': self.context.title, }

            if not kw.get("email"):
                u = api.user.get(username=self.context.title)
                kw["email"] = u.getProperty("email")

        return kw

    def _get_update_attrdict(self):

        kw = super(CustomerStripeManager, self)._get_update_attrdict()
        kw.pop('delinquent', None)
        kw.pop('currency', None)

        if 'default_card' in kw and not kw['default_card']:
            del kw['default_card']

        # FIXME: need to readd ability to set default card
        kw.pop('default_card', None)

        return kw

class View(grok.View):

    grok.context(ICustomer)
    grok.require('zope2.View')

    def customer_info(self):

        mgr = IStripeProxyManager(self.context)
        h = {
            'cards': mgr.children(portal_type="totav.stripe.card"),
            'subscriptions':
                mgr.children(portal_type="totav.stripe.subscription"),
            'add_card_url': 
                self.context.absolute_url() + "/++add++totav.stripe.card",
            'add_subscription_url': 
                self.context.absolute_url() +
                "/++add++totav.stripe.subscription",
        }

        plans = mgr.domain.get("plans")
        if plans:
            h["plans_url"] = plans.absolute_url

        return h


class UpdateView(grok.View):

    grok.context(ICustomer)
    grok.require('zope2.View')
    grok.name('update')

    def do_update(self):

        mgr = IStripeProxyManager(self.context)

        ii = mgr.invoices
        found = dict([ (i.id, i) for i in ii.get("data", []) ])
        found_keys = set(found)

        bb = mgr.children(portal_type="totav.stripe.invoice")
        existing = dict([ (b.id, b) for b in bb ])
        existing_keys = set(existing)

        nadded = nremoved = nupdated = 0

        for k in found_keys - existing_keys:
        
            inv = found[k]
            inv_date = str(datetime.fromtimestamp(inv["date"]))

            inv_item = api.content.create(
                container=self.context,
                type="totav.stripe.invoice",
                title="Invoice %s" % inv_date,
                id=inv["id"],
                #stripe_data = inv,
            )

            imgr = IStripeProxyManager(inv_item)
            imgr._update_stripe_attrs(inv)
            nadded += 1

        for k in existing_keys - found_keys:

            api.content.delete(obj=self.context[k])
            nremoved += 1

        for k in existing_keys & found_keys:

            imgr = IStripeProxyManager(self.context[k])
            imgr._update_stripe_attrs(found[k])
            nupdated += 1

        return {
            'nadded': nadded, 
            'nremoved': nremoved, 
            'nupdated': nupdated, 
        }

