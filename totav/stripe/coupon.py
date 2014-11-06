from five import grok

from z3c.form import group, field
from zope import schema
from zope.interface import invariant, Invalid
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from plone.dexterity.content import Item

from plone.directives import dexterity, form
from plone.app.textfield import RichText
from plone.namedfile.field import NamedImage, NamedFile
from plone.namedfile.field import NamedBlobImage, NamedBlobFile
from plone.namedfile.interfaces import IImageScaleTraversable


from totav.stripe import MessageFactory as _


# Interface class; used to define content-type schema.

class ICoupon(form.Schema, IImageScaleTraversable):
    """
    Stripe Coupon
    """

    duration = schema._field.Choice(
        ( u'forever', u'once', u'repeating', ),
        title=_(u"Duration"),
        default='repeating',
    )

    amount_off = schema.Decimal(
        title=_(u"Amount Off"),
    )

    currency = schema._field.Choice(
        ( u'USD', ),
        title=_(u"Currency"),
        default='USD',
    )

    duration_in_months = schema.Int(
        title=_(u"Duration in Months"),
        default=3,
    )

    max_redemptions = schema.Int(
        title=_(u"Maximun Number of Redemptions"),
        default=999,
    )

    precent_off = schema.Int(
        title=_(u"Percent Off"),
        default=10,
    )

    redeem_by = schema.Datetime(
        title=_(u"Redeem By"),
        required = False,
    )

    times_redeemed = schema.Int(
        title=_(u"Times Redeemed"),
        required = False,
    )

    valid = schema.Bool(
        title=_(u"Valid"),
        default = True,
    )



    


# Custom content-type class; objects created for this content type will
# be instances of this class. Use this class to add content-type specific
# methods and properties. Put methods that are mainly useful for rendering
# in separate view classes.

class Coupon(Item):
    grok.implements(ICoupon)

    # Add your class methods and properties here
    pass


# View class
# The view will automatically use a similarly named template in
# coupon_templates.
# Template filenames should be all lower case.
# The view will render when you request a content object with this
# interface with "/@@sampleview" appended.
# You may make this the default view for content objects
# of this type by uncommenting the grok.name line below or by
# changing the view class name and template filename to View / view.pt.

class SampleView(grok.View):
    """ sample view class """

    grok.context(ICoupon)
    grok.require('zope2.View')

    # grok.name('view')

    # Add view methods here
