
from datetime import datetime

from Acquisition import aq_inner
from Acquisition import aq_parent

from five import grok
from zope import schema
from plone.dexterity.content import Item
from plone.supermodel import model
from plone.directives import form

from z3c import relationfield
from plone.formwidget.contenttree import ObjPathSourceBinder
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary

from totav.stripe import MessageFactory as _
from totav.stripe.interfaces import IStripeProxy
from totav.stripe.interfaces import IStripeProxyManager
from totav.stripe.proxy import StripeProxyManager

from zope.component import getUtility
from zope.intid.interfaces import IIntIds

@grok.provider(IContextSourceBinder)
def PlansVocabulary(context):

    CT = SimpleVocabulary.createTerm
    bb = IStripeProxyManager(context).plan_brains()
    tt = [ CT( b.getObject(), b.getObject(), b.Title) for b in bb ]
    return SimpleVocabulary(tt)

class ISubscription(form.Schema):

    title = schema.TextLine(
        title = _(u"Subscription Name"),
        default = _(u"My Subscription"),
    )

    form.widget(plan="z3c.form.browser.radio.RadioFieldWidget")
    plan = relationfield.RelationChoice (
        title = _(u"Plan"),
        #source=ObjPathSourceBinder(portal_type="totav.stripe.plan")
        source=PlansVocabulary,
        #widget=CheckBoxFieldWidget,
    )

    cancel_at_period_end = schema.Bool(
        title = _(u"Cancel at end of period?"),
        default = False,
    )

    quantity = schema.Int(
        title = _(u"Quantity"),
        default = 1
    )

    status = schema._field.Choice(
        ( u'active', u'trialing', u'past_due', u'canceled', 'unpaid', ),
        title=_(u"Funding"),
        default=_(u"trialing"),
    )
    
    canceled_at = schema._field.Datetime(
        title= _(u"Canceled at"),
        required = False
    )
    
    current_period_start = schema._field.Datetime(
        title= _(u"Current Period Start"),
        required = False
    )
    
    current_period_end = schema._field.Datetime(
        title= _(u"Current Period End"),
        required = False
    )
    
    trial_start = schema._field.Datetime(
        title= _(u"Trial Period Start"),
        required = False
    )
    
    trial_end = schema._field.Datetime(
        title= _(u"Trial Period End"),
        required = False
    )

    form.omitted('title')
    form.omitted('cancel_at_period_end')
    form.omitted('quantity')
    form.omitted('status')
    form.omitted('canceled_at')
    form.omitted('current_period_start')
    form.omitted('current_period_end')
    form.omitted('trial_start')
    form.omitted('trial_end')

class Subscription(Item):

    grok.implements(ISubscription, IStripeProxy)

class SubscriptionStripeManager(StripeProxyManager):

    grok.context(ISubscription)

    proxy_attrs = """
        plan 
        cancel_at_period_end quantity status canceled_at 
        current_period_start current_period_end trial_start trial_end
    """.split()

    @property
    def domain(self):
        return aq_parent(aq_inner(self.customer))

    @property
    def customer(self):
        return aq_parent(aq_inner(self.context))

    @property 
    def api_base(self):
        c = IStripeProxyManager(self.customer)._retrieve_stripe_object()
        return c.subscriptions

    def handle_add(self):

        super(SubscriptionStripeManager, self).handle_add()
        if self.context.plan:
            pname = self.context.plan.to_object.title
            self.context.title = "%s Subscription" % pname
            self.context.reindexObject()

    def _get_attr_plan(self, key): 
        return self.context.plan.to_object.stripe_id

    def _set_attr_plan(self, key, value): 
        plan_id = value.get("id")
        if plan_id and plan_id != self.context.plan.to_object.stripe_id:
            raise NotImplemented("subscription plan has changed!")

    def _set_attr_current_period_start(self, key, value): 
        if value:
            self.context.current_period_start = datetime.fromtimestamp(value)

    def _set_attr_current_period_end(self, key, value): 
        if value:
            self.context.current_period_end = datetime.fromtimestamp(value)

    def _set_attr_trial_start(self, key, value): 
        if value:
            self.context.trial_start = datetime.fromtimestamp(value)

    def _set_attr_trial_end(self, key, value): 
        if value:
            self.context.trial_end = datetime.fromtimestamp(value)

    def _get_add_attrdict(self):

        kw = super(SubscriptionStripeManager, self)._get_add_attrdict()

        for k in """
            id
            cancel_at_period_end status canceled_at
            current_period_start current_period_end trial_start 
        """.split():
            kw.pop(k, None)

        return kw

class View(grok.View):
    """ sample view class """

    grok.context(ISubscription)
    grok.require('zope2.View')

    def view_info(self):

        m = IStripeProxyManager(self.context)
        return {
            'stripe_data': m.stripe_data_dict, 
        }

