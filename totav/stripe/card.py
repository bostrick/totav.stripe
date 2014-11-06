from five import grok

from Acquisition import aq_inner
from Acquisition import aq_parent

from z3c.form import group, field
from zope import schema
from zope.interface import invariant, Invalid
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from plone.dexterity.content import Item

from plone.directives import dexterity, form
from z3c.form.interfaces import IEditForm, IAddForm

from totav.stripe import MessageFactory as _
from totav.stripe.interfaces import IStripeProxy
from totav.stripe.interfaces import IStripeProxyManager
from totav.stripe.proxy import StripeProxyManager

months_vocab = SimpleVocabulary([
    SimpleTerm(value=1, title=_(u'January')),
    SimpleTerm(value=2, title=_(u'February')),
    SimpleTerm(value=3, title=_(u'March')),
    SimpleTerm(value=4, title=_(u'April')),
    SimpleTerm(value=5, title=_(u'May')),
    SimpleTerm(value=6, title=_(u'June')),
    SimpleTerm(value=7, title=_(u'July')),
    SimpleTerm(value=8, title=_(u'August')),
    SimpleTerm(value=9, title=_(u'September')),
    SimpleTerm(value=10, title=_(u'October')),
    SimpleTerm(value=11, title=_(u'November')),
    SimpleTerm(value=12, title=_(u'December')),
])

years_vocab = SimpleVocabulary([
    SimpleTerm(value=14, title=_(u'2014')),
    SimpleTerm(value=15, title=_(u'2015')),
    SimpleTerm(value=16, title=_(u'2016')),
    SimpleTerm(value=17, title=_(u'2017')),
    SimpleTerm(value=18, title=_(u'2018')),
    SimpleTerm(value=19, title=_(u'2019')),
    SimpleTerm(value=20, title=_(u'2020')),
    SimpleTerm(value=21, title=_(u'2021')),
    SimpleTerm(value=22, title=_(u'2022')),
    SimpleTerm(value=23, title=_(u'2023')),
    SimpleTerm(value=24, title=_(u'2024')),
    SimpleTerm(value=25, title=_(u'2025')),
    SimpleTerm(value=26, title=_(u'2026')),
    SimpleTerm(value=27, title=_(u'2027')),
    SimpleTerm(value=28, title=_(u'2028')),
    SimpleTerm(value=29, title=_(u'2029')),
    SimpleTerm(value=30, title=_(u'2030')),
])

class ICard(form.Schema):

    number = schema._field.TextLine(
        title=_(u"Credit Card Number"),
        default=u"4242424242424242",
    )

    name_on_card = schema._field.TextLine(
        title=_(u"Name On Card"),
    )

    exp_month = schema._field.Choice(
        title=_(u"Expiration Month"),
        default=1,
        vocabulary=months_vocab,
    )

    exp_year = schema._field.Choice(
        title=_(u"Expiration Year"),
        default=17,
        vocabulary=years_vocab,
    )

    cvc = schema.Int(
        title=_(u"CVC Code"),
        required = False
    )

    fingerprint = schema.TextLine(
        title=_(u"Fingerprint"),
        required=False,
    )

    funding = schema._field.Choice(
        ( u'credit', u'debit', u'prepaid', u'unknown', ),
        title=_(u"Funding"),
        default=_(u"unknown"),
    )
    
    brand = schema._field.Choice(
        ( u'Visa', u'American Express', u'MasterCard', 
          u'Discover', u'JSB', u'Diners Club', u'Unknown', ),
        title=_(u"Brand"),
        default=_(u"Unknown"),
    )

    form.omitted('number')
    form.omitted('name_on_card')
    form.omitted('exp_month')
    form.omitted('exp_year')
    form.omitted('fingerprint')
    form.omitted('funding')
    form.omitted('brand')
    form.omitted('cvc')

    form.no_omit(IAddForm, 'number')
    form.no_omit(IAddForm, 'name_on_card')
    form.no_omit(IAddForm, 'exp_month')
    form.no_omit(IAddForm, 'exp_year')
    form.no_omit(IAddForm, 'cvc')


class Card(Item):

    grok.implements(ICard, IStripeProxy)


class CardStripeManager(StripeProxyManager):

    grok.context(ICard)

    # cards are created via custom form
    # def handle_add(self): pass

    proxy_attrs = """
        name_on_card exp_year exp_month fingerprint 
        funding brand 
    """.split()

    proxy_attr_map = {
        'number': 'last4',
    }

    @property
    def domain(self):
        return aq_parent(aq_inner(self.customer))

    @property
    def customer(self):
        return aq_parent(aq_inner(self.context))

    @property 
    def api_base(self):
        return IStripeProxyManager(self.customer).card_api_base

    def _get_add_attrdict(self):

        kw = {
            'card': {
                'number': self.context.number,
                'exp_month': self.context.exp_month,
                'exp_year': self.context.exp_year,
                'cvc': self.context.cvc,
                'name': self.context.name_on_card,
            }
        }

        return kw

    def _do_delete(self):
        c = self.customer
        if c.default_card == self.context.stripe_id:
            c.default_card = ""

    def _update_from_remote(self, obj):
        return super(CardStripeManager, self)._update_from_remote(obj)


class SampleView(grok.View):
    """ sample view class """

    grok.context(ICard)
    grok.require('zope2.View')

    # grok.name('view')

    # Add view methods here
