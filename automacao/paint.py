"""Paint: abre o programa.

"jarvis, abra o paint."  /  "jarvis, quero desenhar."

Testar sozinho (da pasta do projeto):  python -m automacao.paint abra o paint
"""
from .comum import Plano, iniciar_programa, rodar_isolado, seguro

RESPOSTA = "Certo, irei abrir o Paint."


def _eh_paint(titulo):
    """Título como 'Sem título - Paint' (ou 'Paint 3D', se a busca abrir esse)."""
    return titulo.endswith(("paint", "paint 3d"))


@seguro("abrir o Paint")
def abrir_paint():
    return iniciar_programa("paint", _eh_paint, "Paint", timeout=15)


def planejar(frase=""):
    return Plano(RESPOSTA, abrir_paint)


if __name__ == "__main__":
    rodar_isolado(planejar)
