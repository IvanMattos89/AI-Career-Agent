import hashlib
import json
from pathlib import Path


CACHE = Path("cache")

CACHE.mkdir(exist_ok=True)


def _file(texto):

    return CACHE / (hashlib.md5(texto.encode()).hexdigest()+".json")


def get(texto):

    arq = _file(texto)

    if arq.exists():

        return json.loads(arq.read_text(encoding="utf8"))

    return None


def save(texto, dados):

    _file(texto).write_text(

        json.dumps(

            dados,

            ensure_ascii=False,

            indent=2

        ),

        encoding="utf8"

    )
