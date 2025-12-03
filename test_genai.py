import google.generativeai as genai
import time
import os
from dotenv import load_dotenv

load_dotenv()

# 1. Configuración de la API Key
# Lo ideal es tenerla en tus variables de entorno, o pégala directamente aquí
# os.environ["GOOGLE_API_KEY"] = "TU_API_KEY_AQUI"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])


def analizar_pdf_con_gemini(ruta_archivo, prompt_usuario):
    """
    Sube un PDF a la API de Gemini y realiza una consulta sobre él.
    """

    # --- PASO 1: Subir el archivo ---
    if not os.path.exists(ruta_archivo):
        print(f"Error: No se encontró el archivo '{ruta_archivo}'")
        return

    print(f"Subiendo {ruta_archivo} a la nube de Gemini...")
    archivo_subido = genai.upload_file(path=ruta_archivo, mime_type="application/pdf")
    print(f"Subida completada. URI: {archivo_subido.uri}")

    # --- PASO 2: Verificar estado del procesamiento ---
    # Los archivos grandes requieren un momento para ser procesados por Google
    while archivo_subido.state.name == "PROCESSING":
        print("Procesando el archivo...")
        time.sleep(2)
        archivo_subido = genai.get_file(archivo_subido.name)

    if archivo_subido.state.name == "FAILED":
        raise ValueError("El procesamiento del archivo ha fallado.")

    print("El archivo está activo y listo para el análisis.")

    # --- PASO 3: Generación de contenido ---
    model = genai.GenerativeModel(model_name="gemini-3-pro-preview")

    print("\nGenerando respuesta...")
    # Enviamos una lista que contiene el prompt (texto) y el objeto del archivo
    response = model.generate_content([prompt_usuario, archivo_subido])

    return response.text


# --- EJECUCIÓN ---
if __name__ == "__main__":
    # Asegúrate de cambiar esto por la ruta real de tu PDF
    mi_pdf = "/media/nicolas/DATA/Tecnomedia/Echevarne/2025.11.24 Muestras IA/Muestras/04/Documento 001.pdf"
    mi_pregunta = "Dame un resumen de esta petición."

    try:
        # Nota: Para probar esto, crea un archivo PDF ficticio o usa uno real
        resultado = analizar_pdf_con_gemini(mi_pdf, mi_pregunta)

        print("-" * 30)
        print("RESPUESTA DE GEMINI:")
        print("-" * 30)
        print(resultado)

    except Exception as e:
        print(f"Ocurrió un error: {e}")
