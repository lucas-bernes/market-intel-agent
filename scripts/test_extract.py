from market_intel.extract import extract_model_comparison

texto = '''
Kling 3.0 e um modelo de geracao de video a partir de imagem, oferecido pela fal.ai.
O preco e de 0.35 dolares por segundo de video gerado.
Aceita no maximo 4 imagens de referencia por geracao.
A janela de prompt suporta ate 2000 tokens.
Suporta geracao multi-shot (varios planos numa mesma geracao).
'''

resultado = extract_model_comparison(texto)
print(resultado)