"""Fotos em disco. Toda foto é reaberta e salva de novo como JPEG: tira o EXIF (que pode ter o GPS da casa
da pessoa), endireita e reduz o tamanho. Quem pode ver cada foto é decidido na API, nunca por um link público."""
from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

TAMANHO_MAXIMO_BYTES = 8 * 1024 * 1024
LADO_MAXIMO = 1080
FORMATOS = {"JPEG", "PNG", "WEBP", "MPO"}


class FotoRecusada(ValueError):
    pass


class Fotos:
    def __init__(self, pasta: str):
        self._pasta = Path(pasta)
        self._pasta.mkdir(parents=True, exist_ok=True)

    def caminho(self, nome: Optional[str]) -> Optional[Path]:
        if not nome or "/" in nome or "\\" in nome or ".." in nome:
            return None
        caminho = self._pasta / nome
        return caminho if caminho.is_file() else None

    def salvar(self, conteudo: bytes) -> str:
        if len(conteudo) > TAMANHO_MAXIMO_BYTES:
            raise FotoRecusada("A foto pode ter até 8 MB.")
        try:
            imagem = Image.open(io.BytesIO(conteudo))
            if imagem.format not in FORMATOS:
                raise FotoRecusada("Mande a foto em JPG, PNG ou WEBP.")
            imagem = ImageOps.exif_transpose(imagem).convert("RGB")
        except (UnidentifiedImageError, OSError):
            raise FotoRecusada("Não consegui abrir essa imagem.")
        imagem.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
        return self._gravar(imagem)

    def apagar(self, nome: Optional[str]) -> None:
        caminho = self.caminho(nome)
        if caminho:
            caminho.unlink(missing_ok=True)

    def gerar_de_exemplo(self, inicial: str, cor: tuple) -> str:
        """Só para o modo demonstração: um retrato liso com a inicial."""
        imagem = Image.new("RGB", (720, 900), cor)
        desenho = ImageDraw.Draw(imagem)
        for i in range(0, 900, 6):     # degradê simples de cima para baixo
            sombra = tuple(max(0, int(c * (1 - i / 1600))) for c in cor)
            desenho.line([(0, i), (720, i)], fill=sombra, width=6)
        fonte = ImageFont.load_default(size=380)
        desenho.text((360, 450), inicial.upper(), fill=(255, 255, 255), font=fonte, anchor="mm")
        return self._gravar(imagem)

    def _gravar(self, imagem: Image.Image) -> str:
        nome = f"{uuid.uuid4().hex}.jpg"
        imagem.save(self._pasta / nome, "JPEG", quality=82, optimize=True)
        return nome
