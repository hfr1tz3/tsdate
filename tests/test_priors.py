# MIT License
#
# Copyright (c) 2023 Tskit Developers
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""
Test cases for prior functionality used in tsdate
"""
import logging

import numpy as np
import pytest
import utility_functions

from tsdate.prior import ConditionalCoalescentTimes
from tsdate.prior import create_timepoints
from tsdate.prior import PriorParams
from tsdate.prior import SpansBySamples


class TestConditionalCoalescentTimes:
    def test_str(self):
        # Test how a CC times object is printed out (for debug purposes)
        priors = ConditionalCoalescentTimes(None, "gamma")
        lines = str(priors).split("\n")
        assert len(lines) == 1
        assert "gamma" in lines[0]

        priors.add(2)
        lines = str(priors).split("\n")
        assert len(lines) == 5
        assert lines[1].startswith("2")
        for n in PriorParams._fields:
            assert n in lines[1]
        for i, line in enumerate(lines[2:]):
            assert line.startswith(f" {i} descendants")
            assert line.endswith("]")

    def test_add_error(self):
        priors = ConditionalCoalescentTimes(None, "gamma")
        with pytest.raises(RuntimeError, match="cannot add"):
            priors.add(2, approximate=True)

    def test_clear_precalc_debug(self, caplog):
        priors = ConditionalCoalescentTimes(None, "gamma")
        caplog.set_level(logging.DEBUG)
        priors.clear_precalculated_priors()
        assert "not yet created" in caplog.text

    @pytest.mark.parametrize("logwt", [True, False])
    def test_mixture_expect_and_var(self, logwt):
        priors = ConditionalCoalescentTimes(None)
        priors.add(3)
        params = {3: {"descendant_tips": [3, 2], "span": np.array([0, 200])}}
        mean1, var1 = priors.mixture_expect_and_var(params, weight_by_log_span=logwt)
        params = {3: {"descendant_tips": [2], "span": np.array([100])}}
        mean2, var2 = priors.mixture_expect_and_var(params, weight_by_log_span=logwt)
        assert mean1 == pytest.approx(1 / 3)  # 1/N for a cherry
        assert var1 == pytest.approx(1 / 9)
        assert mean1 == mean2
        assert var1 == var2

    def test_mixture_expect_and_var_weight(self):
        priors = ConditionalCoalescentTimes(None)
        priors.add(4)
        priors.add(5)
        span = np.array([1, 3])
        params = {
            4: {"descendant_tips": [2], "span": span[0]},
            5: {"descendant_tips": [2], "span": span[1]},
        }
        linwt = priors.mixture_expect_and_var(params, weight_by_log_span=False)
        assert linwt[0] == pytest.approx(
            (1 / 4 * span[0] + 1 / 5 * span[1]) / np.sum(span)
        )

        # use exponential version to test log weights
        # The log weighting adds one to the value, so here we subtract one
        exp_span = np.exp(span) - 1
        params = {
            4: {"descendant_tips": [2], "span": exp_span[0]},
            5: {"descendant_tips": [2], "span": exp_span[1]},
        }
        logwt = priors.mixture_expect_and_var(params, weight_by_log_span=True)
        assert np.allclose(linwt, logwt)


class TestSpansBySamples:
    def test_repr(self):
        ts = utility_functions.single_tree_ts_n2()
        span_data = SpansBySamples(ts)
        rep = repr(span_data)
        assert rep.count("Node") == ts.num_nodes
        for t in ts.trees():
            for u in t.leaves():
                assert rep.count(f"{u}: {{}}") == 1

    def test_error_on_multiroot(self):
        ts = utility_functions.multiroot()
        with pytest.raises(ValueError, match="multiple roots"):
            SpansBySamples(ts)


class TestTimepoints:
    def test_create_timepoints(self):
        priors = ConditionalCoalescentTimes(None, "gamma")
        priors.add(3)
        tp = create_timepoints(priors, n_points=3)
        assert len(tp) == 4
        assert tp[0] == 0

    def test_create_timepoints_error(self):
        priors = ConditionalCoalescentTimes(None, "gamma")
        priors.add(2)
        priors.prior_distr = "bad_distr"
        with pytest.raises(ValueError, match="must be lognorm or gamma"):
            create_timepoints(priors, n_points=3)
