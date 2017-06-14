'Permutations as mappings'

import collections as _collections
import random as _random

#pylint: disable=protected-access

class _FrozenDict(object):
    '''FrozenDict() -> empty immutable mapping
    FrozenDict(mapping) -> immutable copy of mapping
    FrozenDict(iterable) -> FrozenDict(dict(iterable))
    FrozenDict(**kwargs) -> FrozenDict(kwargs)

    FrozenDict are immutable dict like objects.
    '''

    __slots__ = ('_map', '_hash')

    def __init__(self, *args, **kwargs):
        pass

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self._map = dict(*args, **kwargs)
        self._hash = hash(frozenset(self._map))
        return self

    def keys(self):
        "D.keys() -> a set-like object providing a view on D's keys"
        return self._map.keys()

    def items(self):
        "D.keys() -> a set-like object providing a view on D's items"
        return self._map.items()

    def values(self):
        "D.keys() -> a set-like object providing a view on D's values"
        return self._map.values()

    def __len__(self):
        return len(self._map)

    def __iter__(self):
        return iter(self._map)

    def __getitem__(self, key):
        return self._map[key]

    def get(self, key, default=None):
        'D.get(k[, d]) -> D[k] if k in D, else d. d defaults to None.'
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key):
        return key in self._map

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        if isinstance(other, _FrozenDict):
            return self._map == other._map
        elif isinstance(other, dict):
            return other == self._map
        return NotImplemented

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self._map)

_collections.abc.Mapping.register(_FrozenDict)

