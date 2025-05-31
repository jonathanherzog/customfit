import os.path
import uuid

import django.template
from dbtemplates.models import Template
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse

import customfit.designs.helpers.design_choices as DC

# 'Empty' models for the various kinds of templates.


class WaistHemTemplate(Template):
    pass


class SleeveHemTemplate(Template):
    pass


class TrimArmholeTemplate(Template):
    pass


class TrimNecklineTemplate(Template):
    pass


class ButtonBandTemplate(Template):
    pass


class ButtonBandVeeneckTemplate(Template):
    pass


class CowlCastonEdgeTemplate(Template):
    pass


class CowlMainSectionTemplate(Template):
    pass


class CowlCastoffEdgeTemplate(Template):
    pass


class RepeatsSpec(object):
    """
    Note on nomenclature: a RepeatsSpec is designed to capture the notion that
    a stitch requires that the cast-on stitch-count be congruent to 7 mod 17,
    for example. Or more generally, be congruent to x mod y for some x and y.
    Since one-character variable names suck, however, we do not call these two
    values merely 'x' and 'y'. Instead, we call them 'x_mod' and 'mod_y'.

    Note: Since we never need to store members of this class in the DB, this
    is not a model.
    """

    # Note: this is relatively 'thin' class, and we don't use it for much
    # at the moment. It is here to ease future expansion, though. At some
    # point, we will want to do more complicated logic for cast-on repeats
    # and stitch compatibility. Right now, an all-over stitch with repeats
    # 2 mod 4 and a edge-stitch with repeats 2 mod 3 are incompatible and
    # we reject the design. But we may want to expand our notion of compatible
    # and say they they *are* compatible and the cast-on needs to be 2 mod 12.
    # When that happens, we will need a class which holds the notion of
    # 'repeats' and is independent of any one stitch. Hence, this class.
    # For example,

    def __init__(self, x_mod=None, mod_y=None):

        if x_mod is None:
            self.x_mod = 0
        else:
            assert int(x_mod) == x_mod
            assert x_mod >= 0
            self.x_mod = x_mod

        if mod_y is None:
            self.mod_y = 1
        else:
            assert int(mod_y) == mod_y
            assert mod_y >= 1
            self.mod_y = mod_y

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        else:
            return all([self.x_mod == other.x_mod, self.mod_y == other.mod_y])

    def __neq__(self, other):
        return not self.__eq__(other)


#
#
# Helper definitions/classes for the Stitch model
#
#


# Stitch-types
LACE_STITCH = "lace_stitch"
CABLE_STITCH = "cable_stitch"
TEXTURED_STITCH = "textured_stitch"
RIBBING_STITCH = "ribbing_stitch"
OTHER_STITCH_TYPE = "other_stitch_type"
UNKNOWN_STITCH_TYPE = "unknown_stitch_type"

STITCH_TYPE_CHOICES = [
    (LACE_STITCH, "Lace stitch"),
    (CABLE_STITCH, "Cable stitch"),
    (TEXTURED_STITCH, "Textured stitch"),
    (RIBBING_STITCH, "Ribbing stitch"),
    (OTHER_STITCH_TYPE, "Other stitch type"),
    (UNKNOWN_STITCH_TYPE, "Unknown stitch type"),
]


class StitchTypeManager(models.Manager):
    """
    A custom manager that limits the initial queryset to user-visible
    stitches of a particular type. This can be used in forms, for example,
    to quickly build a menu of stitches for e.g., waist hems.
    """

    def __init__(self, stitch_type_flag_name, *args, **kwargs):
        """
        Must be given the name of the Stitch field (as a string) that
        indicates the flag which indicates the stitch-type of interest
        (e.g., "is_waist_hem_stitch").
        """
        super(StitchTypeManager, self).__init__(*args, **kwargs)
        self.field_name = stitch_type_flag_name

    def get_queryset(self):
        """
        Return a queryset of user-visible stitches where the relevant
        flag (given to __init__) is True.
        """
        base_queryset = super(StitchTypeManager, self).get_queryset()
        filter_dict = {self.field_name: True, "user_visible": True}
        return base_queryset.filter(**filter_dict)


