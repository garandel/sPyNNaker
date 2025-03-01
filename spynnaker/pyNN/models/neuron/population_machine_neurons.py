# Copyright (c) 2017-2020The University of Manchester
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
import ctypes
from collections import namedtuple

from spinn_utilities.abstract_base import abstractproperty, abstractmethod
from spinn_utilities.overrides import overrides
from spinn_front_end_common.interface.provenance import ProvenanceWriter
from spinn_front_end_common.utilities import helpful_functions
from spinn_front_end_common.utilities.constants import BYTES_PER_WORD
from spynnaker.pyNN.models.abstract_models import (
    AbstractReadParametersBeforeSet)
from spynnaker.pyNN.utilities.constants import SPIKE_PARTITION_ID
from spynnaker.pyNN.utilities.utility_calls import get_n_bits


class NeuronProvenance(ctypes.LittleEndianStructure):
    """ Provenance items from neuron processing
    """
    _fields_ = [
        # The timer tick at the end of simulation
        ("current_timer_tick", ctypes.c_uint32),
        # The number of misses of TDMA time slots
        ("n_tdma_misses", ctypes.c_uint32),
        # The earliest send time within any time step
        ("earliest_send", ctypes.c_uint32),
        # The latest send time within any time step
        ("latest_send", ctypes.c_uint32)
    ]

    N_ITEMS = len(_fields_)


# Identifiers for neuron regions
NeuronRegions = namedtuple(
    "NeuronRegions",
    ["neuron_params", "neuron_recording"])


