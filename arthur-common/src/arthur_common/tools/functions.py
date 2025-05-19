import hashlib
from uuid import UUID

"""
Convert a uuid to a 12 character, all lowercase string deterministically
"""


def uuid_to_base26(uuid: str | UUID) -> str:
    # Remove hyphens from the UUID
    if isinstance(uuid, UUID):
        uuid_str = str(uuid)
    else:
        uuid_str = uuid

    no_hyphens = uuid_str.replace("-", "")

    # Convert the hex string to an integer
    num = int(no_hyphens, 16)

    # Define the alphabet for base-26
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    base = len(alphabet)

    # Encode the integer into a base-26 string
    base26_str = ""
    while num > 0:
        num, rem = divmod(num, base)
        base26_str = alphabet[rem] + base26_str

    # Ensure the string is 12 characters long (pad with 'a' if necessary)
    base26_str = base26_str.rjust(12, "a")

    # If the resulting string is longer than 12 characters, take the last 12 characters
    return base26_str[-12:]


"""
Hash a string
"""


def hash_nonce(nonce: str) -> str:
    md5_hash = hashlib.md5()
    md5_hash.update(nonce.encode("utf-8"))
    return md5_hash.hexdigest()
