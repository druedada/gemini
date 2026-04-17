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
        'max_output_tokens': 800, # Limit de llargada de la resposta
        'system_instruction': (
            "Ets un analista de riscos professionals. "
            "La teva feina és identificar amenaces i vulnerabilitats. "
            "Sempre respon amb un to seriós, tècnic i estructura la "
            "informació en una taula Markdown amb columnes: 'Risc', 'Probabilitat' i 'Impacte'."
        )
    }

    prompt = """Ets un expert en scoring bancari. Analitza una sol·licitud de préstec personal aplicant
                aquests criteris exactes:
                DADES OBLIGATORIES:
                - Ingressos nets mensuals titular/cotitulars: 3200€ (2000€ titular + 1200€ cotitular)
                - Quotes actuals de deutes: 800€
                - Quota del nou préstec sol·licitat: 1200€
                - Marge de supervivència (900€ persona sol·itària, 1400€ parella, +200€ per fill): 1400€ (parella sense fills)
                - ASNEF: Sí/No: No
                - Tipus contracte: Indefinit/Temporal/Autònom: Indefinit
                - Nombre cotitulars: 1/2: 2
                CÀLCULS QUE HAS DE FER:
                1. Ràtio endeutament DTI = (Quotes actuals + Nova quota) / Ingressos nets * 100
                2. Capital disponible = Ingressos nets - Total quotes - Marge supervivència
                SEMÀFOR DE DECISIÓ:
                - VERD: DTI ≤30% + Capital >300€ + No ASNEF + Contracte indefinit
                - GROC: DTI 30-40% O capital 0-300€ O contracte temporal
                - VERMELL: DTI >40% O capital negatiu O ASNEF Sí"""

    # 4. Petició a la API amb el model Flash i la nostra config
    resposta = client.models.generate_content(
        model='gemini-2.0-flash', # Model estàndard segons instruccions
        contents=prompt,
        config=config_analista
    )

    print(f"\n{5*'='} ANÀLISI DE RISC OBTINGUT {5*'='}")
    print(f"{resposta.text}\n")
    print(f"Tokens gastats: {resposta.usage_metadata.total_token_count}")

except Exception as e:
    print(f"Error: {e} - No es genera resposta")