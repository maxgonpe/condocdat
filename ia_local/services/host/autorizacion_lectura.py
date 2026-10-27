"""
ARC003-B05-D01
Contrato portable de autorizacion de lectura.

- No ejecuta ORM.
- No invoca LLM.
- No modifica planes.
- No descubre automaticamente permisos.
- Rechaza por defecto.
- Solo admite conteos con una igualdad textual positiva.

La politica debe ser una funcion confiable suministrada
por el servidor anfitrion, nunca por Qwen o el navegador.

Esta version admite unicamente autorizacion explicita
del universo completo. No aplica alcances parciales.
"""

from copy import deepcopy

from ia_local.services.host.validador_plan_datos import (
    validar_plan_datos,
)


VERSION = "IA-ARC003-B05-D01-v1"

CLAVES_PLAN = {
    "modelo",
    "tabla",
    "operacion",
    "filtros",
    "orden",
    "limite",
    "condiciones_no_resueltas",
}

CLAVES_DECISION = {
    "permitido",
    "modelo",
    "operacion",
    "campos",
    "alcance",
}


def _rechazo(estado):
    return {
        "ok": False,
        "version": VERSION,
        "estado": estado,
        "autorizado": False,
        "ejecutable": False,
        "ejecutado": False,
    }


def autorizar_lectura(
    usuario,
    plan_host,
    *,
    politica=None,
):
    """
    Evalua una autorizacion de lectura.

    La politica es una dependencia confiable del servidor.

    No admite decisiones preconstruidas como sustituto
    de la politica.

    No autoriza ejecucion: devuelve exclusivamente
    una decision de lectura.
    """

    # --------------------------------------------------------
    # 1. Identidad
    # --------------------------------------------------------

    if (
        usuario is None
        or getattr(usuario, "is_authenticated", False)
            is not True
        or getattr(usuario, "is_active", False)
            is not True
        or getattr(usuario, "pk", None) is None
    ):
        return _rechazo("identidad_no_valida")

    # --------------------------------------------------------
    # 2. Politica obligatoria
    # --------------------------------------------------------

    if not callable(politica):
        return _rechazo("politica_no_disponible")

    # --------------------------------------------------------
    # 3. Contrato estructural
    # --------------------------------------------------------

    if (
        not isinstance(plan_host, dict)
        or set(plan_host) != CLAVES_PLAN
        or plan_host.get("operacion") != "contar"
        or plan_host.get("orden") != []
        or plan_host.get("condiciones_no_resueltas") != []
    ):
        return _rechazo("plan_fuera_de_alcance")

    filtros = plan_host.get("filtros")

    if (
        not isinstance(filtros, list)
        or len(filtros) != 1
        or not isinstance(filtros[0], dict)
    ):
        return _rechazo("filtros_fuera_de_alcance")

    filtro = filtros[0]

    if (
        filtro.get("operador") != "exact"
        or filtro.get("negado") is not False
        or filtro.get("tipo") not in ("CharField", "TextField")
        or filtro.get("lookup") != filtro.get("campo")
    ):
        return _rechazo("filtro_no_admitido")

    modelo = plan_host.get("modelo")
    campo = filtro.get("campo")

    if (
        not isinstance(modelo, str)
        or not modelo
        or not isinstance(campo, str)
        or not campo
    ):
        return _rechazo("identificadores_invalidos")

    # --------------------------------------------------------
    # 4. Revalidar con HOST
    # --------------------------------------------------------

    try:
        validacion = validar_plan_datos(
            deepcopy(plan_host)
        )
    except Exception:
        return _rechazo("validacion_host_no_disponible")

    if (
        not isinstance(validacion, dict)
        or validacion.get("ok") is not True
        or validacion.get("plan_validado") is not True
        or validacion.get("plan") != plan_host
    ):
        return _rechazo("plan_host_no_validado")

    # --------------------------------------------------------
    # 5. Invocar politica del anfitrion
    # --------------------------------------------------------

    try:
        decision = politica(
            usuario=usuario,
            modelo=modelo,
            operacion="contar",
            campos=(campo,),
            plan=deepcopy(plan_host),
        )
    except Exception:
        return _rechazo("error_politica")

    # --------------------------------------------------------
    # 6. Validar decision exacta
    # --------------------------------------------------------

    if (
        not isinstance(decision, dict)
        or set(decision) != CLAVES_DECISION
        or decision.get("permitido") is not True
        or decision.get("modelo") != modelo
        or decision.get("operacion") != "contar"
        or type(decision.get("campos")) is not list
        or decision.get("campos") != [campo]
        or decision.get("alcance") != "universo_completo"
    ):
        return _rechazo("acceso_no_autorizado")

    return {
        "ok": True,
        "version": VERSION,
        "estado": "lectura_autorizada",
        "autorizado": True,
        "modelo": modelo,
        "operacion": "contar",
        "campos": [campo],
        "alcance": "universo_completo",
        # Esta decision NO equivale a permiso de ejecucion.
        "ejecutable": False,
        "ejecutado": False,
    }
