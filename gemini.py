'''Connectar-nos a l'Api de Gemini i configurar Rol d'Analista'''
import os
import sys
from dotenv import load_dotenv
from google import genai

# 1. Carreguem la clau des del fitxer .env
load_dotenv()
CLAU = os.getenv('KEYAPI')

if CLAU is None:
    print("Alguna cosa no ha anat bé en el procés d'agafar la clau!!")
    sys.exit(1)

# 2. Creem el client
try:
    client = genai.Client(api_key=CLAU)
    
    # 3. Definim la configuració del Rol d'Analista de Risc
    # Aquí responem al punt de "configuracions de la IA del generate_content"
    config_analista = {
        'temperature': 0.3,      # Baixa per ser precisos i no inventar (Instruccions txt)
        'top_p': 0.95,           # Flux natural de paraules
        'max_output_tokens': 1200, # Limit de llargada de la resposta
        'system_instruction': (
        "Ets un analista de riscos bancaris. "
        "Respon NOMÉS amb aquest format, sense introducció ni càlculs detallats:\n"
        "Veredicte: APTE / NO APTE\n"
        "Semàfor: VERD / GROC / VERMELL\n"
        "Motiu: una sola frase breu.\n"
        "No afegeixis cap altre text."
        )
    }

    ingressos_nets = 3200
    quotes_actuals = 100
    nova_quota = 500
    marge_supervivencia = 1400
    asnef = False
    contracte = "Indefinit"
    

    prompt = f"""
    Analitza la sol·licitud i respon només amb:
    Veredicte: APTE o NO APTE
    Semàfor: VERD, GROC o VERMELL
    Motiu: una sola frase breu

    Dades:
    - Ingressos nets: {ingressos_nets}€
    - Quotes actuals: {quotes_actuals}€
    - Nova quota: {nova_quota}€
    - Marge supervivència: {marge_supervivencia}€
    - ASNEF: {'Si' if asnef else 'No'}
    - Contracte: {contracte}

    Criteris:
    - VERD: DTI ≤30% + capital >300€ + no ASNEF + contracte indefinit
    - GROC: DTI 30-40% o capital 0-300€ o contracte temporal
    - VERMELL: DTI >40% o capital negatiu o ASNEF Sí
    """

    # 4. Petició a la API amb el model Flash i la nostra config
    if asnef:
        resposta = "NO APTE, VERMELL, ASNEF Sí"
    else:
        resposta = client.models.generate_content(
            model='gemini-2.5-flash', # Model estàndard segons instruccions
            contents=prompt,
            config=config_analista
        )

    print(f"\n{5*'='} ANÀLISI DE RISC OBTINGUT {5*'='}")
    if isinstance(resposta, str):
        print(f"{resposta}\n")
    else:
        print(f"{resposta.text}\n")
        print(f"Tokens gastats: {resposta.usage_metadata.total_token_count}")

except Exception as e:
    print(f"Error: {e} - No es genera resposta")