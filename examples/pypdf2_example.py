from cpytraceafl.rewriter import install_rewriter

install_rewriter()

from PyPDF2 import PdfFileReader
from PyPDF2.utils import PyPdfError
import codecs
from io import BytesIO

try:
    # this is the smallest example of a pdf I could find from the examples at
    # https://stackoverflow.com/questions/17279712/what-is-the-smallest-possible-valid-pdf.
    # it does _not_ successfully parse with pypdf2, but it might be enough to exercise the
    # code enough to get internal imports or caches initialized before the fork. IRL you
    # might like to use a real pdf for this.
    r = PdfFileReader(BytesIO(codecs.decode(
        b"255044462D312E0D747261696C65723C"
        b"3C2F526F6F743C3C2F50616765733C3C"
        b"2F4B6964735B3C3C2F4D65646961426F"
        b"785B302030203320335D3E3E5D3E3E3E"
        b"3E3E3E",
        "hex",
    )))
except PyPdfError:
    pass

import sys
from cpytraceafl import fuzz_from_here, crashing_excepthook

fuzz_from_here(excepthook=crashing_excepthook)

with open(sys.argv[1], "rb") as f:
    try:
        r = PdfFileReader(f)
        r.getFields()
        r.getXmpMetadata()
    except PyPdfError:
        pass
