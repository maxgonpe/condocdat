from datetime import date, datetime

from django import forms

from .models import (
    EquiposAsset,
    EquiposLocation,
    EquiposOtro,
    EquiposResumenFila,
    EquiposSignificadoFila,
)

# Estados editables desde formulario (deben coincidir con lo que se guarda en BD/Excel).
ESTADO_EQUIPOS_FORM_CHOICES = [
    ("", "(sin estado)"),
    ("En Obra", "En Obra"),
    ("Comprado", "Comprado"),
    ("En Proceso Compra", "En Proceso Compra"),
    ("En Revision Odata", "En Revision Odata"),
    ("En revision Propamat", "En revision Propamat"),
]

_ESTADO_FORM_VALUES = frozenset(c[0] for c in ESTADO_EQUIPOS_FORM_CHOICES)

UNIT_EQUIPOS_FORM_CHOICES = [
    ("", "(sin unidad)"),
    ("uni", "uni"),
    ("mts", "mts"),
]
_UNIT_FORM_VALUES = frozenset(c[0] for c in UNIT_EQUIPOS_FORM_CHOICES)

CON_OC_EQUIPOS_FORM_CHOICES = [
    ("", "(sin indicar)"),
    ("Si", "Si"),
    ("No", "No"),
]
_CON_OC_FORM_VALUES = frozenset(c[0] for c in CON_OC_EQUIPOS_FORM_CHOICES)


def parse_equipos_fecha_cadena(raw) -> date | None:
    """Interpreta texto/fecha de Excel o BD para rellenar un <input type=\"date\">."""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    s = str(raw).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            part = s[:10] if fmt == "%Y-%m-%d" else s
            return datetime.strptime(part, fmt).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def _append_legacy_choice_if_needed(form, field_name: str, base_choices, allowed: frozenset) -> None:
    cur = (getattr(form.instance, field_name) or "").strip()
    if cur and cur not in allowed:
        form.fields[field_name].choices = list(base_choices) + [(cur, cur)]


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
    estado = forms.ChoiceField(
        choices=ESTADO_EQUIPOS_FORM_CHOICES,
        required=False,
    )
    unit = forms.ChoiceField(
        choices=UNIT_EQUIPOS_FORM_CHOICES,
        required=False,
    )
    con_oc = forms.ChoiceField(
        choices=CON_OC_EQUIPOS_FORM_CHOICES,
        required=False,
    )

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
            "avance_montaje",
            "avance_conexion",
        ]
        widgets = {
            "fecha_compra": forms.DateInput(
                format="%Y-%m-%d", attrs={"type": "date"}
            ),
            "fecha_llegada_obra": forms.DateInput(
                format="%Y-%m-%d", attrs={"type": "date"}
            ),
            "fecha_planificacion": forms.DateInput(
                format="%Y-%m-%d", attrs={"type": "date"}
            ),
            "asset_name": forms.Textarea(attrs={"rows": 2}),
            "space_room": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for fname in ("fecha_compra", "fecha_llegada_obra", "fecha_planificacion"):
            f = self.fields.get(fname)
            if f is not None:
                f.widget.format = "%Y-%m-%d"
                f.input_formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"]
        _append_legacy_choice_if_needed(
            self, "estado", ESTADO_EQUIPOS_FORM_CHOICES, _ESTADO_FORM_VALUES
        )
        _append_legacy_choice_if_needed(
            self, "unit", UNIT_EQUIPOS_FORM_CHOICES, _UNIT_FORM_VALUES
        )
        _append_legacy_choice_if_needed(
            self, "con_oc", CON_OC_EQUIPOS_FORM_CHOICES, _CON_OC_FORM_VALUES
        )


class EquiposOtroForm(forms.ModelForm):
    estado = forms.ChoiceField(
        choices=ESTADO_EQUIPOS_FORM_CHOICES,
        required=False,
    )
    con_oc = forms.ChoiceField(
        choices=CON_OC_EQUIPOS_FORM_CHOICES,
        required=False,
    )
    fecha_envio_rdi = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        input_formats=["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"],
    )
    fecha_respuesta_rdi = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        input_formats=["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"],
    )

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _append_legacy_choice_if_needed(
            self, "estado", ESTADO_EQUIPOS_FORM_CHOICES, _ESTADO_FORM_VALUES
        )
        _append_legacy_choice_if_needed(
            self, "con_oc", CON_OC_EQUIPOS_FORM_CHOICES, _CON_OC_FORM_VALUES
        )
        for fn in ("fecha_envio_rdi", "fecha_respuesta_rdi"):
            d = parse_equipos_fecha_cadena(getattr(self.instance, fn, None))
            if d:
                self.initial[fn] = d

    def save(self, commit=True):
        inst = super().save(commit=False)
        for fn in ("fecha_envio_rdi", "fecha_respuesta_rdi"):
            d = self.cleaned_data.get(fn)
            setattr(inst, fn, "" if d is None else d.isoformat())
        if commit:
            inst.save()
            self.save_m2m()
        return inst