class Permutation(_FrozenDict):
    '''Permutation() -> IDENTITY
    Permutation(mapping) -> extracts the permutation from the mapping
    Permutation(iterable) -> Permutation(dict(iterable))

    This is an immutable permutation generalized from python mappings.
    Permutations support the usual mapping interface.
    '''

    __slots__ = ('_orbits', '_order', '_cycle')

    def __new__(cls, *args, _cycle=None, **kwargs):
        if kwargs:
            raise TypeError('unexpected keyword arguments')

        if _cycle is not None and len(_cycle) > 1:
            # We got a cycle!
            cycle = tuple(_cycle)
            self = super().__new__(cls, zip(cycle, cycle[1:] + cycle[:1]))
            self._cycle = cycle
            self._orbits = (self,)
            self._order = len(cycle)
            return self

        # Decompose the mapping into orbits
        self = super().__new__(cls, ((key, value) \
                                        for key, value in dict(*args).items() \
                                        if key != value))
        unseen = set(self.keys())
        orbits = []
        while unseen:
            first = key = unseen.pop()
            orbit = []

            while True:
                orbit.append(key)#BUG
                key = self[key]
                if key == first:
                    break
                try:
                    unseen.remove(key)
                except KeyError:
                    raise ValueError('mapping is not injective') from None

            if len(orbit) > 1:
                orbits.append(orbit)

        # Ensure orbits are always in the same order to make
        # it nicer to work with.
        try:
            orbits.sort(key=min)
        except TypeError:
            pass

        # It could be that we have a single cycle that was passed as a mapping
        if len(orbits) == 1:
            return cls(_cycle=orbits[0])

        self._orbits = tuple(self.__class__(_cycle=cycle) for cycle in orbits) # pylint: disable=W0212
        self._order = _lcm(len(orbit) for orbit in self.orbits()) # pylint: disable=W0212
        return self

    @classmethod
    def product(cls, *args):
        '''product(iterable) -> computes the product of all terms
        product(*args) -> product(args)

        Accepts any mapping in args and returns the resulting permutation.
        '''

        if len(args) == 1 and hasattr(args[0], '__iter__'):
            args = args[0]

        result = cls()
        for perm in args:
            result *= perm

        return result

    @classmethod
    def cycle(cls, *args):
        '''cycle(iterable) -> create a cyclic permutation that maps each
            element if the iterable to the next.
        cycle(*args) -> cycle(args)

        If the argument is not a cyclic permutation, then ValueError is raised.
        '''
        if len(args) == 1 and hasattr(args[0], '__iter__'):
            args = args[0]

        args = tuple(args)
        if len(args) <= 1:
            return cls()

        # Try to find the end of the cycle or the length
        # of the repeated content
        try:
            repeat_index = args.index(args[0], 1)
        except ValueError:
            repeat_index = len(args)

        # Cut args at the point where it starts to repeat
        args, repeat = args[:repeat_index], args[repeat_index:]
        mapping = dict(zip(args, args[1:] + args[:1]))
        if len(mapping) < len(args):
            raise ValueError('Cycle mapping is inconsistent (not injective)')

        # Verify that repeat is actually just the mapping repeated
        if set(zip(repeat, repeat[1:] + args[:1])) - mapping.items():
            raise ValueError('Cycle args is not cyclic.')

        # Rotate the cycle so that the least element comes first.
        # This ensures that identical cycles have identical representation
        try:
            least_index = args.index(min(args))
            args = args[least_index:] + args[:least_index]
        except TypeError:
            pass

        return cls(_cycle=args)

    @classmethod
    def random_permutation(cls, *args, **kwargs):
        '''random_permutation(n) -> random permutation of n elements
        random_permutation(start, stop[, step]) ->
            random_permutation(range(start, stop, step)
        random_permutation(iterable) -> a random permutation of the iterable

        The optional keyword argument random can be used to specify
        the random number generator used to shuffle.
        '''
        rng = kwargs.pop('random', None)
        domain = _make_domain(*args, **kwargs)
        vals = list(domain)
        _random.shuffle(vals, rng)
        return cls(zip(domain, vals))

    @classmethod
    def random_cycle(cls, *args, **kwargs):
        '''random_cycle(n) -> random cycle of n elements
        random_cycle(start, stop[, step]) ->
            random_cycle(range(start, stop, step))
        random_cycle(iterable) -> a random cycle of the iterable

        The optional keyword argument random can be used to specify
        the random number generator used to shuffle.
        '''
        rng = kwargs.pop('random', None)
        cycle = _make_domain(*args, **kwargs)
        _random.shuffle(cycle, rng)
        return cls.cycle(cycle)

    def as_two_cycles(self):
        'Return an iterator that decompose the permutation into two cycles'
        for orbit in self.orbits():
            if len(orbit) == 2:
                yield orbit
            else:
                first = next(iter(orbit))
                for elem in reversed(orbit):
                    if first == elem:
                        break
                    yield self.cycle(first, elem)

    def order(self):
        'Returns the multiplicative order'
        return self._order

    def orbits(self):
        'Returns an iterator yields the disjoint cycles that compose this permutation'
        return self._orbits

    def orbit(self, key):
        'Returns the orbit of key'
        for orbit in self.orbits():
            if key in orbit:
                return orbit
        return self.__class__()

    def __iter__(self):
        if hasattr(self, '_cycle'):
            return iter(self._cycle)
        return super().__iter__()

    def __reversed__(self):
        if hasattr(self, '_cycle'):
            return reversed(self._cycle)
        return super().__iter__()

    def __getitem__(self, key):
        'Apply this permutation to key'
        try:
            return super().__getitem__(key)
        except KeyError:
            return key

    def __call__(self, key):
        'Apply this permutation to key'
        return self[key]

    def __repr__(self):
        orbits = tuple(self.orbits())
        if not orbits:
            return '{}()'.format(self.__class__.__name__)
        elif len(orbits) == 1:
            return '{}.cycle{!r}'.format(self.__class__.__name__, self._cycle)
        return '{}.product{!r}'.format(self.__class__.__name__, orbits)

    def __pow__(self, exp):
        '''self ** exp -> self * self * self * ...

        The exponent must be an integer.
        '''
        value = self.__class__()
        for orbit in self.orbits():
            order = orbit.order()
            if exp % order == 0:
                pass
            else:
                unseen = set(range(order))
                cycle = list(orbit)
                while unseen:
                    index = first = unseen.pop()
                    new_cycle = []
                    while True:
                        new_cycle.append(cycle[index])
                        index = (index + exp) % order
                        if index == first:
                            break
                        unseen.remove(index)
                    if len(new_cycle) > 1:
                        value *= self.__class__(_cycle=new_cycle)
        return value

    def __mul__(self, other):
        'self * other -> self applied to other'
        mapping = dict(self)
        for key in other:
            mapping[key] = self[other[key]]
        return self.__class__(mapping)

    def __rmul__(self, other):
        'other * self -> other applied to self'
        mapping = dict(other)
        for key, value in self.items():
            mapping[key] = other.get(value)
        return self.__class__(mapping)

def _gcd(*args):
    '''gcd(iterable)
    gcd(*args) -> gcd(args)

    Computes the greatest common divisor of all elements of iterable.
    '''
    if len(args) == 1 and hasattr(args[0], '__iter__'):
        args = iter(args[0])
    gcd = 0
    for val in args:
        while val > 0:
            val, gcd = gcd % val, val
    return gcd

def _lcm(*args):
    '''lcm(iterable)
    lcm(*args) -> lcm(args)

    Computes the least common multiple of all elements of iterable.
    '''
    if len(args) == 1 and hasattr(args[0], '__iter__'):
        args = iter(args[0])
    lcm = 1
    for val in args:
        lcm *= (val // _gcd(val, lcm))
    return lcm

def _make_domain(*args, **kwargs):
    'iterable or range() args -> iterable'
    if not args and not kwargs:
        raise TypeError('expected arguments')
    try:
        return list(range(*args, **kwargs))
    except TypeError:
        pass
    return list(*args, **kwargs)
