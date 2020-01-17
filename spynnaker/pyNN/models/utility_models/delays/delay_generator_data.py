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

import numpy
from data_specification.enums.data_type import DataType
from spinn_front_end_common.utilities.constants import BYTES_PER_WORD


class DelayGeneratorData(object):
    """ Data for each connection of the delay generator
    """
    __slots__ = (
        "__timestep_in_us",
        "__max_delayed_row_n_synapses",
        "__max_row_n_synapses",
        "__max_stage",
        "__post_slices",
        "__post_slice_index",
        "__post_vertex_slice",
        "__pre_slices",
        "__pre_slice_index",
        "__pre_vertex_slice",
        "__synapse_information")

    BASE_SIZE = 8 * BYTES_PER_WORD

    def __init__(
            self, max_row_n_synapses, max_delayed_row_n_synapses,
            pre_slices, pre_slice_index, post_slices, post_slice_index,
            pre_vertex_slice, post_vertex_slice, synapse_information,
            max_stage, timestep_in_us):
        self.__max_row_n_synapses = max_row_n_synapses
        self.__max_delayed_row_n_synapses = max_delayed_row_n_synapses
        self.__pre_slices = pre_slices
        self.__pre_slice_index = pre_slice_index
        self.__post_slices = post_slices
        self.__post_slice_index = post_slice_index
        self.__pre_vertex_slice = pre_vertex_slice
        self.__post_vertex_slice = post_vertex_slice
        self.__synapse_information = synapse_information
        self.__max_stage = max_stage
        self.__timestep_in_us = timestep_in_us

    @property
    def size(self):
        """ The size of the generated data in bytes

        :rtype: int
        """
        connector = self.__synapse_information.connector

        return (
            self.BASE_SIZE + connector.gen_connector_params_size_in_bytes +
            connector.gen_delay_params_size_in_bytes(
                self.__synapse_information.rounded_delays_in_ms(
                    self.__timestep_in_us)))

    @property
    def gen_data(self):
        """ Get the data to be written for this connection

        :rtype: numpy array of uint32
        """
        connector = self.__synapse_information.connector
        items = list()
        delays = self.__synapse_information.rounded_delays_in_ms(
            self.__timestep_in_us)
        items.append(numpy.array([
            self.__max_row_n_synapses,
            self.__max_delayed_row_n_synapses,
            self.__pre_vertex_slice.lo_atom,
            self.__pre_vertex_slice.n_atoms,
            self.__max_stage,
            DataType.S1615.encode_as_int(1000.0 / self.__timestep_in_us),
            connector.gen_connector_id,
            connector.gen_delays_id(delays)],
            dtype="uint32"))
        items.append(connector.gen_connector_params(
            self.__pre_slices, self.__pre_slice_index, self.__post_slices,
            self.__post_slice_index, self.__pre_vertex_slice,
            self.__post_vertex_slice, self.__synapse_information.synapse_type,
            self.__synapse_information))
        items.append(connector.gen_delay_params(
            delays, self.__pre_vertex_slice, self.__post_vertex_slice))
        return numpy.concatenate(items)
