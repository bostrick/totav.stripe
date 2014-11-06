from five import grok

from z3c.form import group, field
from zope import schema
from plone.dexterity.content import Container
from plone.directives import dexterity, form


from totav.stripe import MessageFactory as _
from totav.stripe.interfaces import IStripeProxy
from totav.stripe.proxy import StripeProxyManager

class IInvoice(form.Schema):

    """Customer Invoice"""


class Invoice(Container):

    grok.implements(IInvoice, IStripeProxy)

class InvoiceStripeManager(StripeProxyManager):

    grok.context(IInvoice)

    # initialization handled via customer update
    def handle_add(self): pass


#class SampleView(grok.View):
#    """ sample view class """
#
#    grok.context(IInvoice)
#    grok.require('zope2.View')
#
#    # grok.name('view')
#
#    # Add view methods here

