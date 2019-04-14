# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

from typing import Iterator, Tuple
from solitude._internal.oi_serializable import ISerializable


class ColorText(ISerializable):
    def __init__(self, chunks=None):
        self._chunks = []
        if chunks:
            self._chunks.extend(chunks)

    def append(self, text, color="") -> None:
        self._chunks.append([text, color])

    def iter_chunks(self) -> Iterator[Tuple[str, str]]:
        for chunk in self._chunks:
            yield chunk

    def __str__(self):
        return "".join(text for text, _ in self._chunks)

    def to_obj(self) -> dict:
        return {
            "chunks": [c for c in self._chunks]
        }

    @staticmethod
    def from_obj(obj) -> "ColorText":
        return ColorText(obj["chunks"])
