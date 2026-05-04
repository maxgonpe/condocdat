from django import forms

from .models import GanttTask


class GanttTaskForm(forms.ModelForm):
    class Meta:
        model = GanttTask
        fields = [
            "nombre_tarea",
            "esp",
            "especialidad",
            "duracion",
            "avance_planificado",
            "trabajo_completado",
            "comienzo",
            "fin",
            "predecesoras",
            "sucesoras",
            "notas",
            "wbs",
            "outline_number",
        ]
        widgets = {
            "comienzo": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "fin": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "predecesoras": forms.Textarea(attrs={"rows": 2}),
            "sucesoras": forms.Textarea(attrs={"rows": 2}),
            "notas": forms.Textarea(attrs={"rows": 4}),
            "nombre_tarea": forms.Textarea(attrs={"rows": 2}),
            "avance_planificado": forms.NumberInput(
                attrs={"step": "0.01", "min": "0", "max": "100"}
            ),
            "trabajo_completado": forms.NumberInput(
                attrs={"step": "0.01", "min": "0", "max": "100"}
            ),
        }
