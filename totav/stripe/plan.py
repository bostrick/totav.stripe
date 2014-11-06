
from five import grok
from zope import schema
from plone.dexterity.content import Item
from plone.supermodel import model

from plone.directives import dexterity, form
from z3c.form.interfaces import IEditForm, IAddForm
from plone.app.textfield import RichText

from totav.stripe import MessageFactory as _

from totav.stripe.interfaces import IStripeProxy
from totav.stripe.proxy import StripeProxyManager

class IPlan(model.Schema):

    """
    Stripe Plan
    """

    body = RichText(
        title=u"Description",
        required=False,
    )

    interval = schema._field.Choice(
        ( u'day', u'week', u'month', u'year', ),
        title=_(u"Interval"),
        default='month',
    )
    
    amount = schema.Decimal(
        title=_(u"Amount"),
    )

    interval_count = schema.Int(
        title=_(u"Interval Count"),
        default=1,
    )

    trial_period_days = schema.Int(
        title=_(u"Trial Period Days"),
        default=0,
    )

    statement_description = schema.TextLine(
        title=_(u"Statement Line"),
        description=_(u"information will show up on customer's statement"),
        required=False,
    )

    currency = schema._field.Choice(
        ( u'usd', ),
        title=_(u"Currency"),
        default='usd',
    )

    form.omitted('interval')
    form.omitted('amount')
    form.omitted('interval_count')
    form.omitted('trial_period_days')
    form.omitted('statement_description')
    form.omitted('currency')

    form.no_omit(IAddForm, 'interval')
    form.no_omit(IAddForm, 'amount')
    form.no_omit(IAddForm, 'interval_count')
    form.no_omit(IAddForm, 'trial_period_days')
    form.no_omit(IAddForm, 'statement_description')
    form.no_omit(IAddForm, 'currency')

class Plan(Item):

    grok.implements(IPlan, IStripeProxy)

    def display_amount(self):
        return "$%0.2f" % float(self.amount)

class View(grok.View):

    grok.context(IPlan)
    grok.require('zope2.View')


class PlanStripeManager(StripeProxyManager):

    grok.context(IPlan)

    proxy_attrs = """
        interval amount interval_count trial_period_days 
        statement_description currency
    """.split()

    proxy_attr_map = {
        'stripe_id': 'id',
        'title': 'name',
    }

    def handle_add(self):

        super(PlanStripeManager, self).handle_add()
        self.context.exclude_from_nav = True
        self.context.reindexObject()

    def _get_attr_amount(self, key): 
        return int(float(self.context.amount) * 100.0)

    def _set_attr_amount(self, key, value): 
        self.context.amount = value / 100.0

    def _get_update_attrdict(self):

        # once created, only plan name can be modified
        return { 'name': self.context.title }




