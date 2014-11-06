from five import grok

from z3c.form import group, field
from zope import schema
from plone.dexterity.content import Container
from plone.directives import dexterity, form


from totav.stripe import MessageFactory as _
from totav.stripe.interfaces import IStripeProxy
from totav.stripe.interfaces import IStripeProxyManager
from totav.stripe.proxy import StripeProxyManager

class IInvoice(form.Schema):

    """Customer Invoice"""

class Invoice(Container):

    grok.implements(IInvoice, IStripeProxy)

class InvoiceStripeManager(StripeProxyManager):

    grok.context(IInvoice)

    stripe_data_filter_map = {
        'total': "cents_to_us_dollar",
        'subtotal': "cents_to_us_dollar",
        'ending_balance': "cents_to_us_dollar",
        'starting_balance': "cents_to_us_dollar",
        'amount_due': "cents_to_us_dollar",
        'date': "timestamp_to_formatted_date",
        'period_start': "timestamp_to_formatted_date",
        'period_end': "timestamp_to_formatted_date",
    }

    line_item_filter_map = {
        'period.start': "timestamp_to_formatted_date",
        'period.end': "timestamp_to_formatted_date",
    }

    # lifecycle handled via customer update
    def handle_add(self): pass

    #def handle_modify(self): pass
    #def handle_delete(self): pass

class View(grok.View):

    grok.context(IInvoice)
    grok.require('zope2.View')
    # grok.name('view')

    def view_info(self):

        m = IStripeProxyManager(self.context)
        idata = m.filtered_stripe_data_dict

        DF = m.stripe_data_filter
        lines = idata["lines"]["data"]
        lines = [ DF(l, m.line_item_filter_map ) for l in lines ]
        return {
            'stripe_data': m.filtered_stripe_data_dict,
            'lines': lines,
        }

