"""Bracket a minimum using successive function calls

:class:`InvertedIntegerOptimization`: inverted integer optimizer

"""
from __future__ import division


class InvertedIntegerOptimization(object):
    def __init__(self, (a, b, c), (fa, fb, fc)):
        if type(a) is not int or type(b) is not int or type(c) is not int:
            raise TypeError("x-values should be integer")
        if not fb < fa or not fb < fc:
            raise TypeError("Minimum is not correctly bracketed")

        self._set_interval((a, b, c), (fa, fb, fc))

    def _set_interval(self, (a, b, c), (fa, fb, fc)):
        self.a = a
        self.b = b
        self.c = c
        self.fa = fa
        self.fb = fb
        self.fc = fc

    def first_step(self):
        return self._guess_next_x()

    def _guess_next_x(self):
        if self.b - self.a > self.c - self.b:
            x = (self.a + self.b) / 2
        else:
            x = (self.b + self.c) / 2
        x = int(round(x))
        self.x = x
        return x

    def next_step(self, fx):
        if self.x < self.b:
            if fx < self.fb:
                self._set_interval((self.a, self.x, self.b),
                                   (self.fa, fx, self.fb))
            else:
                self._set_interval((self.x, self.b, self.c),
                                   (fx, self.fb, self.fc))
        else:
            if fx < self.fb:
                self._set_interval((self.b, self.x, self.c),
                                   (self.fb, fx, self.fc))
            else:
                self._set_interval((self.a, self.b, self.x),
                                   (self.fa, self.fb, fx))

        is_optimum = self._is_optimum()
        if is_optimum:
            return self.b, True
        else:
            x = self._guess_next_x()
            return x, False

    def _is_optimum(self):
        if self.a == self.b or self.b == self.c or \
           self.c - self.b == self.b - self.a == 1:
            return True
        else:
            return False
