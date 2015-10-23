from audiotools import (AudioFile, InvalidFile)

class InvalidMPC(InvalidFile):
    """raised by invalid files during MPC initialization"""

    pass

class MPCAudio(AudioFile):
    """an MPC audio file"""

    SUFFIX = "mpc"
    NAME = SUFFIX
    DESCRIPTION = u"MusePack"
    DEFAULT_COMPRESSION = "5"

    # Ranges from 0 to 10. Lower levels mean lower kbps, and therefore
    # lower quality.
    COMPRESSION_MODE = tuple(map(str, range(0, 11)))
    COMPRESSION_DESCRIPTIONS = {"0": u"poor quality (~20 kbps)",
                                "1": u"poor quality (~30 kbps)",
                                "2": u"low quality (~60 kbps)",
                                "3": u"low/medium quality (~90 kbps)",
                                "4": u"medium quality (~130 kbps)",
                                "5": u"high quality (~180 kbps)",
                                "6": u"excellent quality (~210 kbps)",
                                "7": u"excellent quality (~240 kbps)",
                                "8": u"excellent quality (~270 kbps)",
                                "9": u"excellent quality (~300 kbps)",
                                "10": u"excellent quality (~350 kbps)"} 

