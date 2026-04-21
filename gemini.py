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
        'temperature': 0.1,  # Menys creativitat, més consistència.
        'top_p': 0.8,  # Limita el conjunt de paraules candidates.
        'max_output_tokens': 512,  # Evita respostes massa llargues.
        'response_mime_type': 'application/json',  # Força sortida JSON.
        'http_options': {
            'timeout': 15000,  # Timeout curt per no quedar-se esperant massa.
        },
        'response_schema': {
            # Esquema mínim per validar la resposta.
            'type': 'OBJECT',
            'required': ['Veredicte', 'Semafor', 'Motiu'],
            'properties': {
                'Veredicte': {'type': 'STRING', 'enum': ['APTE', 'NO APTE']},
                'Semafor': {'type': 'STRING', 'enum': ['VERD', 'GROC', 'VERMELL']},
                'Motiu': {'type': 'STRING'},
            },
        },
        # Dona el context i les normes que ha de seguir el model.
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
    asnef = False
    contracte = 'Temporal' # Pot ser 'Indefinit', 'Temporal' o 'Autonom'

    # Calculem el percentatge de deute sobre ingressos.
    total_quotes_mensuals = quotes_actuals + nova_quota
    rati_endeutament = (total_quotes_mensuals / ingressos_nets) * 100

    prompt = f"""
    Analitza la sol·licitud i respon en JSON vàlid.

    Dades:
    - Ingressos nets: {ingressos_nets}€
    - Quotes actuals: {quotes_actuals}€
    - Nova quota: {nova_quota}€
    - Total quotes mensuals de deutes: {total_quotes_mensuals}€
    - ASNEF: {'Si' if asnef else 'No'}
    - Contracte: {contracte}

    - Rati endeutament: {rati_endeutament:.2f}%

    Criteris:
    - VERD: DTI <=30% + no ASNEF + contracte indefinit
    - GROC: DTI 30-40% o contracte temporal
    - VERMELL: DTI >40% o ASNEF Sí
    """

    # ? Apliquem regles bàsiques abans de consultar el model per evitar costos innecessaris en casos clars
    if not asnef and contracte == 'Indefinit' and rati_endeutament <= 30:
        resultat = {
            'Veredicte': 'APTE',
            'Semafor': 'VERD',
            'Motiu': 'Complix criteris bàsics d\'aptesa',
            'Rati_endeutament': round(rati_endeutament, 2),
        }
        print(json.dumps(resultat, ensure_ascii=False, indent=2))
        sys.exit(0)
    elif asnef:     # Si el client està a Asnef --> No apte directe sense consultar el model
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

    # Reintent simple davant error temporal 503 del servei
    resposta = None
    max_retries = 3  # Nombre màxim de reintents abans de fallar.
    for intent in range(1, max_retries + 1):
        try:
            resposta = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=config_analista,
            )
            break
        except Exception as err:
            missatge = str(err)
            if '503' in missatge and intent < max_retries:
                time.sleep(min(intent, 2))
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