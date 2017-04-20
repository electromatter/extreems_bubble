import pyprimes

def totient_factors_non_prime(n):
	if n <= 1:
		# Really it could be defined as zero?
		# but that would break the factorization code
		# that assumes that p >= 2
		raise ValueError('totient of n < 2 undefined')
	phi = 1
	for p, e in pyprimes.factorise(n):
		yield (p - 1), 1
		if e > 1:
			yield p, (e - 1)

def totient_factors(n):
	factors = {}
	for p, e in totient_factors_non_prime(n):
		if e > 1:
			factors[p] = factors.get(p, 0) + e
		elif e == 1:
			for p, e in pyprimes.factorise(p):
				factors[p] = factors.get(p, 0) + e
	return factors.items()

def eval_factors(factors, modulus=None):
	val = 1
	for p, e in factors:
		val = val * pow(p, e, modulus)
		if modulus is not None:
			val %= modulus
	return val

def totient(n):
	return eval_factors(totient_factors_non_prime(n))

_UNSPECIFIED=object()

class PrimitiveRootTest:
	def __init__(self, modulus):
		self.totient_factors = list(totient_factors(modulus))
		self.totient = eval_factors(self.totient_factors)
		self.modulus = modulus
		self.primes = pyprimes.primes()

	def __new__(cls, n=_UNSPECIFIED, modulus=_UNSPECIFIED):
		if modulus is _UNSPECIFIED or n is _UNSPECIFIED:
			return super(cls, cls).__new__(cls)
		return cls(modulus)(n)

	def __iter__(self):
		return self

	def __next__(self):
		if self.primes is None:
			raise StopIteration

		for p in self.primes:
			if p > self.modulus:
				self.primes = None
				raise StopIteration

			if self(p):
				return p

	def __call__(self, n):
		n %= self.modulus

		if n == 0:
			return False

		for p, _ in self.totient_factors:
			if pow(n, self.totient // p, self.totient) == 1:
				return False

		return True

primitive_roots = PrimitiveRootTest
is_primitive_root = PrimitiveRootTest

# WARNING: this is recursive
def egcd(a, b):
	if b == 0:
		return (a, 1, 0)
	q, r = divmod(a, b)
	g, s, t = egcd(b, r)
	return (g, t, s - q*t)

def gcd(a, b):
	while b > 0:
		a, b = b, a % b
	return a

def is_coprime(a, b):
	return gcd(a, b) == 1

def mul_inv(n, mod):
	g, x, _ = egcd(n, mod)
	if g != 1:
		raise ValueError('%i is not coprime to %i' % (n, mod))
	return x % mod