class PopulationMachineNeurons(
        AbstractReadParametersBeforeSet, allow_derivation=True):
    """ Mix-in for machine vertices that have neurons in them
    """

    # This MUST stay empty to allow mixing with other things with slots
    __slots__ = []

    @abstractproperty
    def _app_vertex(self):
        """ The application vertex of the machine vertex.

        :note: This is likely to be available via the MachineVertex.

        :rtype: AbstractPopulationVertex
        """

    @abstractproperty
    def _vertex_slice(self):
        """ The slice of the application vertex atoms on this machine vertex.

        :note: This is likely to be available via the MachineVertex.

        :rtype: ~pacman.model.graphs.common.Slice
        """

    @abstractproperty
    def _slice_index(self):
        """ The index of the slice of this vertex in the list of slices

        :rtype: int
        """

    @abstractproperty
    def _key(self):
        """ The key for spikes.

        :rtype: int
        """

    @abstractmethod
    def _set_key(self, key):
        """ Set the key for spikes.

        :note: This is required because this class cannot have any storage.

        :param int key: The key to be set
        """

    @abstractproperty
    def _neuron_regions(self):
        """ The region identifiers for the neuron regions

        :rtype: .NeuronRegions
        """

    def _parse_neuron_provenance(
            self, label, x, y, p, provenance_data):
        """ Extract and yield neuron provenance

        :param str label: The label of the node
        :param int x: x coordinate of the chip where this core
        :param int y: y coordinate of the core where this core
        :param int p: virtual id of the core
        :param list(int) provenance_data: A list of data items to interpret
        :return: a list of provenance data items
        :rtype: iterator of ProvenanceDataItem
        """
        neuron_prov = NeuronProvenance(*provenance_data)
        self._app_vertex.get_tdma_provenance_item(
            x, y, p, label, neuron_prov.n_tdma_misses)
        with ProvenanceWriter() as db:
            db.insert_core(
                x, y, p, "Last_timer_tic_the_core_ran_to",
                neuron_prov.current_timer_tick)
            db.insert_core(
                x, y, p, "Earliest_send_time", neuron_prov.earliest_send)
            db.insert_core(
                x, y, p, "Latest_Send_time", neuron_prov.latest_send)

    def _write_neuron_data_spec(self, spec, routing_info, ring_buffer_shifts):
        """ Write the data specification of the neuron data

        :param ~data_specification.DataSpecificationGenerator spec:
            The data specification to write to
        :param ~pacman.model.routing_info.RoutingInfo routing_info:
            The routing information to read the key from
        :param list(int) ring_buffer_shifts:
            The shifts to apply to convert ring buffer values to S1615 values
        """
        # Get and store the key
        self._set_key(routing_info.get_first_key_from_pre_vertex(
            self, SPIKE_PARTITION_ID))

        # Write the neuron parameters
        self._write_neuron_parameters(spec, ring_buffer_shifts)

        # Write the neuron recording region
        neuron_recorder = self._app_vertex.neuron_recorder
        spec.reserve_memory_region(
            region=self._neuron_regions.neuron_recording,
            size=neuron_recorder.get_metadata_sdram_usage_in_bytes(
                self._vertex_slice),
            label="neuron recording")
        neuron_recorder.write_neuron_recording_region(
            spec, self._neuron_regions.neuron_recording, self._vertex_slice)

    def _write_neuron_parameters(self, spec, ring_buffer_shifts):
        """ Write the neuron parameters region

        :param ~data_specification.DataSpecificationGenerator spec:
            The data specification to write to
        :param list(int) ring_buffer_shifts:
            The shifts to apply to convert ring buffer values to S1615 values
        """
        self._app_vertex.set_has_run()

        # pylint: disable=too-many-arguments
        n_atoms = self._vertex_slice.n_atoms
        spec.comment("\nWriting Neuron Parameters for {} Neurons:\n".format(
            n_atoms))

        # Reserve and switch to the memory region
        params_size = self._app_vertex.get_sdram_usage_for_neuron_params(
            self._vertex_slice)
        spec.reserve_memory_region(
            region=self._neuron_regions.neuron_params, size=params_size,
            label='NeuronParams')
        spec.switch_write_focus(self._neuron_regions.neuron_params)

        # store the tdma data here for this slice.
        data = self._app_vertex.generate_tdma_data_specification_data(
            self._slice_index)
        spec.write_array(data)

        # Write whether the key is to be used, and then the key, or 0 if it
        # isn't to be used
        if self._key is None:
            spec.write_value(data=0)
            spec.write_value(data=0)
        else:
            spec.write_value(data=1)
            spec.write_value(data=self._key)

        # Write the number of neurons in the block:
        spec.write_value(data=n_atoms)
        spec.write_value(data=2**get_n_bits(n_atoms))

        # Write the ring buffer data
        # This is only the synapse types that need a ring buffer i.e. not
        # those stored in synapse dynamics
        n_synapse_types = self._app_vertex.neuron_impl.get_n_synapse_types()
        spec.write_value(n_synapse_types)
        spec.write_array(ring_buffer_shifts)

        # Write the neuron parameters
        neuron_data = self._app_vertex.neuron_impl.get_data(
            self._app_vertex.parameters, self._app_vertex.state_variables,
            self._vertex_slice)
        spec.write_array(neuron_data)

    @overrides(AbstractReadParametersBeforeSet.read_parameters_from_machine)
    def read_parameters_from_machine(
            self, transceiver, placement, vertex_slice):

        # locate SDRAM address to where the neuron parameters are stored
        neuron_region_sdram_address = \
            helpful_functions.locate_memory_region_for_placement(
                placement, self._neuron_regions.neuron_params,
                transceiver)

        # shift past the extra stuff before neuron parameters that we don't
        # need to read
        neurons_pre_size = (
            self._app_vertex.tdma_sdram_size_in_bytes +
            self._app_vertex.BYTES_TILL_START_OF_GLOBAL_PARAMETERS +
            (self._app_vertex.neuron_impl.get_n_synapse_types() *
             BYTES_PER_WORD))
        neuron_parameters_sdram_address = (
            neuron_region_sdram_address + neurons_pre_size)

        # get size of neuron params
        size_of_region = self._app_vertex.get_sdram_usage_for_neuron_params(
            vertex_slice) - neurons_pre_size

        # get data from the machine
        byte_array = transceiver.read_memory(
            placement.x, placement.y, neuron_parameters_sdram_address,
            size_of_region)

        # update python neuron parameters with the data
        self._app_vertex.neuron_impl.read_data(
            byte_array, 0, vertex_slice, self._app_vertex.parameters,
            self._app_vertex.state_variables)
