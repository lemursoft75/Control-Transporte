# utils/calendar_logic.py

import json
from datetime import datetime, timedelta


def agregar_pedido(calendar, units, cliente, unidad, fecha_pedido, dias_retorno):
    fecha_str = fecha_pedido.strftime("%Y-%m-%d")

    # Verificar disponibilidad
    if units[unidad] > 0:
        # Descontar la unidad
        units[unidad] -= 1

        # Generar un ID único para el pedido (útil para eliminar)
        pedido_id = f"{cliente}-{unidad}-{fecha_pedido.strftime('%Y%m%d%H%M%S')}"

        # --- INICIO: Lógica para ajustar días de retorno si la carga es en sábado y dias_retorno <= 2 ---
        dias_retorno_ajustados = dias_retorno

        # Solo aplica el ajuste si los días de retorno ORIGINALES son 2 o menos
        if dias_retorno <= 2:  # <--- CAMBIO AQUÍ: de >= 3 a <= 2
            # Si la fecha de pedido (carga) es sábado (weekday() == 5)
            if fecha_pedido.weekday() == 5:  # Lunes es 0, Martes 1, ..., Sábado 5, Domingo 6
                dias_retorno_ajustados += 1  # Incrementa un día para que el retorno no sea el domingo
        # --- FIN: Lógica para ajustar días de retorno si la carga es en sábado y dias_retorno <= 2 ---

        # Registrar el pedido de ENTREGA (o carga)
        pedido = {
            "id": pedido_id,
            "cliente": cliente,
            "unidad": unidad,
            "dias_retorno": dias_retorno,  # Guardamos los días originales del Excel
            "dias_retorno_calculados": dias_retorno_ajustados,  # <-- ACTUALIZADO: Días con ajuste condicional
            "fecha_pedido": fecha_str,
            "tipo_evento": "entrega"
        }

        # Agregar al día del pedido
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
    else:
        return False, f"No hay unidades disponibles de tipo {unidad} para el día seleccionado."


def eliminar_pedido(calendar, units, pedido_id_a_eliminar):
    """
    Elimina un pedido y su evento de retorno asociado del calendario,
    y devuelve la unidad al pool de disponibles.
    """
    unidad_liberada = None
    pedido_encontrado = False

    # Itera sobre una copia de los items para poder modificar el calendario mientras iteras
    for fecha_str, eventos in list(calendar.items()):
        eventos_filtrados = []
        for evento in eventos:
            if evento.get("id") == pedido_id_a_eliminar and evento.get("tipo_evento") == "entrega":
                # Este es el pedido a eliminar
                unidad_liberada = evento["unidad"]
                pedido_encontrado = True
                # No añadirlo a eventos_filtrados para eliminarlo
            elif evento.get("tipo_evento") == "retorno" and evento.get("pedido_id_asociado") == pedido_id_a_eliminar:
                # Este es el evento de retorno asociado al pedido
                # No añadirlo a eventos_filtrados para eliminarlo
                pass
            else:
                eventos_filtrados.append(evento)  # Mantener otros eventos

        calendar[fecha_str] = eventos_filtrados

        # Si el día queda vacío después de eliminar, puedes optar por borrar la clave
        if not calendar[fecha_str]:
            del calendar[fecha_str]

    if pedido_encontrado and unidad_liberada:
        # Devolver la unidad al pool de disponibles
        units[unidad_liberada] += 1
        return True, f"Pedido {pedido_id_a_eliminar} y su retorno eliminados. Unidad '{unidad_liberada}' devuelta a disponibles."
    else:
        return False, f"Pedido {pedido_id_a_eliminar} no encontrado o ya eliminado."


def editar_dias_retorno(calendar, units, pedido_id_a_editar, nuevos_dias_retorno):
    """
    Edita los días de retorno de un pedido, ajusta su evento de retorno en el calendario
    y asegura que la unidad no se pierda o se duplique.
    """
    pedido_original = None

    # 1. Encontrar el pedido original
    for fecha_str, eventos in calendar.items():
        for evento in eventos:
            if evento.get("id") == pedido_id_a_editar and evento.get("tipo_evento") == "entrega":
                pedido_original = evento
                break
        if pedido_original:
            break

    if not pedido_original:
        return False, f"Pedido {pedido_id_a_editar} no encontrado para editar."

    # Obtener la fecha de carga como objeto date
    fecha_carga_dt = datetime.strptime(pedido_original["fecha_pedido"], "%Y-%m-%d").date()

    # Calcular la antigua fecha de retorno usando los días_retorno_calculados si existen, sino dias_retorno
    antiguos_dias_calculados = pedido_original.get("dias_retorno_calculados", pedido_original["dias_retorno"])
    antigua_fecha_retorno_str = (fecha_carga_dt + timedelta(days=antiguos_dias_calculados)).strftime("%Y-%m-%d")

    # 2. Remover el antiguo evento de retorno asociado a este pedido
    if antigua_fecha_retorno_str in calendar:
        calendar[antigua_fecha_retorno_str] = [
            e for e in calendar[antigua_fecha_retorno_str]
            if not (e.get("tipo_evento") == "retorno" and e.get("pedido_id_asociado") == pedido_id_a_editar)
        ]
        # Si el día queda vacío, elimina la clave
        if not calendar[antigua_fecha_retorno_str]:
            del calendar[antigua_fecha_retorno_str]

    # 3. Actualizar los días de retorno del pedido original (mantenemos los originales para referencia)
    pedido_original["dias_retorno"] = nuevos_dias_retorno

    # --- INICIO: Recalcular días de retorno ajustados para la edición con la nueva condición ---
    nuevos_dias_retorno_ajustados = nuevos_dias_retorno

    # Solo aplica el ajuste si los nuevos días de retorno son 2 o menos
    if nuevos_dias_retorno <= 2:  # <--- CAMBIO AQUÍ: de >= 3 a <= 2
        # Si la fecha de pedido (carga) es sábado (weekday() == 5)
        if fecha_carga_dt.weekday() == 5:
            nuevos_dias_retorno_ajustados += 1  # Incrementa un día

    pedido_original["dias_retorno_calculados"] = nuevos_dias_retorno_ajustados  # ACTUALIZA ESTE CAMPO
    # --- FIN: Recalcular días de retorno ajustados para la edición con la nueva condición ---

    # 4. Calcular y añadir el nuevo evento de retorno
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
    fecha_str = fecha_actual.strftime("%Y-%m-%d")
    eventos = calendar.get(fecha_str, [])

    for evento in eventos:
        if evento.get("tipo_evento") == "retorno":
            unidad = evento["unidad"]
            units[unidad] += 1