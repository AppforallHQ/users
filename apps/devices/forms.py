from django import forms
from django.utils.translation import ugettext, ugettext_lazy as _
from .models import Device


class NewForm(forms.ModelForm):
    """
    A form that register new device for user.
    """
    error_messages = {}
    PLANS = (
        (1, '1 Month'),
        (2, '2 Month'),
        (3, '3 Month'),
        (6, '6 Month'),
        (12, '12 Month')
    )
    plan = forms.ChoiceField(label=_("Plan"),
        choices = PLANS)

    class Meta:
        model = Device
        fields = ('email',)

    def save(self, commit=True):
        device = super(NewForm, self).save(commit=False)
        if commit:
            device.save()
        return device
    
    