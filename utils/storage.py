import json
import os
import pandas as pd # Necesitamos pandas para manejar DataFrames

# --- Rutas base de los archivos JSON ---
UNITS_PATH = os.path.join("data", "units.json")
CALENDAR_PATH = os.path.join("data", "calendar.json")
PEDIDOS_EXCEL_PATH = os.path.join("data", "pedidos_excel_guardados.json") # Nueva ruta para los pedidos del Excel

# --- Utilidad genérica para asegurar que el directorio y el archivo existen ---
def _asegurar_directorio_y_archivo(path, estructura_inicial):
    """
    Asegura que el directorio del archivo exista y crea el archivo
    con una estructura inicial si no existe.
    """
    dir_name = os.path.dirname(path)
    if dir_name: # Solo si hay un directorio especificado (e.g., "data/...")
        os.makedirs(dir_name, exist_ok=True) # Crea el directorio si no existe

    if not os.path.exists(path):
        with open(path, "w", encoding='utf-8') as f: # Usa utf-8 para consistencia
            json.dump(estructura_inicial, f, indent=2) # Añadido indent para legibilidad

# --- Funciones para Unidades ---
def load_units():
    """Carga las unidades disponibles desde units.json. Crea el archivo si no existe."""
    _asegurar_directorio_y_archivo(UNITS_PATH, {
        "Tráiler 53": 0,
        "Tráiler 48": 0,
        "Torton": 0,
        "Interplanta": 0
    })
    with open(UNITS_PATH, "r", encoding='utf-8') as f:
        return json.load(f)

def save_units(data):
    """Guarda las unidades actualizadas en units.json."""
    # El directorio ya debería existir por load_units o la llamada inicial de _asegurar_directorio_y_archivo
    with open(UNITS_PATH, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=2)

# --- Funciones para Calendario ---
def load_calendar():
    """Carga el calendario completo desde calendar.json. Crea el archivo si no existe."""
    _asegurar_directorio_y_archivo(CALENDAR_PATH, {}) # Estructura inicial: diccionario vacío
    with open(CALENDAR_PATH, "r", encoding='utf-8') as f:
        return json.load(f)

def save_calendar(data):
    """Guarda el calendario actualizado en calendar.json."""
    with open(CALENDAR_PATH, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=2)

# --- ¡Nuevas Funciones para Pedidos de Excel Persistentes! ---
def load_pedidos_excel():
    """
    Carga los pedidos de Excel guardados desde un archivo JSON.
    Retorna un DataFrame de pandas o None si no hay datos/archivo.
    """
    _asegurar_directorio_y_archivo(PEDIDOS_EXCEL_PATH, []) # Estructura inicial: lista vacía
    with open(PEDIDOS_EXCEL_PATH, "r", encoding='utf-8') as f:
        try:
            data = json.load(f)
            # Asegúrate de que 'data' sea una lista, ya que 'orient="records"' espera eso
            if isinstance(data, list):
                return pd.DataFrame(data)
            else:
                # Si el JSON no es una lista de diccionarios, es un formato inesperado
                return pd.DataFrame() # Retorna un DataFrame vacío
        except json.JSONDecodeError:
            # Si el archivo está vacío o corrupto, retorna un DataFrame vacío
            return pd.DataFrame() # O None, dependiendo de tu preferencia

def save_pedidos_excel(df: pd.DataFrame):
    """
    Guarda un DataFrame de pedidos de Excel en un archivo JSON.
    """
    _asegurar_directorio_y_archivo(PEDIDOS_EXCEL_PATH, []) # Asegura que el archivo exista antes de intentar escribir
    with open(PEDIDOS_EXCEL_PATH, "w", encoding='utf-8') as f:
        # Convertir DataFrame a lista de diccionarios para guardar en JSON
        json.dump(df.to_dict(orient="records"), f, indent=2)