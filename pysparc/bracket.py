"""Bracket a minimum using successive function calls

:class:`InvertedIntegerOptimization`: inverted integer optimizer

"""
from __future__ import division


class InvertedIntegerRootFinder(object):
    def __init__(self, (a, b), (fa, fb)):
        if type(a) is not int or type(b) is not int:
            raise TypeError("x-values should be integer")
        self._set_interval((a, b), (fa, fb))

    def _set_interval(self, (a, b), (fa, fb)):
        # root must be between a and b
        if not ((fa >= 0 and fb <= 0) or (fa <= 0 and fb >= 0)):
            raise TypeError("Root is not in (a, b)")
        else:
            self.a = a
            self.b = b
            self.fa = fa
            self.fb = fb

    def first_step(self):
        return self._guess_next_x()

    def _guess_next_x(self):
        x = int(round((self.a + self.b) / 2))
        self.x = x
        return x

    def next_step(self, fx):
        if self._sign(fx) == self._sign(self.fa):
            self._set_interval((self.x, self.b), (fx, self.fb))
        else:
            self._set_interval((self.a, self.x), (self.fa, fx))

        is_optimum = self._is_optimum(fx)
        if is_optimum:
            return self.x, True
        else:
            x = self._guess_next_x()
            return x, False

    def _is_optimum(self, fx):
        if fx == 0:
            return True
        elif self.a == self.b or self.b - self.a == 1:
            return True
        else:
            return False

    def _sign(self, value):
        if value < 0:
            return -1
        else:
            return 1


class ParallelInvertedIntegerRootFinder(object):
    def __init__(self, grouped_xvalues, grouped_fvalues):
        self._init_optimizations(InvertedIntegerRootFinder,
                                 grouped_xvalues, grouped_fvalues)

    def _init_optimizations(self, optimizer_class, grouped_xvalues,
                             grouped_fvalues):
        self.optimizations = []
        individual_optimization_xvalues = zip(*grouped_xvalues)
        individual_optimization_fvalues = zip(*grouped_fvalues)
        for xvalues, fvalues in zip(individual_optimization_xvalues,
                                    individual_optimization_fvalues):
            self.optimizations.append(optimizer_class(xvalues, fvalues))

    def first_step(self):
        return [opt.first_step() for opt in self.optimizations]

    def next_step(self, fvalues):
        results = [opt.next_step(fvalue) for opt, fvalue in
                   zip(self.optimizations, fvalues)]
        guesses, is_all_done = zip(*results)
        return guesses, is_all_done


class LinearInvertedIntegerRootFinder(InvertedIntegerRootFinder):
    def _guess_next_x(self):
        x0, y0 = self.a, self.fa
        x1, y1 = self.b, self.fb

        # f(x) = a * x + b
        a = (y0 - y1) / (x0 - x1)
        b = y0 - a * x0

        # solution of f(x) = 0
        x = int(round(-b / a))

        self.x = x
        return x

    def next_step(self, fx):
        if self._sign(fx) == self._sign(self.fa):
            self._set_interval((self.x, self.b), (fx, self.fb))
        else:
            self._set_interval((self.a, self.x), (self.fa, fx))

        is_optimum = self._is_optimum(fx)
        if is_optimum:
            return self.x, True
        else:
            x = self._guess_next_x()
            if x in [self.a, self.b]:
                return x, True
            else:
                return x, False

class LinearParallelInvertedIntegerRootFinder(
        ParallelInvertedIntegerRootFinder):
    def __init__(self, grouped_xvalues, grouped_fvalues):
        self._init_optimizations(LinearInvertedIntegerRootFinder,
                                 grouped_xvalues, grouped_fvalues)
