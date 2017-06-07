'Permutations as mappings'

__all__ = ('Permutation', 'Cycle', 'IDENTITY')

import _collections
import _random

def _gcd(*args):
    '''gcd(iterable)
    gcd(*args) -> gcd(args)

    Computes the greatest common divisor of all elements of iterable.
    '''
    if len(args) == 1 and hasattr(args[0], '__iter__'):
        args = iter(args[0])
    g = 0
    for x in args:
        while x > 0:
            x, g = g % x, x
    return g

def _lcm(*args):
    '''lcm(iterable)
    lcm(*args) -> lcm(args)

    Computes the least common multiple of all elements of iterable.
    '''
    if len(args) == 1 and hasattr(args[0], '__iter__'):
        args = iter(args[0])
    m = 1
    for x in args:
        m *= (x // _gcd(x, m))
    return m

class FrozenDict(_collections.abc.Mapping):
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
        return '%s.FrozenDict(%r)' % (__name__, self._map)

class Permutation(FrozenDict):
    '''Permutation() -> IDENTITY
    Permutation(mapping) -> extracts the permutation from the mapping
    Permutation(iterable) -> Permutation(dict(iterable))
    Permutation(**kwargs) -> Permutation(kwargs)

    This is an immutable permutation generalized from python mappings.
    Permutations support the usual mapping interface.
    '''

    __slots__ = ('__orbits', '__order')

    def __new__(cls, *args, **kwargs):
        # Extract the mapping from the arguments
        self = super().__new__(cls, *args, **kwargs)

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

        if len(orbits) == 0:
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

        if len(args) == 0:
            # Empty product
            return IDENTITY
        elif len(args) == 1:
            # Product with one term
            return Cycle(args)

        mapping = {}
        for cycle in reversed(args):
            mapping.update(cycle * mapping)

        return cls(mapping)

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
        return Permutation((k, self[other[k]]) for k in other)

    def __rmul__(self, other):
        'other * self -> other applied to self'
        return Permutation((k, other.get(v, v)) for k, v in self.items())

    def __call__(self, key):
        'Apply this permutation to key'
        return self[key]

    def __repr__(self):
        return '%s.Permutation.from_product%r' % (__name__, self.orbits())

class Cycle(Permutation):
    '''Cycle(iterable) -> create a cyclic permutation that maps each
        element if the iterable to the next.
    Cycle(*args) -> Cycle(args)

    If the argument is not a cyclic permutation, then ValueError is raised.
    '''

    __slots__ = ('__cycle')

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

        self = FrozenDict.__new__(cls, mapping)
        self.__cycle = args
        return self

    def __iter__(self):
        return self.__cycle

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
                index  = (index + exp) % order
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
                cycles.append(cycle)

        return Permutation.from_product(cycles)

    def __repr__(self):
        return '%s.Cycle%r' % (__name__, self.__cycle)

class Identity(Cycle):
    'The identity permutation that maps all elements to themselves'

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
    x = _make_domain(*args, **kwargs)
    y = list(x)
    _random.shuffle(y, rng)
    return Permutation(zip(x, y))

def random_cycle(*args, **kwargs):
    '''random_cycle(n) -> random cycle of n elements
    random_cycle(start, stop[, step]) ->
        random_cycle(range(start, stop, step))
    random_cycle(iterable) -> a random cycle of the iterable

    The optional keyword argument random can be used to specify
    the random number generator used to shuffle.
    '''
    rng = kwargs.pop('random', None)
    x = _make_domain(*args, **kwargs)
    _random.shuffle(x, rng)
    return Cycle(x)
