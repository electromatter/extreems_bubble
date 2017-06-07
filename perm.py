__all__ = ('Permutation', 'Cycle', 'Identity', 'IDENTITY')

import collections
import random

def gcd(*args):
    if len(args) == 1 and hasattr(args[0], '__iter__'):
        args = iter(args[0])
    g = 0
    for x in args:
        while x > 0:
            x, g = g % x, x
    return g

def lcm(*args):
    if len(args) == 1 and hasattr(args[0], '__iter__'):
        args = iter(args[0])
    m = 1
    for x in args:
        m *= (x // gcd(x, m))
    return m

class FrozenDict(collections.abc.Mapping):
    __slots__ = ('_map', '_hash')

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self._map = dict(*args, **kwargs)
        self._hash = hash(frozenset(self._map))
        return self

    def __getitem__(self, key):
        return self._map[key]

    def __len__(self):
        return len(self._map)

    def __iter__(self):
        return iter(self._map)

    def __hash__(self):
        return self._hash

    def __repr__(self):
        return '%s.FrozenDict(%r)' % (__name__, self._map)

class Permutation(FrozenDict):
    __slots__ = ('_orbits', '_order')

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        unseen = set(self.keys())
        orbits = []
        while unseen:
            first = key = unseen.pop()
            orbit = []
            while True:
                orbit.append(key)
                key = self[key]
                if key == first:
                    break
                try:
                    unseen.remove(key)
                except KeyError:
                    raise ValueError('mapping is not injective') from None
            if len(orbit) > 1:
                orbits.append(Cycle(orbit))
        try:
            orbits.sort()
        except TypeError:
            pass
        if len(orbits) == 0:
            return IDENTITY
        elif len(orbits) == 1:
            return orbits[0]
        self._orbits = tuple(orbits)
        self._order = lcm(orbit.order() for orbit in self._orbits)
        return self

    @classmethod
    def from_product(cls, *args):
        if len(args) == 1 and hasattr(args[0], '__iter__'):
            args = args[0]
        if len(args) == 0:
            return IDENTITY
        elif len(args) == 1:
            return Cycle(args)
        mapping = {}
        for cycle in reversed(args):
            mapping.update({k: mapping.get(v, v) for k, v in Cycle(cycle).items()})
        return cls(mapping)

    def order(self):
        return self._order

    def orbits(self):
        return self._orbits

    def orbit(self, key):
        for orbit in self.orbits():
            if key in orbit:
                return orbit
        return IDENTITY

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            return key

    def __pow__(self, exp):
        mapping = {}
        for orbit in self.orbits():
            mapping.update(orbit ** exp)
        return Permutation(mapping)

    def __mul__(self, other):
        mapping = dict(self)
        mapping.update({k: mapping.get(v, v) for k, v in other.items()})
        return Permutation(mapping)

    def __call__(self, key):
        return self[key]

    def __repr__(self):
        return '%s.Permutation.from_product%r' % (__name__, self.orbits())

class Cycle(Permutation):
    __slots__ = ('_cycle')

    def __new__(cls, *args):
        if len(args) == 1 and hasattr(args[0], '__iter__'):
            args = args[0]
        args = tuple(args)
        if len(args) <= 1:
            return IDENTITY
        try:
            repeat_index = args.index(args[0], 1)
        except ValueError:
            repeat_index = len(args)
        args, repeat = args[:repeat_index], args[repeat_index:]
        mapping = dict(zip(args, args[1:] + args[:1]))
        if len(mapping) < len(args) or set(zip(args, repeat[1:] + repeat[:1])) - mapping.items():
            raise ValueError('cycle inconsistent (not injective)')
        try:
            least_index = args.index(min(args))
            args = args[least_index:] + args[:least_index]
        except TypeError:
            pass
        self = FrozenDict.__new__(cls, mapping)
        self._cycle = args
        return self

    def __iter__(self):
        return iter(self._cycle)

    def order(self):
        return len(self)

    def orbits(self):
        return (self,)

    def orbit(self, key):
        if key in self:
            return self
        return IDENTITY

    def __pow__(self, exp):
        order = self.order()
        exp %= order
        if exp == 0:
            return IDENTITY
        elif exp == 1:
            return self
        elif exp == order - 1:
            return Cycle(reversed(self._cycle))
        elif gcd(exp, order) == 1:
            cycle = []
            index = 0
            for _ in range(order):
                index  = (index + exp) % order
                cycle.append(self._cycle[index])
            return Cycle(cycle)
        unseen = set(range(order))
        cycles = []
        while unseen:
            index = first = unseen.pop()
            cycle = []
            while True:
                cycle.append(self._cycle[index])
                index = (index + exp) % order
                if index == first:
                    break
                unseen.remove(index)
            if len(cycle) > 1:
                cycles.append(cycle)
        return Permutation.from_product(cycles)

    def __repr__(self):
        return '%s.Cycle%r' % (__name__, self._cycle)

class Identity(Cycle):
    __slots__ = ()

    __new__ = FrozenDict.__new__

    def __iter__(self):
        return iter([])

    def order(self):
        return 1

    def orbits(self):
        return ()

    def orbit(self, key):
        return self

    def __pow__(self, exp):
        return self

    def __mul__(self, other):
        return other

    def __repr__(self):
        return '%s.IDENTITY' % __name__

IDENTITY = Identity()

def _make_domain(*args, **kwargs):
    if not args and not kwargs:
        raise TypeError('expected arguments')
    try:
        return list(range(*args, **kwargs))
    except TypeError:
        pass
    return list(*args, **kwargs)

def random_permutation(*args, **kwargs):
    rng = kwargs.pop('random', None)
    x = _make_domain(*args, **kwargs)
    y = list(x)
    random.shuffle(y, rng)
    return Permutation(zip(x, y))

def random_cycle(*args, **kwargs):
    rng = kwargs.pop('random', None)
    x = _make_domain(*args, **kwargs)
    random.shuffle(y, rng)
    return Cycle(x)
