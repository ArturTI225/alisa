from django import forms


class MessageForm(forms.Form):
    text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Scrie mesajul..."}),
        label="Mesaj",
    )
    attachment = forms.FileField(required=False, label="Fișier (opțional)")
