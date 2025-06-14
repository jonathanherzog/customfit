# Generated by Django 5.0.6 on 2025-01-25 18:39

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("pieces", "0001_initial"),
        ("schematics", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="gradedpatternpieces",
            name="schematic",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="schematics.gradedconstructionschematic",
            ),
        ),
        migrations.AddField(
            model_name="gradedpatternpiece",
            name="graded_pattern_pieces",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="gradedpatternpiece_set",
                to="pieces.gradedpatternpieces",
            ),
        ),
        migrations.AddField(
            model_name="patternpiece",
            name="polymorphic_ctype",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="polymorphic_%(app_label)s.%(class)s_set+",
                to="contenttypes.contenttype",
            ),
        ),
        migrations.AddField(
            model_name="patternpieces",
            name="polymorphic_ctype",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="polymorphic_%(app_label)s.%(class)s_set+",
                to="contenttypes.contenttype",
            ),
        ),
        migrations.AddField(
            model_name="patternpieces",
            name="schematic",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="schematics.constructionschematic",
            ),
        ),
    ]
