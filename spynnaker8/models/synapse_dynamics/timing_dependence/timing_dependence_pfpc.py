# Copyright (c) 2021 The University of Manchester
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from spynnaker.pyNN.models.neuron.plasticity.stdp.timing_dependence import (
    TimingDependencePFPC as
    _BaseClass)
from spynnaker.pyNN.utilities.utility_calls import moved_in_v6


class TimingDependencePFPC(_BaseClass):
    """
    .. deprecated:: 6.0
        Use
        :py:class:`spynnaker.pyNN.models.neuron.plasticity.stdp.timing_dependence.TimingDependencePFPC`
        instead.
    """
    __slots__ = []

    def __init__(
            self, tau_plus=20.0, tau_minus=20.0, A_plus=0.01, A_minus=0.01,
            t_peak=100, kernel_scaling=1.0):
        r"""
        :param float tau_plus: :math:`\tau_+`
        :param float tau_minus: :math:`\tau_-`
        :param float A_plus: :math:`A^+`
        :param float A_minus: :math:`A^-`
        :param float t_peak: :math:`t_\mathrm{peak}`
        :param float kernel_scaling:
        """
        moved_in_v6("spynnaker8.models.synapse_dynamics.timing_dependence."
                    "TimingDependencePFPC",
                    "spynnaker.pyNN.models.neuron.plasticity.stdp."
                    "timing_dependence.TimingDependencePFPC")
        super(TimingDependencePFPC, self).__init__(
            tau_plus=tau_plus, tau_minus=tau_minus, A_plus=A_plus,
            A_minus=A_minus, t_peak=t_peak, kernel_scaling=kernel_scaling)