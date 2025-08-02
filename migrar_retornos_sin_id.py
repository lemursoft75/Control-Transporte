import json
import os
from datetime import datetime

CALENDAR_PATH = os.path.join("data", "calendar.json")

def cargar_calendario():
    with open(CALENDAR_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_calendario(calendar):
    with open(CALENDAR_PATH, "w", encoding="utf-8") as f:
        json.dump(calendar, f, indent=2)

def migrar_retornos(calendar):
    # 1. Indexar entregas: (unidad, cliente, fecha) => id
    entregas_index = {}
    for fecha_str, eventos in calendar.items():
        for evento in eventos:
            if evento.get("tipo_evento") == "entrega":
                clave = (
                    evento["unidad"],
                    evento["cliente"],
                    evento["fecha_pedido"]
                )
                entregas_index[clave] = evento.get("id")

    cambios_realizados = 0

    # 2. Revisar retornos sin `id_entrega_asociada`
    for fecha_str, eventos in calendar.items():
        for evento in eventos:
            if evento.get("tipo_evento") == "retorno" and "id_entrega_asociada" not in evento:
                unidad = evento["unidad"]
                cliente = evento.get("cliente_asociado", "Desconocido")
                fecha_pedido = evento.get("fecha_pedido_asociado")

                clave = (unidad, cliente, fecha_pedido)
                id_asociado = entregas_index.get(clave)

                if id_asociado:
                    evento["id_entrega_asociada"] = id_asociado
                    cambios_realizados += 1
                else:
                    print(f"⚠️ No se pudo asociar retorno: {clave}")

    return calendar, cambios_realizados

if __name__ == "__main__":
    print("📁 Cargando calendario...")
    calendario = cargar_calendario()
    calendario_migrado, cambios = migrar_retornos(calendario)
    guardar_calendario(calendario_migrado)
    print(f"✅ Migración completada. {cambios} retornos actualizados.")
