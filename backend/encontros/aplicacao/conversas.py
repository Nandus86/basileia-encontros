"""Casos de uso depois do Descobrir: curtir/passar, o match, a conversa e a foto liberada."""
from __future__ import annotations

from typing import List, Optional

from encontros.aplicacao.curadoria import Curadoria
from encontros.aplicacao.portas import Match, Mensagem, Repositorio
from encontros.dominio.afinidade import podem_se_ver
from encontros.dominio.perfil import Perfil

TAMANHO_DA_MENSAGEM = 1000


class NaoEncontrado(LookupError):
    pass


class Recusado(ValueError):
    pass


class Conversas:
    def __init__(self, repositorio: Repositorio, curadoria: Curadoria):
        self._repo = repositorio
        self._curadoria = curadoria

    async def reagir(self, pessoa: Perfil, outra_id: int, curtiu: bool) -> Optional[Match]:
        """Curtir só vale para quem o Descobrir mostraria (afinidade guardada e compatível).
        Se a outra pessoa já tinha curtido, nasce o match."""
        outra = await self._repo.perfil(outra_id)
        if not outra or outra.id == pessoa.id:
            raise NaoEncontrado()
        if curtiu:
            afinidade = await self._curadoria.afinidade(pessoa, outra)
            if not (afinidade and afinidade.compativel and podem_se_ver(pessoa, outra)):
                raise Recusado("Essa pessoa não está mais disponível.")
        return await self._repo.reagir(pessoa.id, outra.id, curtiu)

    async def match_de(self, pessoa_id: int, match_id: int, ativo: bool = True) -> Match:
        match = await self._repo.match(match_id)
        if not match or not match.tem(pessoa_id) or (ativo and match.desfeito):
            raise NaoEncontrado()
        return match

    async def mensagens(self, pessoa_id: int, match_id: int, depois_de: int = 0) -> List[Mensagem]:
        await self.match_de(pessoa_id, match_id, ativo=False)
        return await self._repo.mensagens(match_id, depois_de)

    async def enviar(self, pessoa_id: int, match_id: int, texto: str) -> Mensagem:
        await self.match_de(pessoa_id, match_id)
        texto = (texto or "").strip()
        if not texto:
            raise Recusado("Escreva uma mensagem.")
        if len(texto) > TAMANHO_DA_MENSAGEM:
            raise Recusado(f"A mensagem pode ter até {TAMANHO_DA_MENSAGEM} letras.")
        return await self._repo.enviar(match_id, pessoa_id, texto)

    async def liberar_foto(self, pessoa_id: int, match_id: int) -> None:
        """Cada um libera a própria foto, para aquela conversa só. Não tem como "desliberar"."""
        await self.match_de(pessoa_id, match_id)
        await self._repo.liberar_foto(match_id, pessoa_id)

    async def pode_ver_foto(self, espectador_id: int, dono_id: int) -> bool:
        if espectador_id == dono_id:
            return True
        match = await self._repo.match_entre(espectador_id, dono_id)
        return bool(match and not match.desfeito and match.foto_liberada.get(dono_id))
