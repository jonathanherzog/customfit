# Generated by Django 5.0.6 on 2025-01-25 18:39

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("garment_parameters", "0003_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConstructionSchematic",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "creation_date",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                (
                    "customized",
                    models.BooleanField(
                        default=False,
                        help_text="If true, the user has tweaked the values in this model. If false, everything was derived.",
                    ),
                ),
                (
                    "individual_garment_parameters",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="garment_parameters.individualgarmentparameters",
                    ),
                ),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_%(app_label)s.%(class)s_set+",
                        to="contenttypes.contenttype",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="GradedConstructionSchematic",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "creation_date",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                (
                    "graded_garment_parameters",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="garment_parameters.gradedgarmentparameters",
                    ),
                ),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_%(app_label)s.%(class)s_set+",
                        to="contenttypes.contenttype",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="GradedPieceSchematic",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "construction_schematic",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="gradedpieceschematic_set",
                        to="schematics.gradedconstructionschematic",
                    ),
                ),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_%(app_label)s.%(class)s_set+",
                        to="contenttypes.contenttype",
                    ),
                ),
            ],
        ),
    ]
