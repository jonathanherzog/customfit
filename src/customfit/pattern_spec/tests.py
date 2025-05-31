import django.test
from django.core.files.uploadedfile import SimpleUploadedFile

from customfit.designs.factories import DesignFactory
from customfit.userauth.factories import UserFactory

from .factories import GradedPatternSpecFactory, PatternSpecFactory


class BasePatternSpecTest(object):

    def test_pass_through_to_design(self):
        cover_sheet = SimpleUploadedFile("image.jpg", b"contents")
        des = DesignFactory(
            notions="notions foo",
            recommended_gauge="recommended_gauge foo",
            recommended_materials="recommended_materials foo",
            needles="needles foo",
            yarn_notes="yarn_notes foo",
            style_notes="style_notes foo",
            description="description foo",
            cover_sheet=cover_sheet,
        )
        pspec = self.factory(design_origin=des)
        self.assertEqual(pspec.notions, "notions foo")
        self.assertEqual(pspec.recommended_gauge, "recommended_gauge foo")
        self.assertEqual(pspec.recommended_materials, "recommended_materials foo")
        self.assertEqual(pspec.needles, "needles foo")
        self.assertEqual(pspec.yarn_notes, "yarn_notes foo")
        self.assertEqual(pspec.style_notes, "style_notes foo")
        self.assertEqual(pspec.description, "description foo")
        # Unfortunately, we can't test equality for this last one
        # as we change the file's name when we store it in storage.
        self.assertIsNotNone(pspec.get_cover_sheet())

    def test_pass_through_to_no_design(self):
        pspec = self.factory(design_origin=None)
        self.assertIsNone(pspec.notions)
        self.assertIsNone(pspec.recommended_gauge)
        self.assertIsNone(pspec.recommended_materials)
        self.assertIsNone(pspec.needles)
        self.assertIsNone(pspec.yarn_notes)
        self.assertIsNone(pspec.style_notes)
        self.assertIsNone(pspec.description)
        self.assertIsNone(pspec.get_cover_sheet())

    def test_unicode(self):
        user = UserFactory()
        pspec = self.factory(name="name", user=user)
        goal_text = "name/%s" % user
        self.assertEqual(str(pspec), goal_text)


class PatternSpecTest(django.test.TestCase, BasePatternSpecTest):

    factory = PatternSpecFactory


class GradedPatternSpecTest(django.test.TestCase, BasePatternSpecTest):
    factory = GradedPatternSpecFactory
