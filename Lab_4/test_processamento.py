"""Testes locais determinísticos; execute python3 -m unittest -v."""

import unittest
import numpy as np
from processamento_imagens import analisar, classificar, gerar_imagem, intervalos


class TestProcessamento(unittest.TestCase):
    def setUp(self):
        self.p = dict(linhas=4, colunas=5, limiar_suspeito=200, limiar_alto=230,
                      pct_critico=5.0, pct_altos=1.0, seed=42, foco='direito')

    def test_limites_e_lateralidade_colunas_impares(self):
        bloco = np.array([[200, 201, 230, 231, 255], [0, 1, 2, 3, 4]], dtype=np.uint8)
        self.assertEqual(analisar(bloco, self.p), dict(pixels=10, soma=1127, maximo=255,
                                                     suspeitos=4, altos=2, esquerdo=1, direito=3))

    def test_resto_e_faixas_vazias(self):
        self.assertEqual(intervalos(2003, 4), [(0, 501), (501, 1002), (1002, 1503), (1503, 2003)])
        self.assertEqual(intervalos(2, 4), [(0, 1), (1, 2), (2, 2), (2, 2)])
        vazio = analisar(np.empty((0, 5), dtype=np.uint8), self.p)
        self.assertTrue(all(v == 0 for v in vazio.values()))
        self.assertEqual(classificar(0, 0, 0, self.p), 'SEM DADOS')

    def test_classificacao_fronteiras(self):
        for suspeitos, altos, esperado in [(0, 0, 'NORMAL'), (9, 0, 'NORMAL'),
                                           (10, 0, 'ATENÇÃO'), (49, 0, 'ATENÇÃO'),
                                           (50, 0, 'CRÍTICA'), (10, 10, 'CRÍTICA')]:
            self.assertEqual(classificar(1000, suspeitos, altos, self.p), esperado)

    def test_conservacao_metricas_e_reprodutibilidade(self):
        self.p.update(linhas=203, colunas=101)
        imagem = gerar_imagem(self.p)
        np.testing.assert_array_equal(imagem, gerar_imagem(self.p))
        esperado = analisar(imagem, self.p)
        self.assertEqual(esperado['esquerdo'], 0)
        self.assertGreater(esperado['direito'], 0)
        for size in (1, 2, 4, 8, 210):
            locais = [analisar(imagem[a:b], self.p) for a, b in intervalos(203, size)]
            for chave, valor in esperado.items():
                agregar = max if chave == 'maximo' else sum
                self.assertEqual(agregar(r[chave] for r in locais), valor)
        self.p['foco'] = 'nenhum'
        self.assertEqual(analisar(gerar_imagem(self.p), self.p)['suspeitos'], 0)
        self.p['foco'] = 'esquerdo'
        invertido = analisar(gerar_imagem(self.p), self.p)
        self.assertGreater(invertido['esquerdo'], 0)
        self.assertEqual(invertido['direito'], 0)


if __name__ == '__main__':
    unittest.main()
