"""Lê as senhas das contas criadas na versão anterior do site (Flask).

A versão anterior guardava as senhas no formato do Werkzeug:
    scrypt:32768:8:1$<salt>$<hash em hexadecimal>
Esse texto tem 162 caracteres e não cabe no campo de senha do Django (128).
Por isso o importador guarda a mesma informação de forma mais curta:
    wzscrypt$32768:8:1$<salt>$<hash em base64>
Este hasher só serve para CONFERIR essas senhas. Depois do primeiro login,
o Django troca a senha automaticamente para o formato padrão dele.
"""
import base64
import hashlib

from django.contrib.auth.hashers import BasePasswordHasher
from django.utils.crypto import constant_time_compare


def converter_senha_werkzeug(senha_hash):
    """scrypt:N:r:p$salt$hex  ->  wzscrypt$N:r:p$salt$base64"""
    metodo, salt, hash_hex = senha_hash.split("$", 2)
    parametros = metodo.split(":", 1)[1]
    hash_base64 = base64.b64encode(bytes.fromhex(hash_hex)).decode("ascii")
    return "wzscrypt$" + parametros + "$" + salt + "$" + hash_base64


class WerkzeugScryptHasher(BasePasswordHasher):
    algorithm = "wzscrypt"

    def verify(self, password, encoded):
        try:
            algoritmo, parametros, salt, hash_base64 = encoded.split("$", 3)
            partes = parametros.split(":")
            n = int(partes[0])
            r = int(partes[1])
            p = int(partes[2])
            hash_salvo = base64.b64decode(hash_base64)
        except (ValueError, IndexError):
            return False
        calculado = hashlib.scrypt(password.encode("utf-8"), salt=salt.encode("utf-8"),
                                   n=n, r=r, p=p, maxmem=132 * n * r * p)
        return constant_time_compare(calculado, hash_salvo)

    def encode(self, password, salt):
        raise NotImplementedError("Senhas novas usam o formato padrão do Django.")

    def decode(self, encoded):
        algoritmo, parametros, salt, hash_base64 = encoded.split("$", 3)
        return {"algorithm": self.algorithm, "salt": salt, "hash": hash_base64}

    def safe_summary(self, encoded):
        return {"algoritmo": self.algorithm}

    def must_update(self, encoded):
        return True
