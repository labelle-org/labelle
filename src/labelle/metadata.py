from importlib.metadata import metadata as md

dist_name = __name__.split(".", maxsplit=1)[0]
our_metadata = md(dist_name)
__version__ = our_metadata["Version"]
