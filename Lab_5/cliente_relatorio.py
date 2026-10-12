import argparse
import requests

def consumir_api(url):
    resposta = requests.get(url, timeout=5)
    resposta.raise_for_status()
    return resposta.json()

def consultar_status(urls):
    for url in urls:
        try:
            dados = consumir_api(url)
            print(f"{dados['service']}: {dados['status']} | {dados['timestamp']}")
        except (requests.RequestException, ValueError, KeyError) as erro:
            print(f'Erro em {url}: {erro}')

def gerar_relatorio(id):
    fiscais = consumir_api(f'http://localhost:5000/detalhes/{id}')
    estoque = consumir_api(f'http://localhost:3000/estoque/{id}')
    dados = {**fiscais, **estoque}
    print(f"ID: {id} | Nome: {dados['nome']} | Preço: R$ {dados['preco']} | Estoque: {dados['estoque']}")
    return dados

def main():
    parser = argparse.ArgumentParser(description='Cliente integrador dos serviços fiscais e de estoque')
    parser.add_argument('--id', help='ID; se omitido, solicita no terminal')
    parser.add_argument('--status', action='store_true')
    args = parser.parse_args()
    if args.status:
        consultar_status(['http://localhost:5000/status', 'http://localhost:3000/status'])
        return 0
    id = args.id if args.id is not None else input('Informe o id: ').strip()
    try:
        gerar_relatorio(id)
    except requests.HTTPError as erro:
        print(f'Erro HTTP {erro.response.status_code}: {erro.response.text.strip()}')
        return 1
    except (requests.RequestException, ValueError, KeyError) as erro:
        print(f'Erro ao consultar os serviços: {erro}')
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
