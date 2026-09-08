"""Qual modelo de embedding cabe em CPU? Decide MODELO/DIM/PREFIXO (risco #1 do spec).

Mede duas coisas: velocidade de indexacao e **recuperacao entre idiomas** —
pergunta em portugues achando documento em ingles, e vice-versa. E o caso real de
uma bibliotheca com norma em portugues e datasheet em ingles na mesma pasta.
"""
import time
from sentence_transformers import SentenceTransformer, util

CANDIDATOS = [
    "intfloat/multilingual-e5-small",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "BAAI/bge-m3",
]

# A familia e5 foi treinada com estes prefixos e perde qualidade sem eles. Medir sem
# prefixo subestimaria o e5 e faria o spike escolher o modelo errado.
PREFIXOS = {"intfloat/multilingual-e5-small": ("query: ", "passage: ")}

# Cada assunto existe em UM idioma so. Assim, acertar exige cruzar o idioma —
# nao da para vencer o teste casando palavra com palavra.
CORPUS = [
    "A armadura passiva deve respeitar o cobrimento nominal indicado na tabela 7.2.",
    "Ensaio de tracao em barras de aco destinadas a armaduras para concreto armado.",
    "The anchorage length depends on the design bond strength of the reinforcement.",
    "Configuration of the variable frequency drive for soft start of the motor.",
]
CASOS = [
    ("como calcular o comprimento de ancoragem", 2, "PT -> EN"),
    ("nominal cover of passive reinforcement", 0, "EN -> PT"),
    ("partida suave do motor trifasico", 3, "PT -> EN"),
    ("tensile test on steel reinforcing bars", 1, "EN -> PT"),
]

for nome in CANDIDATOS:
    pre_consulta, pre_doc = PREFIXOS.get(nome, ("", ""))
    t = time.perf_counter()
    m = SentenceTransformer(nome, device="cpu")
    carga = time.perf_counter() - t

    t = time.perf_counter()
    emb = m.encode([pre_doc + c for c in CORPUS] * 40, batch_size=16,
                   show_progress_bar=False)
    vazao = len(CORPUS) * 40 / (time.perf_counter() - t)

    base = m.encode([pre_doc + c for c in CORPUS])
    print(f"{nome}\n  dim {emb.shape[1]}  carga {carga:.1f}s  {vazao:.0f} chunks/s")
    for consulta, esperado, rotulo in CASOS:
        pontos = util.cos_sim(m.encode(pre_consulta + consulta), base)[0]
        ordem = pontos.argsort(descending=True).tolist()
        print(f"    {rotulo}  top1={'OK ' if ordem[0] == esperado else 'ERRO'}"
              f"  posicao={ordem.index(esperado) + 1}")
    print()
