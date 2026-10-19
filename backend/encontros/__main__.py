"""python -m encontros — sobe a API."""
import logging

import uvicorn

from encontros.config import configuracao
from encontros.entrada.api import criar_app

if __name__ == "__main__":
    config = configuracao()
    logging.basicConfig(level=config.nivel_log, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    uvicorn.run(criar_app(config=config), host="0.0.0.0", port=config.porta, proxy_headers=True,
                forwarded_allow_ips="*")
