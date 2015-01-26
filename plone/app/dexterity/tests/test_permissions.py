# -*- coding: utf-8 -*-
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import login
from plone.app.testing import setRoles
from plone.app.content.browser.vocabulary import VocabularyView
from plone.app.widgets.testing import PLONEAPPWIDGETS_DX_INTEGRATION_TESTING
from plone.app.widgets.testing import TestRequest
from plone.autoform.interfaces import WIDGETS_KEY
from plone.autoform.interfaces import WRITE_PERMISSIONS_KEY
from zope import schema
from zope.globalrequest import setRequest
from zope.interface import Interface
from z3c.form.widget import FieldWidget
from plone.dexterity.fti import DexterityFTI

import json

try:
    import unittest2 as unittest
except ImportError:  # pragma: nocover
    import unittest  # pragma: nocover
    assert unittest  # pragma: nocover


def add_mock_fti(portal):
    # Fake DX Type
    fti = DexterityFTI('dx_mock')
    portal.portal_types._setObject('dx_mock', fti)
    fti.klass = 'plone.dexterity.content.Item'
    fti.schema = 'plone.app.widgets.tests.test_dx.IMockSchema'
    fti.filter_content_types = False
    fti.behaviors = ('plone.app.dexterity.behaviors.metadata.IBasic',)


def _custom_field_widget(field, request):
    from plone.app.z3cform.widget import AjaxSelectWidget
    widget = FieldWidget(field, AjaxSelectWidget(request))
    widget.vocabulary = 'plone.app.vocabularies.PortalTypes'
    return widget


class IMockSchema(Interface):
    allowed_field = schema.Choice(
        vocabulary='plone.app.vocabularies.PortalTypes')
    disallowed_field = schema.Choice(
        vocabulary='plone.app.vocabularies.PortalTypes')
    default_field = schema.Choice(
        vocabulary='plone.app.vocabularies.PortalTypes')
    custom_widget_field = schema.TextLine()
    adapted_widget_field = schema.TextLine()

IMockSchema.setTaggedValue(WRITE_PERMISSIONS_KEY, {
    'allowed_field': u'zope2.View',
    'disallowed_field': u'zope2.ViewManagementScreens',
    'custom_widget_field': u'zope2.View',
    'adapted_widget_field': u'zope2.View',
})
IMockSchema.setTaggedValue(WIDGETS_KEY, {
    'custom_widget_field': _custom_field_widget,
})


class DexterityVocabularyPermissionTests(unittest.TestCase):

    layer = PLONEAPPWIDGETS_DX_INTEGRATION_TESTING

    def setUp(self):
        self.request = TestRequest(environ={'HTTP_ACCEPT_LANGUAGE': 'en'})
        setRequest(self.request)
        self.portal = self.layer['portal']

        login(self.portal, TEST_USER_NAME)
        setRoles(self.portal, TEST_USER_ID, ['Manager'])

        add_mock_fti(self.portal)
        self.portal.invokeFactory('dx_mock', 'test_dx')

        self.portal.test_dx.manage_permission('View',
                                              ('Anonymous',),
                                              acquire=False)
        self.portal.test_dx.manage_permission('View management screens',
                                              (),
                                              acquire=False)
        self.portal.test_dx.manage_permission('Modify portal content',
                                              ('Editor', 'Manager',
                                               'Site Adiminstrator'),
                                              acquire=False)

    def test_vocabulary_field_allowed(self):
        view = VocabularyView(self.portal.test_dx, self.request)
        self.request.form.update({
            'name': 'plone.app.vocabularies.PortalTypes',
            'field': 'allowed_field',
        })
        data = json.loads(view())
        self.assertEquals(len(data['results']),
                          len(self.portal.portal_types.objectIds()))

    def test_vocabulary_field_wrong_vocabulary_disallowed(self):
        view = VocabularyView(self.portal.test_dx, self.request)
        self.request.form.update({
            'name': 'plone.app.vocabularies.Fake',
            'field': 'allowed_field',
        })
        data = json.loads(view())
        self.assertEquals(data['error'], 'Vocabulary lookup not allowed')

    def test_vocabulary_field_disallowed(self):
        view = VocabularyView(self.portal.test_dx, self.request)
        self.request.form.update({
            'name': 'plone.app.vocabularies.PortalTypes',
            'field': 'disallowed_field',
        })
        data = json.loads(view())
        self.assertEquals(data['error'], 'Vocabulary lookup not allowed')

    def test_vocabulary_field_default_permission(self):
        view = VocabularyView(self.portal.test_dx, self.request)
        self.request.form.update({
            'name': 'plone.app.vocabularies.PortalTypes',
            'field': 'default_field',
        })
        # If the field is does not have a security declaration, the
        # default edit permission is tested (Modify portal content)
        setRoles(self.portal, TEST_USER_ID, ['Member'])
        data = json.loads(view())
        self.assertEquals(data['error'], 'Vocabulary lookup not allowed')

        setRoles(self.portal, TEST_USER_ID, ['Editor'])
        # Now access should be allowed, but the vocabulary does not exist
        data = json.loads(view())
        self.assertEquals(len(data['results']),
                          len(self.portal.portal_types.objectIds()))

    def test_vocabulary_field_default_permission_wrong_vocab(self):
        view = VocabularyView(self.portal.test_dx, self.request)
        self.request.form.update({
            'name': 'plone.app.vocabularies.Fake',
            'field': 'default_field',
        })
        setRoles(self.portal, TEST_USER_ID, ['Editor'])
        # Now access should be allowed, but the vocabulary does not exist
        data = json.loads(view())
        self.assertEquals(data['error'], 'Vocabulary lookup not allowed')

    def test_vocabulary_missing_field(self):
        view = VocabularyView(self.portal.test_dx, self.request)
        self.request.form.update({
            'name': 'plone.app.vocabularies.PortalTypes',
            'field': 'missing_field',
        })
        setRoles(self.portal, TEST_USER_ID, ['Member'])
        with self.assertRaises(AttributeError):
            view()

    def test_vocabulary_on_widget(self):
        view = VocabularyView(self.portal.test_dx, self.request)
        self.request.form.update({
            'name': 'plone.app.vocabularies.PortalTypes',
            'field': 'custom_widget_field',
        })
        data = json.loads(view())
        self.assertEquals(len(data['results']),
                          len(self.portal.portal_types.objectIds()))
        self.request.form['name'] = 'plone.app.vocabularies.Fake'
        data = json.loads(view())
        self.assertEquals(data['error'], 'Vocabulary lookup not allowed')

    def test_vocabulary_on_adapted_widget(self):
        view = VocabularyView(self.portal.test_dx, self.request)
        self.request.form.update({
            'name': 'plone.app.vocabularies.PortalTypes',
            'field': 'adapted_widget_field',
        })
        data = json.loads(view())
        self.assertEquals(len(data['results']),
                          len(self.portal.portal_types.objectIds()))

        self.request.form['name'] = 'plone.app.vocabularies.Fake'
        data = json.loads(view())
        self.assertEquals(data['error'], 'Vocabulary lookup not allowed')
