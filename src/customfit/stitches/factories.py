import factory

from customfit.stitches import models

# Factories for the various template types. The content cut-and-copied
# from the relevant default template as of 29 Sept 2014. I thought about
# having them just dynamically get the content of the templates themselves,
# but decided there was value in making these factories (and therefore the unit
# tests) as static and independent as possible.


class WaistHemTemplateFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.WaistHemTemplate
        strategy = factory.CREATE_STRATEGY

    content = """
{% load pattern_conventions %}
    
    <p>
        CO {{ piece.cast_ons }} stitches using long tail cast-on
        or other 
        cast-on method of your choice. Work even in 
        {{ piece.hem_stitch_patterntext }} for 
        {{ piece.waist_hem_height | length_fmt }} 
        ({{ piece.waist_hem_height_in_rows }} rows from beginning), 
        ending with a WS row.
    </p>
    {{ stitch_transition_text }}
"""


class SleeveHemTemplateFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.SleeveHemTemplate
        strategy = factory.CREATE_STRATEGY

    content = """
{% load pattern_conventions %}
    <p>
        CO {{ piece.cast_ons }} stitches using 
        long tail or other 
        cast-on method of your choice. Work even in
        {{ piece.hem_stitch_patterntext }} for
        {{ piece.wrist_hem_height | length_fmt }} 
        ({{ piece.wrist_hem_height_in_rows }} rows), ending with a WS row.
    </p>
    {{ stitch_transition_text }}
"""


class TrimArmholeTemplateFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.TrimArmholeTemplate
        strategy = factory.CREATE_STRATEGY

    content = """
{% load pattern_conventions %}
{% with design=piece.get_spec_source %}

<p>
     <em>Trim Armholes:</em>
</p>

    <p>
        Beginning at underarm seam, pick up and knit 
        {{ piece.total_armhole_stitches }} sts
        around armhole with a circular needle. 
    </p>
    <p>
        Join for working in the round, being careful not to twist. Work even in 
        {{ design.armhole_edging_stitch_patterntext }} for 
        {{ design.armhole_edging_height | length_fmt }}, 
        then BO all sts. 
    </p>
    <p>
        Repeat for other armhole.
    </p> 

{% endwith %}
"""


class TrimNecklineTemplateFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.TrimNecklineTemplate
        strategy = factory.CREATE_STRATEGY

    content = """
{% load pattern_conventions %}
{% with design=piece.get_spec_source %}
<p>
    <em>Trim Neckline:</em>
</p>

<p>
    Beginning at right neck edge, pick up and knit stitches around the neckline     
    at the following rates: 1 stitch for every bound-off stitch, 3 out of         
    every 4 stitches along the diagonal, and 2 out of every 3 stitches along     
    vertical sections. Approximately 
    {{ piece.total_neckline_pickup_stitches }} stitches picked up total.
    <em>(This exact number is not crucial, <strong>but should respect stitch counts 
    for your stitch pattern</strong>.)</em>
</p>

<p>
    {% if not design.is_cardigan %}
        {# pullover #}
    
        Join for working in the round.
        {% if veeneck_point_instructions %}        
            {# V-neck pullover #}
            Work in 
            {{ design.neck_edging_stitch_patterntext }} for
            {{ design.neck_edging_height | length_fmt }}
            ({{ piece.neck_edging_height_in_rows }} rounds), 
            working a double decrease at center neck point every other round.
        {% else %}        
            {# non-v-neck pullover #}
            Work in 
            {{ design.neck_edging_stitch_patterntext }} for
            {{ design.neck_edging_height | length_fmt }}
            ({{ piece.neck_edging_height_in_rows }} rounds).
        {% endif %}
    {% else %}
        {% comment %}
            Cardigan. The code in renders.py ensures that this is not
            a v-neck cardigan, so we only need to give the non-v-neck
            instructions.
        {% endcomment %}
        Work in 
        {{ design.neck_edging_stitch_patterntext }} for
        {{ design.neck_edging_height | length_fmt }}
        ({{ piece.neck_edging_height_in_rows }} rows).
    {% endif %}
    BO all sts.
</p>

{% endwith %}
"""


class ButtonBandTemplateFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.ButtonBandTemplate
        strategy = factory.CREATE_STRATEGY

    content = """
{% load pattern_conventions %}
<p>
    <em>Right Front Button-band:</em>
</p>
<p>
    Beginning at hem of Right Front, pick up and knit button-band  
    as follows: Pick up and knit stitches at the rate of 2 for every 3 rows
    along button band edge from hem to neck, 
    approximately {{ button_band.stitches }} stitches. (This number is not 
    crucial, <strong>but should respect stitch counts 
    for your stitch pattern</strong>. Buttonhole instructions should be 
    modified if you do not achieve this exact number.) 
</p>
{% if button_band.num_buttonholes != 0 %}
    <p>
        Work even in {{ button_band.edging_stitch_patterntext}} for 
        {{ button_band.half_height | length_fmt }} 
        (approximately {{ button_band.half_height_in_rows }} rows), 
        ending with a WS row.
    </p>
    {% if button_band.evenly_spaced_buttonholes %}
        <p>
            <em>Buttonhole row (RS):</em> Work 
            {{ button_band.stitches_before_first_buttonhole }} stitches, 
            *k2tog, yo, work {{ button_band.inter_buttonhole_stitches }} sts, 
            rep from * {{ button_band.num_interior_buttonholes }} times, 
            [k2tog, yo] once more, work to end. 
            {{ button_band.num_buttonholes }} buttonholes spaced evenly across 
            front. <em>(Note: If you prefer a different buttonhole than an 
                eyelet buttonhole, please feel free to substitute it.)</em>
        </p>
    {% else %}
        <p>
            On last row, place marker at bottom of each desired button hole.
        </p>
        <p>
            <em>Buttonhole row (RS):</em> *Work to marker, *k2tog, yo.
            Rep from * for each marker, work to end.
        </p>
    {% endif %}
{% endif %}    
<p>
    Work even in {{ button_band.edging_stitch_patterntext}} until button band measures
    a total of 
    {{ button_band.height | length_fmt }}
    ({{ button_band.height_in_rows }} rows). BO all stitches.</p>
<p>
    <em>Left Front Button-band:</em> 
</p>
<p>
    Beginning at neck of Left Front, pick up and knit button-band as 
    follows: Pick up and knit stitches at the rate of 2 for every 3 rows along
     button band edge from neck to hem, 
    approximately {{ button_band.stitches }} stitches. (This number is not 
    crucial, <strong>but should respect stitch counts 
    for your stitch pattern</strong>. Buttonhole instructions should be 
    modified if you do not achieve this exact number.)
</p>
<p>
    Work even in {{ button_band.edging_stitch_patterntext}} for 
    {{ button_band.height | length_fmt }} 
    (approximately {{ button_band.height_in_rows }} rows). BO all stitches.
</p>
"""


class ButtonBandVeeneckTemplateFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.ButtonBandVeeneckTemplate
        strategy = factory.CREATE_STRATEGY

    content = """
{% load pattern_conventions %}
<p>
    <em>Button-band and Neckline Trim:</em>
</p>
<p>
    Beginning at hem of Right Front, pick up and knit around entire
    button-band and neckline edge as follows:
</p>
<p> 
    Stitches should be picked up and knit at the rate of 1 stitch for every 
    bound-off stitch, 3 out of every 4 stitches along the diagonal, and 2 out 
    of every 3 stitches along vertical sections. Place markers while picking
    up stitches as follows:
</p>
<p>
    Pick up approximately {{ button_band.stitches }} stitches along right
    front button band edge, place marker; pick up approximately 
    {{ button_band.neckline_pickup_stitches }} along neck edge, place marker;
    pick up approximately {{ button_band.stitches }} along left front edge.
    Approximately {{ button_band.total_veeneck_cardigan_stitches }} stitches;
    this exact number is not crucial, <strong>but should respect stitch counts 
    for your stitch pattern</strong>. 
</p>
{% if button_band.num_buttonholes != 0 %}
    <p>
        Work even in {{ button_band.edging_stitch_patterntext}} for 
        {{ button_band.half_height | length_fmt }} 
        (approximately {{button_band.half_height_in_rows_ws}} rows), 
        ending with a WS row.
    </p>
    {% if button_band.evenly_spaced_buttonholes %}
        <p>
            <em>Buttonhole row (RS):</em> Work 
            {{ button_band.stitches_before_first_buttonhole }} stitches, 
            *k2tog, yo, k {{ button_band.inter_buttonhole_stitches }} sts, 
            rep from * {{ button_band.num_interior_buttonholes }} times, 
            [k2tog, yo] once more, work to first marker, slip first marker, 
            then work to end. 
            {{ button_band.num_buttonholes }} buttonholes spaced evenly across 
            right front. 
        </p>
        <p>
            <strong>Note:</strong> buttonhole instructions should
            be modified if you did not pick up the specified number of stitches
            along the right front button band edge.
        </p>
    {% else %}
        <p>
            On last row, place marker at bottom of each desired button hole.
        </p>
        <p>
            <em>Buttonhole row (RS):</em> *Work to buttonhole marker, *k2tog, yo.
            Rep from * for each marker, work to end of buttonhole.
        </p>
    {% endif %}
{% endif %}    
<p>
    Work as established in {{ button_band.edging_stitch_patterntext}} until trim measures 
    {{ button_band.height | length_fmt}} (approximately 
    {{ button_band.height_in_rows}} rows). BO all stitches. 
</p>
"""


class CowlCastonEdgeTemplateFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.CowlCastonEdgeTemplate
        strategy = factory.CREATE_STRATEGY

    content = """
    {% load pattern_conventions %}
    <p>[default CowlCastonEdgeTemplateFactory template]<p>
    <p>{{ piece.cast_on_stitches | count_fmt }}<p>
    """


class CowlMainSectionTemplateFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.CowlMainSectionTemplate
        strategy = factory.CREATE_STRATEGY

    content = """
    {% load pattern_conventions %}
    <p>[default CowlMainSectionTemplateFactory template]<p>
    <p>{{ piece.cast_on_stitches | count_fmt }}<p>
    """


class CowlCastoffEdgeTemplateFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.CowlCastoffEdgeTemplate
        strategy = factory.CREATE_STRATEGY

    content = """
        {% load pattern_conventions %}
    <p>[default CowlCastoffEdgeTemplateFactory template]<p>
    <p>{{ piece.cast_on_stitches | count_fmt }}<p>
    """


# And now, factories for various kinds of stitches


class StitchFactory(factory.django.DjangoModelFactory):
    """
    A factory for stitches that use no templates. Note: all is_type flags set
    to True, but almost everything else left as the default.
    """

    class Meta:
        model = models.Stitch
        strategy = factory.CREATE_STRATEGY
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: "DefaultEdgingStitchFactory-built stitch %s" % n)
    user_visible = False
    stitch_type = models.UNKNOWN_STITCH_TYPE
    is_waist_hem_stitch = True
    is_sleeve_hem_stitch = True
    is_neckline_hem_stitch = True
    is_armhole_hem_stitch = True
    is_buttonband_hem_stitch = True
    is_allover_stitch = True
    is_panel_stitch = True
    is_accessory_edge_stitch = True
    is_accessory_main_stitch = True
    notes = None


class TemplateStitchFactory(StitchFactory):
    """
    A factory for stitches that use templates.  Note: all is_type flags set to
    True and all templates build by sub-factories, but almost everything else
    left as the default.
    """

    _waist_hem_stitch_template = factory.SubFactory(WaistHemTemplateFactory)
    _sleeve_hem_template = factory.SubFactory(SleeveHemTemplateFactory)
    _trim_armhole_template = factory.SubFactory(TrimArmholeTemplateFactory)
    _trim_neckline_template = factory.SubFactory(TrimNecklineTemplateFactory)
    _button_band_template = factory.SubFactory(ButtonBandTemplateFactory)
    _button_band_veeneck_template = factory.SubFactory(ButtonBandVeeneckTemplateFactory)

    _cowl_caston_edge_template = factory.SubFactory(CowlCastonEdgeTemplateFactory)
    _cowl_main_section_template = factory.SubFactory(CowlMainSectionTemplateFactory)
    _cowl_castoff_edge_template = factory.SubFactory(CowlCastoffEdgeTemplateFactory)
