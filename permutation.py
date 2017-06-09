'Permutations as mappings'

__all__ = ('Permutation', 'Cycle', 'IDENTITY')

import collections as _collections
import random as _random

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

class _FrozenDict(_collections.abc.Mapping):
    '''FrozenDict() -> empty immutable mapping
    FrozenDict(mapping) -> immutable copy of mapping
    FrozenDict(iterable) -> FrozenDict(dict(iterable))
    FrozenDict(**kwargs) -> FrozenDict(kwargs)

    FrozenDict are immutable dict like objects.
    '''

    __slots__ = ('__map', '__hash')

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self.__map = dict(*args, **kwargs)
        self.__hash = hash(frozenset(self.__map))
        return self

    def __getitem__(self, key):
        return self.__map[key]

    def __len__(self):
        return len(self.__map)

    def __iter__(self):
        return iter(self.__map)

    def __hash__(self):
        return self.__hash

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self.__map)

class Permutation(_FrozenDict):
    '''Permutation() -> IDENTITY
    Permutation(mapping) -> extracts the permutation from the mapping
    Permutation(iterable) -> Permutation(dict(iterable))

    This is an immutable permutation generalized from python mappings.
    Permutations support the usual mapping interface.
    '''

    __slots__ = ('__orbits', '__order')

    def __new__(cls, *args):
        # Extract the mapping from the arguments
        self = super().__new__(cls, *args)

        # Decompose the mapping into orbits
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

        # Ensure orbits are always in the same order to make
        # it nicer to work with.
        try:
            orbits.sort()
        except TypeError:
            pass

        if not orbits:
            # Got the identity map, return the singleton
            return IDENTITY
        elif len(orbits) == 1:
            # Got a single cycle
            return orbits[0]

        # Otherwise, this permutation is a product of disjoint cycles
        self.__orbits = tuple(orbits)
        self.__order = _lcm(orbit.order() for orbit in self.__orbits)
        return self

    @classmethod
    def from_product(cls, *args):
        '''from_product(iterable) -> computes the product of all terms
        from_product(*args) -> from_product(args)

        Accepts any mapping in args and returns the resulting permutation.
        '''

        if len(args) == 1 and hasattr(args[0], '__iter__'):
            args = args[0]

        mapping = IDENTITY
        for perm in args:
            mapping *= perm

        return cls(mapping)

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
                    yield Cycle(first, elem)

    def order(self):
        'Returns the multiplicative order'
        return self.__order

    def orbits(self):
        'Returns an iterator yields the disjoint cycles that compose this permutation'
        return self.__orbits

    def orbit(self, key):
        'Returns the orbit of key'
        for orbit in self.orbits():
            if key in orbit:
                return orbit
        return IDENTITY

    def __getitem__(self, key):
        'Apply this permutation to key'
        try:
            return super().__getitem__(key)
        except KeyError:
            return key

    def __pow__(self, exp):
        '''self ** exp -> self * self * self * ...

        The exponent must be an integer.
        '''
        mapping = {}
        for orbit in self.orbits():
            # mappings are disjoint, so their products are as well.
            mapping.update(orbit ** exp)
        return Permutation(mapping)

    def __mul__(self, other):
        'self * other -> self applied to other'
        mapping = dict(self)
        for key in other:
            mapping[key] = self[other[key]]
        return Permutation(mapping)

    def __rmul__(self, other):
        'other * self -> other applied to self'
        mapping = dict(other)
        for key, value in self.items():
            mapping[key] = other.get(value)
        return Permutation(mapping)

    def __call__(self, key):
        'Apply this permutation to key'
        return self[key]

    def __repr__(self):
        return '{}.from_product{!r}'.format(self.__class__.__name__, self.orbits())

class Cycle(Permutation):
    '''Cycle(iterable) -> create a cyclic permutation that maps each
        element if the iterable to the next.
    Cycle(*args) -> Cycle(args)

    If the argument is not a cyclic permutation, then ValueError is raised.
    '''

    __slots__ = ('__cycle', )

    def __new__(cls, *args):
        if len(args) == 1 and hasattr(args[0], '__iter__'):
            args = args[0]

        args = tuple(args)
        if len(args) <= 1:
            # 1-Cycles are identity mappings
            return IDENTITY

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

        self = _FrozenDict.__new__(cls, mapping)
        self.__cycle = args
        return self

    def __iter__(self):
        return iter(self.__cycle)

    def __reversed__(self):
        return reversed(self.__cycle)

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

        # Special cases
        exp %= order
        if exp == 0:
            return IDENTITY
        elif exp == 1:
            return self
        elif exp == order - 1:
            return Cycle(reversed(self.__cycle))
        elif _gcd(exp, order) == 1:
            cycle = []
            index = 0
            for _ in range(order):
                index = (index + exp) % order
                cycle.append(self.__cycle[index])
            return Cycle(cycle)

        unseen = set(range(order))
        cycles = []
        while unseen:
            index = first = unseen.pop()
            cycle = []
            while True:
                cycle.append(self.__cycle[index])
                index = (index + exp) % order
                if index == first:
                    break
                unseen.remove(index)
            if len(cycle) > 1:
                cycles.append(Cycle(cycle))

        return Permutation.from_product(cycles)

    def __repr__(self):
        return '{}{!r}'.format(self.__class__.__name__, self.__cycle)

class Identity(Cycle):
    'The identity permutation that maps all elements to themselves'

    __slots__ = ()

    __new__ = _FrozenDict.__new__

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

    def __rmul__(self, other):
        return other

    def __repr__(self):
        return '{}()'.format(self.__class__.__name__)

# The identity singleton
IDENTITY = Identity()

def _make_domain(*args, **kwargs):
    'iterable or range() args -> iterable'
    if not args and not kwargs:
        raise TypeError('expected arguments')
    try:
        return list(range(*args, **kwargs))
    except TypeError:
        pass
    return list(*args, **kwargs)

def random_permutation(*args, **kwargs):
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
    return Permutation(zip(domain, vals))

def random_cycle(*args, **kwargs):
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
    return Cycle(cycle)
