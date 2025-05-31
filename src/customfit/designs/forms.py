from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms

from customfit.designs.models import Design

from .models import Collection


class CreateCollectionForm(forms.ModelForm):
    designs = forms.ModelMultipleChoiceField(
        queryset=None, widget=forms.SelectMultiple(attrs={"size": "15"})
    )

    def __init__(self, *args, **kwargs):
        super(CreateCollectionForm, self).__init__(*args, **kwargs)
        available_designs = Design.listable.filter(collection=None).order_by("-pk")
        self.fields["designs"].queryset = available_designs

        self.helper = FormHelper(self)
        self.helper.add_input(
            Submit("create", "Create Collection", css_class="btn-customfit-action")
        )

    class Meta:
        model = Collection
        fields = ("name",)
