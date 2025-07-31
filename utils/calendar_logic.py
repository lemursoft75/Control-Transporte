from datetime import datetime, timedelta

def agregar_pedido(calendar, units, cliente, unidad, fecha_pedido, dias_retorno):
    fecha_str = fecha_pedido.strftime("%Y-%m-%d")

    # Generar un ID único para el pedido (útil para eliminar)
    pedido_id = f"{cliente}-{unidad}-{fecha_pedido.strftime('%Y%m%d%H%M%S')}"

    # --- INICIO: Lógica para ajustar días de retorno si la carga es en sábado y dias_retorno <= 2 ---
    dias_retorno_ajustados = dias_retorno
    if dias_retorno <= 2:
        if fecha_pedido.weekday() == 5:  # Sábado
            dias_retorno_ajustados += 1
    # --- FIN: Lógica para ajustar días de retorno si la carga es en sábado y dias_retorno <= 2 ---

    # Registrar el pedido de ENTREGA (o carga)
    pedido = {
        "id": pedido_id,
        "cliente": cliente,
        "unidad": unidad,
        "dias_retorno": dias_retorno,
        "dias_retorno_calculados": dias_retorno_ajustados,
        "fecha_pedido": fecha_str,
        "tipo_evento": "entrega"
    }

    calendar.setdefault(fecha_str, []).append(pedido)

    # Calcular y registrar retorno usando los días ajustados
    fecha_retorno = fecha_pedido + timedelta(days=dias_retorno_ajustados)
    retorno_str = fecha_retorno.strftime("%Y-%m-%d")
    calendar.setdefault(retorno_str, []).append({
        "id": f"retorno-{pedido_id}",
        "tipo_evento": "retorno",
        "unidad": unidad,
        "pedido_id_asociado": pedido_id,
        "cliente_asociado": cliente,
        "fecha_pedido_asociado": fecha_str
    })

    return True, f"Pedido registrado para {cliente} con unidad {unidad}. Retorno en {dias_retorno_ajustados} días."


def eliminar_pedido(calendar, units, pedido_id_a_eliminar):
    """
    Elimina un pedido y su evento de retorno asociado del calendario.
    """
    unidad_liberada = None
    pedido_encontrado = False

    for fecha_str, eventos in list(calendar.items()):
        eventos_filtrados = []
        for evento in eventos:
            if evento.get("id") == pedido_id_a_eliminar and evento.get("tipo_evento") == "entrega":
                unidad_liberada = evento["unidad"]
                pedido_encontrado = True
            elif evento.get("tipo_evento") == "retorno" and evento.get("pedido_id_asociado") == pedido_id_a_eliminar:
                pass
            else:
                eventos_filtrados.append(evento)

        calendar[fecha_str] = eventos_filtrados

        if not calendar[fecha_str]:
            del calendar[fecha_str]

    if pedido_encontrado and unidad_liberada:
        return True, f"Pedido {pedido_id_a_eliminar} y su retorno eliminados."
    else:
        return False, f"Pedido {pedido_id_a_eliminar} no encontrado o ya eliminado."


def editar_dias_retorno(calendar, units, pedido_id_a_editar, nuevos_dias_retorno):
    """
    Edita los días de retorno de un pedido, ajusta su evento de retorno en el calendario.
    """
    pedido_original = None
    for fecha_str, eventos in calendar.items():
        for evento in eventos:
            if evento.get("id") == pedido_id_a_editar and evento.get("tipo_evento") == "entrega":
                pedido_original = evento
                break
        if pedido_original:
            break

    if not pedido_original:
        return False, f"Pedido {pedido_id_a_editar} no encontrado para editar."

    fecha_carga_dt = datetime.strptime(pedido_original["fecha_pedido"], "%Y-%m-%d").date()
    antiguos_dias_calculados = pedido_original.get("dias_retorno_calculados", pedido_original["dias_retorno"])
    antigua_fecha_retorno_str = (fecha_carga_dt + timedelta(days=antiguos_dias_calculados)).strftime("%Y-%m-%d")

    if antigua_fecha_retorno_str in calendar:
        calendar[antigua_fecha_retorno_str] = [
            e for e in calendar[antigua_fecha_retorno_str]
            if not (e.get("tipo_evento") == "retorno" and e.get("pedido_id_asociado") == pedido_id_a_editar)
        ]
        if not calendar[antigua_fecha_retorno_str]:
            del calendar[antigua_fecha_retorno_str]

    pedido_original["dias_retorno"] = nuevos_dias_retorno
    nuevos_dias_retorno_ajustados = nuevos_dias_retorno

    if nuevos_dias_retorno <= 2:
        if fecha_carga_dt.weekday() == 5:
            nuevos_dias_retorno_ajustados += 1

    pedido_original["dias_retorno_calculados"] = nuevos_dias_retorno_ajustados
    nueva_fecha_retorno = fecha_carga_dt + timedelta(days=nuevos_dias_retorno_ajustados)
    nueva_fecha_retorno_str = nueva_fecha_retorno.strftime("%Y-%m-%d")

    calendar.setdefault(nueva_fecha_retorno_str, []).append({
        "id": f"retorno-{pedido_original['id']}",
        "tipo_evento": "retorno",
        "unidad": pedido_original["unidad"],
        "pedido_id_asociado": pedido_original["id"],
        "cliente_asociado": pedido_original["cliente"],
        "fecha_pedido_asociado": pedido_original["fecha_pedido"]
    })

    return True, f"Días de retorno para pedido {pedido_id_a_editar} actualizados a {nuevos_dias_retorno} días (calculado: {nuevos_dias_retorno_ajustados} días)."


def actualizar_disponibilidad(calendar, units, fecha_actual):
    # Esta función ahora no tiene funcionalidad, el cálculo se hace en el main.py
    pass