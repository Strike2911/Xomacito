import re
import unicodedata

def clean_filename_text(text, clean_emojis=True):
    """
    Sanitiza texto para usarlo de forma segura como nombre de archivo.
    
    Args:
        text (str): El texto original (título, nombre de archivo).
        clean_emojis (bool): Si es True, elimina emojis y símbolos gráficos.
        
    Returns:
        str: El texto limpio.
    """
    if not text:
        return ""

    # 1. Normalizar Unicode (NFC es el estándar más compatible)
    text = unicodedata.normalize('NFC', text)

    if clean_emojis:
        # 2. Filtrar por categorías Unicode
        # Lo (Letter Other): Japonés, Chino, Coreano, etc. -> MANTENER
        # Ll, Lu, Lt, Lm (Letras): -> MANTENER
        # Nd (Números): -> MANTENER
        # Zs (Espacios): -> MANTENER
        # P (Puntuación): -> MANTENER
        # So (Symbol other): Emojis, símbolos -> ELIMINAR si clean_emojis es True
        # Cn (Unassigned): -> ELIMINAR
        
        cleaned_chars = []
        for char in text:
            category = unicodedata.category(char)
            
            # Mantener si es letra, número, puntuación o espacio
            if category.startswith(('L', 'N', 'P', 'Z')):
                cleaned_chars.append(char)
            # Eliminar si es símbolo (So) o no asignado (Cn)
            elif category in ('So', 'Cn'):
                continue
            # Por defecto mantener otros (ej: marcas combinadas Mc, Me, Mn)
            else:
                cleaned_chars.append(char)
                
        text = "".join(cleaned_chars)

    # 3. Eliminar caracteres prohibidos por el sistema de archivos (Windows/Mac)
    # Eliminar caracteres que los sistemas de archivos no permiten.
    forbidden_chars = r'[\\/:\*\?"<>|]'
    text = re.sub(forbidden_chars, '', text)

    # 4. Normalizar espacios (eliminar dobles espacios resultantes de la limpieza)
    text = re.sub(r'\s+', ' ', text).strip()

    # 5. Eliminar puntos y espacios al final (Windows no los permite en archivos)
    text = text.rstrip('. ')

    # 6. Límite de longitud recomendado para rutas estables.
    if len(text) > 150:
        text = text[:147] + "..."

    return text or "Sin Titulo"
