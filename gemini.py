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
    # Introdueix les dades del client aqui:
    ingressos_nets = 3000
    quotes_actuals = 100
    nova_quota = 500
    marge_supervivencia = 1400
    asnef = False
    titulars = 1 # Nombre de titulars (1 o 2)
    fills = 0 # Nombre de fills a càrrec
    contracte = 'Indefinit' # Pot ser 'Indefinit', 'Temporal' o 'Autonom'

    # Calculem el rati d'endeutament
    total_quotes_mensuals = quotes_actuals + nova_quota
    rati_endeutament = (total_quotes_mensuals / ingressos_nets) * 100

    prompt = f"""
    Analitza la sol·licitud i respon en JSON vàlid.

    Dades:
    - Ingressos nets: {ingressos_nets}€
    - Quotes actuals: {quotes_actuals}€
    - Nova quota: {nova_quota}€
    - Total quotes mensuals de deutes: {total_quotes_mensuals}€
    - Marge supervivència: {marge_supervivencia}€
    - ASNEF: {'Si' if asnef else 'No'}
    - Contracte: {contracte}
    - Titulars: {titulars}
    - Fills a càrrec: {fills}

    - Rati endeutament: {rati_endeutament:.2f}%

    Criteris:
    - VERD: DTI <=30% + capital >300€ + no ASNEF + contracte indefinit
    - GROC: DTI 30-40% o capital 0-300€ o contracte temporal
    - VERMELL: DTI >40% o capital negatiu o ASNEF Sí
    """

    # ? Apliquem regles bàsiques abans de consultar el model per evitar costos innecessaris en casos clarament no aptes
    # Si el client està a Asnef --> No apte directe sense consultar el model
    if asnef:
        resultat = {
            'Veredicte': 'NO APTE',
            'Semafor': 'VERMELL',
            'Motiu': 'ASNEF Sí',
            'Rati_endeutament': round(rati_endeutament, 2),
        }
        print(json.dumps(resultat, ensure_ascii=False, indent=2))
        sys.exit(0)
        
    elif rati_endeutament > 40:
        resultat = {
            'Veredicte': 'NO APTE',
            'Semafor': 'VERMELL',
            'Motiu': f'Rati endeutament alt: {rati_endeutament:.2f}%',
            'Rati_endeutament': round(rati_endeutament, 2),
        }
        print(json.dumps(resultat, ensure_ascii=False, indent=2))
        sys.exit(0)
    elif (marge_supervivencia < (900 + fills * 200) and titulars == 1) or (marge_supervivencia < (1500 + fills * 200) and titulars == 2):
        resultat = {
            'Veredicte': 'NO APTE',
            'Semafor': 'VERMELL',
            'Motiu': f'Marge de supervivència insuficient: {marge_supervivencia}€ (mínim requerit: {(900 + fills * 200) if titulars == 1 else (1500 + fills * 200)}€)',
            'Rati_endeutament': round(rati_endeutament, 2),
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
        'Rati_endeutament': round(rati_endeutament, 2),
    }

    if hasattr(resposta, 'usage_metadata') and resposta.usage_metadata is not None:
        sortida['Tokens_gastats'] = resposta.usage_metadata.total_token_count

    print(json.dumps(sortida, ensure_ascii=False, indent=2))

except Exception as e:
    print(f"Error: {e} - No es genera resposta")