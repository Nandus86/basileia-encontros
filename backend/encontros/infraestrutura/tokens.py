"""Token de acesso do app (JWT com segredo próprio). Vai no cabeçalho Authorization de toda chamada."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt


class TokensJwt:
    ALGORITMO = "HS256"

    def __init__(self, segredo: str, dias_de_acesso: int = 30):
        if len(segredo) < 16:
            raise ValueError("ENCONTROS_JWT_SECRET precisa ter pelo menos 16 caracteres")
        self._segredo = segredo
        self._validade = timedelta(days=dias_de_acesso)

    def de_acesso(self, pessoa_id: int) -> str:
        agora = datetime.now(timezone.utc)
        return jwt.encode({"sub": str(pessoa_id), "tipo": "acesso", "iat": agora, "exp": agora + self._validade},
                          self._segredo, algorithm=self.ALGORITMO)

    def pessoa_do_acesso(self, token: str) -> Optional[int]:
        try:
            dados = jwt.decode(token, self._segredo, algorithms=[self.ALGORITMO])
        except JWTError:
            return None
        if dados.get("tipo") != "acesso":
            return None
        try:
            return int(dados.get("sub"))
        except (TypeError, ValueError):
            return None
