import doctest
import unittest

from Testing import ZopeTestCase as ztc

from Products.Five import zcml
from Products.PloneTestCase import PloneTestCase as ptc
from Products.PloneTestCase.layer import PloneSite
from Products.PloneTestCase.layer import onsetup

import totav.stripe

OPTION_FLAGS = doctest.NORMALIZE_WHITESPACE | \
               doctest.ELLIPSIS

ptc.setupPloneSite(products=['totav.stripe'])


class TestCase(ptc.PloneTestCase):

    class layer(PloneSite):

        @classmethod
        def setUp(cls):
            zcml.load_config('configure.zcml',
              totav.stripe)

        @classmethod
        def tearDown(cls):
            pass


def test_suite():
    return unittest.TestSuite([

        # Unit tests
        #doctestunit.DocFileSuite(
        #    'README.txt', package='totav.stripe',
        #    setUp=testing.setUp, tearDown=testing.tearDown),

        #doctestunit.DocTestSuite(
        #    module='totav.stripe.mymodule',
        #    setUp=testing.setUp, tearDown=testing.tearDown),


        # Integration tests that use PloneTestCase
        ztc.ZopeDocFileSuite(
            'INTEGRATION.txt',
            package='totav.stripe',
            optionflags = OPTION_FLAGS,
            test_class=TestCase),

        # -*- extra stuff goes here -*-

        # Integration tests for Invoice
        ztc.ZopeDocFileSuite(
            'Invoice.txt',
            package='totav.stripe',
            optionflags = OPTION_FLAGS,
            test_class=TestCase),


        # Integration tests for Subscription
        ztc.ZopeDocFileSuite(
            'Subscription.txt',
            package='totav.stripe',
            optionflags = OPTION_FLAGS,
            test_class=TestCase),


        # Integration tests for Card
        ztc.ZopeDocFileSuite(
            'Card.txt',
            package='totav.stripe',
            optionflags = OPTION_FLAGS,
            test_class=TestCase),


        # Integration tests for Coupon
        ztc.ZopeDocFileSuite(
            'Coupon.txt',
            package='totav.stripe',
            optionflags = OPTION_FLAGS,
            test_class=TestCase),


        # Integration tests for Plan
        ztc.ZopeDocFileSuite(
            'Plan.txt',
            package='totav.stripe',
            optionflags = OPTION_FLAGS,
            test_class=TestCase),


        # Integration tests for PricingPlan
        ztc.ZopeDocFileSuite(
            'PricingPlan.txt',
            package='totav.stripe',
            optionflags = OPTION_FLAGS,
            test_class=TestCase),


        # Integration tests for Customer
        ztc.ZopeDocFileSuite(
            'Customer.txt',
            package='totav.stripe',
            optionflags = OPTION_FLAGS,
            test_class=TestCase),


        # Integration tests for StripeDomain
        ztc.ZopeDocFileSuite(
            'StripeDomain.txt',
            package='totav.stripe',
            optionflags = OPTION_FLAGS,
            test_class=TestCase),


        ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
