# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import os
import errno
import logging
import shlex

import sunbeam.deck

from ecl.eclfile import EclFile
from ecl.grid import EclGrid
from ecl.summary import EclSum

# Default parse option to Sunbeam for a very permissive parsing
SUNBEAM_RECOVERY = [
    ("PARSE_UNKNOWN_KEYWORD", sunbeam.action.ignore),
    ("SUMMARY_UNKNOWN_GROUP", sunbeam.action.ignore),
    ("PARSE_RANDOM_SLASH", sunbeam.action.ignore),
    ("UNSUPPORTED_*", sunbeam.action.ignore),
    ("PARSE_MISSING_SECTIONS", sunbeam.action.ignore),
    ("PARSE_MISSING_DIMS_KEYWORD", sunbeam.action.ignore),
    ("PARSE_RANDOM_TEXT", sunbeam.action.ignore),
    ("PARSE_MISSING_INCLUDE", sunbeam.action.ignore),
    ("PARSE_EXTRA_RECORDS", sunbeam.action.ignore),
    ("PARSE_EXTRA_DATA", sunbeam.action.ignore),
]

# For Python2 compatibility:
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


class EclFiles(object):
    """
    Class for holding an Eclipse deck with result files

    Exists only for convenience, so that loading of
    EclFile/EclSum objects is easy for users, and with
    caching if wanted.

    Various functions that needs some of the Eclipse output
    (or input file) should be able to ask this class, and
    it should be loaded or served from cache.
    """

    def __init__(self, eclbase):
        # eclbase might be a a Posix path object
        eclbase = str(eclbase)

        # Strip .DATA or . at end of eclbase:
        eclbase = rreplace(".DATA", "", eclbase)
        eclbase = rreplace(".", "", eclbase)
        self._eclbase = eclbase

        # Set class variables to None
        self._egridfile = None  # Should be EclFile
        self._initfile = None  # Should be EclFile
        self._eclsum = None  # Should be EclSum

        self._egrid = None  # Should be EclGrid

        self._rstfile = None  # EclFile
        self._rftfile = None  # EclFile

        self._deck = None

    def get_path(self):
        """Return the full path to the directory with the DATA file"""
        return os.path.dirname(os.path.abspath(self._eclbase))

    def get_ecldeck(self):
        """Return a sunbeam deck of the DATA file"""
        if not self._deck:
            if os.path.exists(self._eclbase + ".DATA"):
                deckfile = self._eclbase + ".DATA"
            else:
                deckfile = self._eclbase  # Will be any filename
            logging.info("Parsing deck file %s...", deckfile)
            deck = sunbeam.deck.parse(deckfile, recovery=SUNBEAM_RECOVERY)
            self._deck = deck
        return self._deck

    @staticmethod
    def str2deck(string, recovery=None):
        """Produce a sunbeam deck from a string, using permissive
        parsing by default"""
        if not recovery:
            recovery = SUNBEAM_RECOVERY
        return sunbeam.deck.parse_string(string, recovery=recovery)

    @staticmethod
    def file2deck(filename):
        """Try to convert standalone files into Sunbeam Deck objects"""
        with open(filename) as fhandle:
            filestring = "".join(fhandle.readlines())
            return EclFiles.str2deck(filestring)

    def get_egrid(self):
        """Find and return EGRID file as an EclGrid object"""
        if not self._egrid:
            egridfilename = self._eclbase + ".EGRID"
            if not os.path.exists(egridfilename):
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), egridfilename
                )
            logging.info("Opening grid data from EGRID file: %s", egridfilename)
            self._egrid = EclGrid(egridfilename)
        return self._egrid

    def get_egridfile(self):
        """Find and return the EGRID file as a EclFile object

        This gives access to data vectors defined on the grid."""
        if not self._egridfile:
            egridfilename = self._eclbase + ".EGRID"
            if not os.path.exists(egridfilename):
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), egridfilename
                )
            logging.info("Opening data vectors from EGRID file: %s", egridfilename)
            self._egridfile = EclFile(egridfilename)
        return self._egridfile

    def get_eclsum(self, include_restart=True):
        """Find and return the summary file and
        return as EclSum object

        Args:
            include_restart: boolean sent to libecl for whether restart files
                should be traversed.
        Returns:
            ecl.summary.EclSum
        """
        if not self._eclsum:
            smryfilename = self._eclbase + ".UNSMRY"
            if not os.path.exists(smryfilename):
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), smryfilename
                )
            logging.info("Opening UNSMRY file: %s", smryfilename)
            self._eclsum = EclSum(smryfilename, include_restart=include_restart)
        return self._eclsum

    def get_initfile(self):
        """Find and return the INIT file as an EclFile object"""
        if not self._initfile:
            initfilename = self._eclbase + ".INIT"
            if not os.path.exists(initfilename):
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), initfilename
                )
            logging.info("Opening INIT file: %s", initfilename)
            self._initfile = EclFile(initfilename)
        return self._initfile

    def get_rftfile(self):
        """Find and return the RFT file as an EclFile object"""
        if not self._rftfile:
            rftfilename = self._eclbase + ".RFT"
            if not os.path.exists(rftfilename):
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), rftfilename
                )
            logging.info("Opening RFT file: %s", rftfilename)
            self._rftfile = EclFile(rftfilename)
        return self._rftfile

    def get_rstfile(self):
        """Find and return the UNRST file as an EclFile object"""
        if not self._rstfile:
            rstfilename = self._eclbase + ".UNRST"
            if not os.path.exists(rstfilename):
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), rstfilename
                )
            logging.info("Opening RST file: %s", rstfilename)
            self._rstfile = EclFile(rstfilename)
        return self._rstfile

    def get_rstfilename(self):
        """Return the inferred name of the UNRST file"""
        return self._eclbase + ".UNRST"

    def get_zonemap(self, filename=None):
        """Return a dictionary from (int) K layers in the simgrid to strings

        Typical usage is to map from grid layer to zone names.

        The layer filename must currently follow format

          'ZoneA' 1-4
          'ZoneB' 5-10

        where the single quotes are optional for zones without spaces.
        Write single layer zones as 11-11. NB: ResInsight requires single
        quotes always.

        Args:
            filename (str): Name of file. If relative path, relative to DATA
                file location. If nonexisting file, an empty dict will be
                returned and a warning issued.

        Returns:
            dict, integer keys which are the K layers. Every layer mentioned
                in the interval in the input file is present. Can be empty.
        """
        if not filename:
            filename_defaulted = True
            filename = "zones.lyr"
        else:
            filename_defaulted = False
        assert isinstance(filename, str)
        if not os.path.isabs(filename):
            fullpath = os.path.join(self.get_path(), filename)
        else:
            fullpath = filename
        if not os.path.exists(fullpath):
            if filename_defaulted:
                # No warnings when the default filename is not there.
                return {}
            logging.warning("Zonefile %s not found, ignoring", fullpath)
            return {}

        zonelines = open(fullpath).readlines()
        zonelines = [line.strip() for line in zonelines]
        zonelines = [line for line in zonelines if not line.startswith("--")]
        zonelines = [line for line in zonelines if not line.startswith("#")]
        zonelines = filter(len, zonelines)

        zonemap = {}
        for line in zonelines:
            (layername, interval) = shlex.split(line)
            (k_0, k_1) = interval.strip().split("-")
            for k in range(int(k_0), int(k_1) + 1):
                zonemap[k] = layername
        return zonemap


def rreplace(pat, sub, string):
    """Variant of str.replace() that only replaces at the end of the string"""
    return string[0 : -len(pat)] + sub if string.endswith(pat) else string
