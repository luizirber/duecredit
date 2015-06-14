import os
import sys
from functools import wraps

from .entries import DueCreditEntry
from .stub import InactiveDueCreditCollector
from .io import TextOutput, PickleOutput

import logging
lgr = logging.getLogger('duecredit.collector')

class DueCreditCollector(object):
    """Collect the references

    The mighty beast which will might become later a proxy on the way to
    talk to a real collector
    """
    def __init__(self, entries=None, citations=None):
        self._entries = entries or {}
        self.citations = citations or {}

    def add(self, entry):
        """entry should be a DueCreditEntry object"""
        if isinstance(entry, list):
            for e in entry:
                self.add(e)
        else:
            key = entry.get_key()
            self._entries[key] = entry

    def load(self, src):
        """Loads references from a file or other recognizable source

        ATM supported only
        - .bib files
        """
        # raise NotImplementedError
        if isinstance(src, str):
            if src.endswith('.bib'):
                self._load_bib(src)
            else:
                raise NotImplementedError('Format not yet supported')
        else:
            raise ValueError('Must be a string')

    def _load_bib(self, src):
        lgr.debug("Loading %s" % src)

    # # TODO: figure out what would be the optimal use for the __call__
    # def __call__(self, *args, **kwargs):
    #     # TODO: how to determine and cite originating module???
    #     #       - we could use inspect but many people complain
    #     #         that it might not work with other Python
    #     #         implementations
    #     pass # raise NotImplementedError

    def cite(self, entry, use=None, level=None):
        """Decorator for references

        Parameters
        ----------
        entry: str or DueCreditEntry
          The entry to use, either identified by its id or a new one (to be added)
        """
        if isinstance(entry, DueCreditEntry):
            # new one -- add it
            self.add(entry)
            entry_ = entry
        else:
            entry_ = self._entries[entry]
        entry_key = entry_.get_key()

        if entry_key not in self.citations:
            self.citations[entry_key] = Citation(entry_, use, level)
        citation = self.citations[entry_key]
        citation.count += 1
        # TODO: update level and use here?

        return citation

    def dcite(self, *args, **kwargs):
        """Decorator for references.  Wrap a function or

        Parameters
        ----------
        args, kwargs
          Arguments to be passed to cite.  If no "level" provided, we deduce it
          from the wrapped function/method

        Examples
        --------

        @due.dcite('XXX00', use="Provides an answer for meaningless existence")
        def purpose_of_life():
            return None

        """
        def func_wrapper(func):
            if 'level' not in kwargs:
                # deduce level from the actual function which was decorated
                kwargs['level'] = 'func %s.%s' % (func.__module__, func.__name__)

            @wraps(func)
            def cite_wrapper(*fargs, **fkwargs):
                citation = self.cite(*args, **kwargs)
                return func(*fargs, **fkwargs)
            return cite_wrapper
        return func_wrapper

    def __repr__(self):
        args = []
        if self.citations:
            args.append("citations={0}".format(repr(self.citations)))
        if self._entries:
            args.append("entries={0}".format(repr(self._entries)))

        if args:
            args = ", ".join(args)
        else:
            args = ""
        return self.__class__.__name__ + '({0})'.format(args)

    def __str__(self):
        return self.__class__.__name__ + \
            ' {0:d} entries, {1:d} citations'.format(
                len(self._entries), len(self.citations))


class CollectorGrave(object):
    """A helper which would take care about exporting citations upon its Death
    """
    def __init__(self, collector, fn=None):
        self._due = collector
        self.fn = fn or '.duecredit.p'
        # for now decide on output "format" right here
        self._outputs = [self._get_output_handler(
            type_.lower().strip(), collector, fn=fn)
            for type_ in os.environ.get('DUECREDIT_OUTPUTS',
                                        'stdout').split(',')
            if type_]

    @staticmethod
    def _get_output_handler(type_, collector, fn=None):
        # just a little factory
        if type_ in ("stdout", "stderr"):
            return TextOutput(getattr(sys, type_), collector)
        elif type_ == "pickle":
            return PickleOutput(collector, fn=fn)
        else:
            raise NotImplementedError()

    def __del__(self):
        for output in self._outputs:
            output.dump()

# TODO:  provide HTML, MD, RST etc formattings

class Citation(object):
    """Encapsulates citations and information on their use"""

    def __init__(self, entry, use, level):
        self._entry = entry
        self._use = use
        self._level = level
        self.count = 0

    def __repr__(self):
        args = [repr(self._entry)]
        if self._use:
            args.append("use={0}".format(repr(self._use)))
        if self._level:
            args.append("level={0}".format(repr(self._level)))

        if args:
            args = ", ".join(args)
        else:
            args = ""
        return self.__class__.__name__ + '({0})'.format(args)

    @property
    def level(self):
        return self._level

    @property
    def entry(self):
        return self._entry
