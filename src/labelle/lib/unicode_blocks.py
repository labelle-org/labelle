from PIL.Image import Image
from PIL.ImageOps import pad

UH = "▀"
LH = "▄"
FB = "█"
NB = "\xa0"

assert UH == "\N{UPPER HALF BLOCK}"
assert LH == "\N{LOWER HALF BLOCK}"
assert FB == "\N{FULL BLOCK}"
assert NB == "\N{NO-BREAK SPACE}"

BLACK_PIXEL = (255, 255, 255, 255)
WHITE_PIXEL = (0, 0, 0, 255)
# when the image height is odd, the preview image height is extended by 1 pixel
# this padding result in the added line being composed of transparent pixels.
TRANSPARENT_PIXEL = (0, 0, 0, 0)

dict_unicode = {
    (BLACK_PIXEL, BLACK_PIXEL): FB,
    (WHITE_PIXEL, BLACK_PIXEL): LH,
    (BLACK_PIXEL, WHITE_PIXEL): UH,
    (WHITE_PIXEL, WHITE_PIXEL): NB,
    (BLACK_PIXEL, TRANSPARENT_PIXEL): UH,
    (WHITE_PIXEL, TRANSPARENT_PIXEL): NB,
}

dict_unicode_inverted = {
    (BLACK_PIXEL, BLACK_PIXEL): NB,
    (WHITE_PIXEL, BLACK_PIXEL): UH,
    (BLACK_PIXEL, WHITE_PIXEL): LH,
    (WHITE_PIXEL, WHITE_PIXEL): FB,
    (BLACK_PIXEL, TRANSPARENT_PIXEL): NB,
    (WHITE_PIXEL, TRANSPARENT_PIXEL): UH,
}


def image_to_unicode(im: Image, invert: bool = False) -> str:
    char_for = dict_unicode_inverted if invert else dict_unicode
    width = im.width
    height = im.height + (im.height % 2)
    padded_im = pad(image=im, size=(width, height))
    a = padded_im.load()
    output_rows = []
    for r in range(0, height, 2):
        char_list = [char_for[(a[c, r], a[c, r + 1])] for c in range(width)]
        row = "".join(char_list)
        output_rows.append(row)
    output_str = "\n".join(output_rows)
    return output_str
