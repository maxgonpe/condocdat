from datetime import date

from django import forms

from .models import Transmital, TransmitalFolderConfig


class TransmitalForm(forms.ModelForm):
    FECHA_CARATULA_FIJA = date(2026, 1, 28)
    ESTATUS_CHOICES = (
        ("", "---------"),
        ("Para información", "Para información"),
        ("Para revisión", "Para revisión"),
        ("Otros", "Otros"),
    )

    class Meta:
        model = Transmital
        exclude = ["file", "imported_at", "updated_at", "consecutivo"]
        widgets = {
            "codigo_transmital": forms.TextInput(
                attrs={
                    "class": "transmital-input-lg",
                    "autocomplete": "off",
                    "spellcheck": "false",
                }
            ),
            "fecha_caratula": forms.DateInput(attrs={"type": "date"}),
            "fecha_envio": forms.DateInput(attrs={"type": "date"}),
            "referencia": forms.Textarea(attrs={"rows": 5, "class": "transmital-textarea-lg"}),
            "destinatario": forms.TextInput(attrs={"class": "transmital-input-lg"}),
            "empresa": forms.TextInput(attrs={"class": "transmital-input-lg"}),
            "emision": forms.TextInput(attrs={"class": "transmital-input-lg"}),
            "unidad_revisora": forms.TextInput(attrs={"class": "transmital-input-lg"}),
            "unidad_emisora": forms.TextInput(attrs={"class": "transmital-input-lg"}),
            "revision": forms.TextInput(attrs={"class": "transmital-input-lg"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "fecha_caratula" in self.fields:
            self.initial["fecha_caratula"] = self.FECHA_CARATULA_FIJA
            self.fields["fecha_caratula"].help_text = "Fecha fija: 28-01-2026"
        for i in range(1, Transmital.ITEM_COUNT + 1):
            name = f"item_{i:02d}_documento"
            if name in self.fields:
                self.fields[name].widget.attrs.setdefault(
                    "class", "transmital-item-doc"
                )
                self.fields[name].required = False
            estatus_name = f"item_{i:02d}_estatus"
            if estatus_name in self.fields:
                self.fields[estatus_name].widget = forms.Select(
                    choices=self.ESTATUS_CHOICES
                )

    def clean_fecha_caratula(self):
        # Regla operativa: carátula siempre fija al 28-01-2026.
        return self.FECHA_CARATULA_FIJA


class TransmitalFolderConfigForm(forms.ModelForm):
    class Meta:
        model = TransmitalFolderConfig
        fields = ["base_path", "current_number"]
