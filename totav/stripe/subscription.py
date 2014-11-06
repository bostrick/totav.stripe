
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

@grok.provider(IContextSourceBinder)
def PlansVocabulary(context):

    CT = SimpleVocabulary.createTerm
    bb = IStripeProxyManager(context).plan_brains()
#    import pdb; pdb.set_trace()
    tt = [ CT(b.UID, b.getObject(), b.Title) for b in bb]
    return SimpleVocabulary(tt)


class ISubscription(form.Schema):

    plan = relationfield.RelationChoice (
        title = _(u"Plan"),
        source=ObjPathSourceBinder(portal_type="totav.stripe.plan")
        #source=PlansVocabulary,
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

    proxy_attr_map = {
        #'stripe_id': 'id',
        #'title': 'name',
    }

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



# View class
# The view will automatically use a similarly named template in
# subscription_templates.
# Template filenames should be all lower case.
# The view will render when you request a content object with this
# interface with "/@@sampleview" appended.
# You may make this the default view for content objects
# of this type by uncommenting the grok.name line below or by
# changing the view class name and template filename to View / view.pt.

#class SampleView(grok.View):
#    """ sample view class """
#
#    grok.context(ISubscription)
#    grok.require('zope2.View')
#
#    # grok.name('view')
#
#    # Add view methods here
