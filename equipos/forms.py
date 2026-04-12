from django import forms

from .models import (
    EquiposAsset,
    EquiposLocation,
    EquiposOtro,
    EquiposResumenFila,
    EquiposSignificadoFila,
)


class EquiposResumenFilaForm(forms.ModelForm):
    class Meta:
        model = EquiposResumenFila
        fields = ["etiqueta", "cuenta", "fraccion"]


class EquiposSignificadoFilaForm(forms.ModelForm):
    class Meta:
        model = EquiposSignificadoFila
        fields = ["flujo", "status", "significado"]


class EquiposLocationForm(forms.ModelForm):
    class Meta:
        model = EquiposLocation
        fields = [
            "campus",
            "building",
            "zones",
            "floors",
            "space_name",
            "fase",
            "area_m2",
            "code",
        ]


class EquiposAssetForm(forms.ModelForm):
    class Meta:
        model = EquiposAsset
        fields = [
            "row_type",
            "tipe",
            "especialidad",
            "tag_number",
            "asset_name",
            "space_room",
            "unit",
            "quantity",
            "phase",
            "zones",
            "proveedor",
            "vendor",
            "estado",
            "con_oc",
            "fecha_compra",
            "rdi_ttal",
            "fecha_llegada_obra",
            "fecha_planificacion",
            "cumple",
            "dias",
            "avance_montaje",
            "avance_conexion",
        ]
        widgets = {
            "fecha_compra": forms.DateInput(attrs={"type": "date"}),
            "fecha_llegada_obra": forms.DateInput(attrs={"type": "date"}),
            "fecha_planificacion": forms.DateInput(attrs={"type": "date"}),
            "asset_name": forms.Textarea(attrs={"rows": 2}),
            "space_room": forms.Textarea(attrs={"rows": 2}),
        }


class EquiposOtroForm(forms.ModelForm):
    class Meta:
        model = EquiposOtro
        fields = [
            "row_type",
            "tipe",
            "especialidad",
            "tag_number",
            "asset_name",
            "estado",
            "rdi_ttal",
            "fecha_envio_rdi",
            "fecha_respuesta_rdi",
            "con_oc",
        ]
        widgets = {
            "asset_name": forms.Textarea(attrs={"rows": 2}),
        }
