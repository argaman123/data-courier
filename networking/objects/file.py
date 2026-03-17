import os


class File:
    def __init__(self, path: str, _bytes: bytes, _id: bytes = None):
        self.path = path
        self.bytes = _bytes
        if _id is not None:
            self.id = _id
        else:
            self.id = os.urandom(8)

    def save(self, folder: str):
        with open(os.path.join(folder, self.path), 'wb') as f:
            f.write(self.bytes)

    def __str__(self):
        return self.path + f" [{self.id.hex()}]"