DEFAULT_TEMPLATE_DIR = os.path.join("stitches", "default_templates")


def _get_image_path(instance, filename):
    """
    Helper method to make sure image files go somewhere sensible.
    """
    unique_filename = "%s%s" % (uuid.uuid4(), filename)
    return os.path.join("stitches", unique_filename)


class Stitch(models.Model):
    """
    Representation of a stitch, which contains many aspects. Among the
    surprising ones:

    * user_visible: if False, then the stitch should not be shown to the
    end-user in any of the drop-down menus of the design wizard.
    We admins can still use the stitch to enter designs, but the user
    shouldn't.

    * Okay, so suppose that a stitch is user-visible. Does that mean it is
    appropriate for *every* component of a design? No. Some stitches are
    suitable as a hem-stitch but not as an all-over stitch. And even within hem-
    stitches, some stitches are suitable for necklines but not armholes. To
    indicate this, there are a series of flags (e.g., is_waist_hem_stitch, etc.)
    Client code can use these flags to select only those stitches for a
    particular hem.

    To combine the previous two items into one example, suppose a user-facing
    form wants to build a list of stitches from which the user can select a
    waist hem. The Right Way to do this would combine both the user-visible flag
    and the waist-hem flag:

    waist_stitches = Stitch.objects.filter(is_waist_hem_stitch = True,
                                           user_visible = True)

    Note that for convenience, this Model provides a set of custom managers
    (e.g., public_waist_stitches) that will automatically return the right
    queryset for these menus. Note, however, that the limit_choices_to argument
    to ForeignKey fields can't take querysets or managers, and so it is still
    important to know how to reproduce these custom managers manually when
    necessary.


    * Moving on: a stitch can hold a number of templates (e.g.,
    _waist_hem_template). Note that these template fields are *internal*, and
    that the public name (waist_hem_template) is actually a property. That is
    so we that if a field is left blank, the property can return a default
    template instead (stored as a template file in the templates
    directory). Also, note that the templates and flags are orthogonal: If a
    stitch has a flag set (e.g., is_waist_hem_stitch) but the template
    (e.g., _waist_hem_stitch_template) is left blank, then the property
    will still export a template. Likewise, the property will *always* return
    a template, even if the flag is set to False. This is by design: Suppose
    that we enable a stitch to be a neckline stitch, and people use it to make
    patterns. Then suppose that we decide to turn the flag off. (Maybe
    it's generating too many questions, or we decide we need to re-work it.)
    This will keep people from using it to make new patterns, but we don't want
    to break the existing ones.
    """

    name = models.CharField(
        max_length=100,
        help_text="Examples: 'Garter Stitch', 'Sugar Cube stitch'",
        unique=True,
    )

    _patterntext = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Text to use for this stitch in patterntext. If left "
        "blank, name is used instead. Example: Other Stitch uses "
        "'stitch pattern of your choice.'",
    )

    user_visible = models.BooleanField(
        default=False,
        help_text="If set, user will be able to see stitch in Design Wizard.",
    )

    repeats_x_mod = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text=" How many extra stitches are required by the repeat "
        "pattern. (If no repeats, put 0.)",
    )

    repeats_mod_y = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="How many stitches are in a full repeat. (If no repeats, " "put 1).",
    )

    stitch_type = models.CharField(
        max_length=20, default=UNKNOWN_STITCH_TYPE, choices=STITCH_TYPE_CHOICES
    )

    notes = models.TextField(
        null=True,
        blank=True,
        help_text="Notes and written instructions. Enter in Markdown format.",
    )

    short_description = models.TextField(
        null=True,
        blank=True,
        help_text="A short description, suitable for characterizing the "
        "stitch on, e.g., the stitch list page. Should not be more "
        "than a sentence or two. Enter in plain text format.",
    )

    chart = models.ImageField(upload_to=_get_image_path, null=True, blank=True)

    photo = models.ImageField(upload_to=_get_image_path, null=True, blank=True)

    extra_notions_text = models.TextField(
        blank=True,
        null=True,
        help_text="Extra notions needed for this stitch. Added to the "
        "'Notions' section of a pattern. Can be HTML, but plaintext safer "
        "when possible. Ignored if left blank.",
    )

    is_waist_hem_stitch = models.BooleanField(default=False)

    is_sleeve_hem_stitch = models.BooleanField(default=False)

    is_neckline_hem_stitch = models.BooleanField(default=False)

    is_armhole_hem_stitch = models.BooleanField(default=False)

    is_buttonband_hem_stitch = models.BooleanField(default=False)

    is_allover_stitch = models.BooleanField(default=False)

    is_panel_stitch = models.BooleanField(default=False)

    is_accessory_edge_stitch = models.BooleanField(default=False)

    is_accessory_main_stitch = models.BooleanField(default=False)

    # TODO: Move these fields to the sweaters app

    # These next fields have internal names (leading underscore) because
    # we will hide them behind properties of the analagous public name
    _waist_hem_stitch_template = models.ForeignKey(
        WaistHemTemplate,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )

    _sleeve_hem_template = models.ForeignKey(
        SleeveHemTemplate,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )

    _trim_armhole_template = models.ForeignKey(
        TrimArmholeTemplate,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )

    _trim_neckline_template = models.ForeignKey(
        TrimNecklineTemplate,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )

    _button_band_template = models.ForeignKey(
        ButtonBandTemplate,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )

    _button_band_veeneck_template = models.ForeignKey(
        ButtonBandVeeneckTemplate,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )

    _cowl_caston_edge_template = models.ForeignKey(
        CowlCastonEdgeTemplate,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )

    _cowl_main_section_template = models.ForeignKey(
        CowlMainSectionTemplate,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )

    _cowl_castoff_edge_template = models.ForeignKey(
        CowlCastoffEdgeTemplate,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )

    # Accessory-specific templates belong in the accessory's app

    extra_finishing_instructions = models.TextField(
        null=True,
        blank=True,
        help_text="Text to go into finishing instructions. NOT MARKDOWN: "
        "enter in HTML.",
    )

    # Managers
    #
    # THE ORDER OF MANAGER-DECLARATION IS FRAGILE AND IMPORTANT.
    # If you define any custom managers, Django will interepret the first defined manager
    # to be the default manager. Since Django uses the default manager in
    # model/form validation, it is important that the default manager return
    # all objects. Therefore, it is crucial that we define 'objects' manually
    # and that it appear *first* in the list of managers.
    #
    # See https://docs.djangoproject.com/en/1.8/topics/db/managers/#default-managers for more information
    #
    objects = models.Manager()
    public_waist_hem_stitches = StitchTypeManager("is_waist_hem_stitch")
    public_sleeve_hem_stitches = StitchTypeManager("is_sleeve_hem_stitch")
    public_neckline_hem_stitches = StitchTypeManager("is_neckline_hem_stitch")
    public_armhole_hem_stitches = StitchTypeManager("is_armhole_hem_stitch")
    public_buttonband_hem_stitches = StitchTypeManager("is_buttonband_hem_stitch")
    public_allover_stitches = StitchTypeManager("is_allover_stitch")
    public_panel_stitches = StitchTypeManager("is_panel_stitch")
    public_accessory_edge_stitches = StitchTypeManager("is_accessory_edge_stitch")
    public_accessory_main_stitches = StitchTypeManager("is_accessory_main_stitch")

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "stitches"

    # Other methods

    def __str__(self):
        return self.name

    @property
    def patterntext(self):
        if self._patterntext:
            return self._patterntext
        else:
            return self.name

    # And now, the promised properties. But first, a helper property

    def _get_public_template(self, field, template_filename):
        """
        If the field is not empty, return a Template from the field's contents.
        Otherwise, return a Template from the template_file. This will be used
        to provide a simple external interface to get the e.g., waist-hem
        template for this stitch.
        """
        if field:
            return django.template.Template(
                field.content,
                # Why do we add this? For testing
                name=field.name,
            )
        else:
            template_path = os.path.join(DEFAULT_TEMPLATE_DIR, template_filename)
            return django.template.loader.get_template(template_path)

    @property
    def waist_hem_stitch_template(self):
        return self._get_public_template(
            self._waist_hem_stitch_template, "waist_hem.html"
        )

    @property
    def sleeve_hem_template(self):
        return self._get_public_template(self._sleeve_hem_template, "sleeve_hem.html")

    @property
    def trim_armhole_template(self):
        return self._get_public_template(
            self._trim_armhole_template, "trim_armhole.html"
        )

    @property
    def trim_neckline_template(self):
        return self._get_public_template(
            self._trim_neckline_template, "trim_neckline.html"
        )

    @property
    def button_band_template(self):
        return self._get_public_template(self._button_band_template, "button_band.html")

    @property
    def button_band_veeneck_template(self):
        return self._get_public_template(
            self._button_band_veeneck_template, "button_band_veeneck.html"
        )

    @property
    def cowl_caston_edge_template(self):
        return self._get_public_template(
            self._cowl_caston_edge_template, "cowl_caston_edge.html"
        )

    @property
    def cowl_castoff_edge_template(self):
        return self._get_public_template(
            self._cowl_castoff_edge_template, "cowl_castoff_edge.html"
        )

    @property
    def cowl_main_section_template(self):
        return self._get_public_template(
            self._cowl_main_section_template, "cowl_main_section.html"
        )

    @property
    def use_repeats(self):
        """
        Return True if this stitch uses non-trivial repeats (i.e., anything
        other than 0 mod 1).
        """
        return (self.repeats_x_mod, self.repeats_mod_y) != (0, 1)

    def is_compatible(self, other_stitch):
        """
        Returns True other_stitch is compatible with this one, meaning that
        this stitch could be used when the design calls for other_stitch.
        Note that other_stitch can be None.

        In general, this method returns False only when it is *certain* that
        the two stitches cannot substitute for each other, meaning that they
        have different repeat-requirements:

        * If other_stitch does not use repeats (other_stitch is None or is
        0 mod 1) then the stitch's repeat-requirements cannot be
        incompatible. This method will return True.

        * Likewise, suppose that this stitch does not use repeats. Then
        other_stitch cannot be incompatible no matter what it is. This method
        returns True.

        * So the only interesting case is when both this stitch and other_stitch
        both use repeats. If the repeat-requirements are the same, then the two
        stitches might be compatible (read: produce the same gauge) and so this
        method returns True. If the two repeat-requirements are different,
        though, then we know that the two stitches are different and we return
        False.
        """

        if other_stitch is None:
            return True
        else:
            if self.use_repeats and other_stitch.use_repeats:
                return all(
                    [
                        self.repeats_x_mod == other_stitch.repeats_x_mod,
                        self.repeats_mod_y == other_stitch.repeats_mod_y,
                    ]
                )
            else:
                return True

    def get_absolute_url(self):
        return reverse("stitch_models:stitch_detail_view", args=[self.pk])

    def get_repeats_spec(self):
        return RepeatsSpec(x_mod=self.repeats_x_mod, mod_y=self.repeats_mod_y)

    def _get_designs(self):
        """
        Returns a list of all designs that use this stitch in any way.

        This includes designs that *should not be visible to end users*,
        so don't use it in templates.
        """
        from customfit.designs.models import Design

        all_designs = [d for d in Design.objects.all() if d.uses_stitch(self)]
        return all_designs

    def get_public_designs(self):
        """
        Returns a list of designer's designs that use this stitch in any way
        and may visible to a (non-staff) user.
        """
        # Note: moving this import to the top-level creates an import loop
        # with the designs app
        from customfit.designs.models import Design

        designs_using = self._get_designs()
        listable = Design.listable.all()
        listable_using = [d for d in designs_using if d in listable]
        return listable_using
