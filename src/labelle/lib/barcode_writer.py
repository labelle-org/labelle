# === LICENSE STATEMENT ===
# Copyright (c) 2011 Sebastian J. Bronner <waschtl@sbronner.com>
#
# Copying and distribution of this file, with or without modification, are
# permitted in any medium without royalty provided the copyright notice and
# this notice are preserved.
# === END LICENSE STATEMENT ===

from typing import List, NamedTuple, NewType

from barcode.writer import BaseWriter

BinaryString = NewType("BinaryString", str)
"""A string that's been validated to contain only '0's and '1's."""


def _validate_string_as_binary(s: str) -> BinaryString:
    if not all(c in ("0", "1") for c in s):
        raise ValueError("Barcode can only contain 0 and 1")
    return BinaryString(s)


class BarcodeResult(NamedTuple):
    line: BinaryString
    quiet_zone: float


class SimpleBarcodeWriter(BaseWriter):
    def render(self, code: List[str]) -> BarcodeResult:
        """Extract the barcode string from the code and render it into an image."""
        if len(code) != 1:
            raise ValueError("Barcode expected to have only one line")
        line = _validate_string_as_binary(code[0])
        return BarcodeResult(line=line, quiet_zone=self.quiet_zone)
