import hashlib, os

class File:
    def __init__(self, path: str, _bytes: bytes, _id: bytes = None, checksum: bytes = None):
        self.path = path
        self.bytes = _bytes
        if _id is not None:
            self.id = _id
        else:
            self.id = os.urandom(8)
        # TODO REMOVE CHECKSUM IN PRODUCTION
        if checksum is not None:
            self.checksum = checksum
        else:
            self.checksum = hashlib.sha256(self.bytes).digest()

    def __str__(self):
        return self.path + f" [{self.id.hex()}]"