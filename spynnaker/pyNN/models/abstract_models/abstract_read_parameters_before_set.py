# Copyright (c) 2017-2019 The University of Manchester
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

from six import add_metaclass
from spinn_utilities.abstract_base import AbstractBase, abstractmethod


@add_metaclass(AbstractBase)
class AbstractReadParametersBeforeSet(object):
    """ A vertex whose parameters must be read before any can be set.
    """

    __slots__ = ()

    @abstractmethod
    def read_parameters_from_machine(
            self, transceiver, placement, vertex_slice):
        """ Read the parameters from the machine before any are changed.

        :param transceiver: the SpinnMan interface
        :type transceiver: ~spinnman.transceiver.Transceiver
        :param placement: the placement of a vertex
        :type placement: ~pacman.model.placements.Placement
        :param vertex_slice: the slice of atoms for this vertex
        :type vertex_slice: ~pacman.model.graphs.common.Slice
        """
