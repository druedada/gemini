'''Connectar-nos a l'Api de Gemini i configurar Rol d'Analista'''
import os
import sys
import json
import time
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

    # 3. Configuració del rol i format de sortida: JSON natiu
    config_analista = {
        'temperature': 0.3,
        'top_p': 0.95,
        'max_output_tokens': 1200,
        'response_mime_type': 'application/json',
        'response_schema': {
            'type': 'OBJECT',
            'required': ['Veredicte', 'Semafor', 'Motiu'],
            'properties': {
                'Veredicte': {'type': 'STRING', 'enum': ['APTE', 'NO APTE']},
                'Semafor': {'type': 'STRING', 'enum': ['VERD', 'GROC', 'VERMELL']},
                'Motiu': {'type': 'STRING'},
            },
        },
        'system_instruction': (
            'Ets un analista de riscos bancaris. '\
            'Respon sempre en JSON vàlid amb les claus exactes: '\
            'Veredicte, Semafor, Motiu. No afegeixis text fora del JSON.'
        ),
    }

    ingressos_nets = 3200
    quotes_actuals = 100
    nova_quota = 500
    marge_supervivencia = 1400
    asnef = False
    contracte = 'Indefinit'

    prompt = f"""
Analitza la sol·licitud i respon en JSON vàlid.

Dades:
- Ingressos nets: {ingressos_nets}€
- Quotes actuals: {quotes_actuals}€
- Nova quota: {nova_quota}€
- Marge supervivència: {marge_supervivencia}€
- ASNEF: {'Si' if asnef else 'No'}
- Contracte: {contracte}

Criteris:
- VERD: DTI <=30% + capital >300€ + no ASNEF + contracte indefinit
- GROC: DTI 30-40% o capital 0-300€ o contracte temporal
- VERMELL: DTI >40% o capital negatiu o ASNEF Sí
"""

    if asnef:
        resultat = {
            'Veredicte': 'NO APTE',
            'Semafor': 'VERMELL',
            'Motiu': 'ASNEF Sí',
        }
        print(json.dumps(resultat, ensure_ascii=False, indent=2))
        sys.exit(0)

    # Reintent simple davant error temporal 503 del servei
    resposta = None
    max_intents = 3
    for intent in range(1, max_intents + 1):
        try:
            resposta = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=config_analista,
            )
            break
        except Exception as err:
            missatge = str(err)
            if '503' in missatge and intent < max_intents:
                time.sleep(intent)
                continue
            raise

    if resposta is None:
        raise RuntimeError('No s\'ha pogut obtenir resposta del model.')

    if hasattr(resposta, 'parsed') and resposta.parsed is not None:
        resultat = dict(resposta.parsed)
    else:
        resultat = json.loads(resposta.text)

    # Garantim claus esperades encara que el model respongui incomplet
    sortida = {
        'Veredicte': resultat.get('Veredicte'),
        'Semafor': resultat.get('Semafor'),
        'Motiu': resultat.get('Motiu'),
    }

    if hasattr(resposta, 'usage_metadata') and resposta.usage_metadata is not None:
        sortida['Tokens_gastats'] = resposta.usage_metadata.total_token_count

    print(json.dumps(sortida, ensure_ascii=False, indent=2))

except Exception as e:
    print(f"Error: {e} - No es genera resposta")