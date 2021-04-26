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
from enum import Enum

from spinn_utilities.overrides import overrides
from spinn_utilities.abstract_base import abstractmethod
from spinn_front_end_common.utilities.constants import BYTES_PER_WORD
from spynnaker.pyNN.exceptions import SynapticConfigurationException
from spynnaker.pyNN.models.abstract_models import (
    ReceivesSynapticInputsOverSDRAM, SendsSynapticInputsOverSDRAM)
from spynnaker.pyNN.utilities.utility_calls import get_time_to_write_us
from .population_machine_common import CommonRegions, PopulationMachineCommon
from .population_machine_synapses import SynapseRegions
from .population_machine_synapses_provenance import SynapseProvenance

# Size of SDRAM params = 1 word for address + 1 word for size
#  + 1 word for time to send
SDRAM_PARAMS_SIZE = 3 * BYTES_PER_WORD

# Overhead in time to write, which includes the clearing of input spikes
TIME_TO_CLEAR_SPIKES = 50


class PopulationSynapsesMachineVertexCommon(
        PopulationMachineCommon,
        SendsSynapticInputsOverSDRAM):
    """ Common parts of a machine vertex for the synapses of a Population
    """

    __slots__ = [
        "__sdram_partition"]

    class REGIONS(Enum):
        """Regions for populations."""
        SYSTEM = 0
        PROVENANCE_DATA = 1
        PROFILING = 2
        RECORDING = 3
        SYNAPSE_PARAMS = 4
        DIRECT_MATRIX = 5
        SYNAPTIC_MATRIX = 6
        POPULATION_TABLE = 7
        SYNAPSE_DYNAMICS = 8
        STRUCTURAL_DYNAMICS = 9
        BIT_FIELD_FILTER = 10
        SDRAM_EDGE_PARAMS = 11
        CONNECTOR_BUILDER = 12
        BIT_FIELD_BUILDER = 13
        BIT_FIELD_KEY_MAP = 14

    # Regions for this vertex used by common parts
    COMMON_REGIONS = CommonRegions(
        system=REGIONS.SYSTEM.value,
        provenance=REGIONS.PROVENANCE_DATA.value,
        profile=REGIONS.PROFILING.value,
        recording=REGIONS.RECORDING.value)

    # Regions for this vertex used by synapse parts
    SYNAPSE_REGIONS = SynapseRegions(
        synapse_params=REGIONS.SYNAPSE_PARAMS.value,
        direct_matrix=REGIONS.DIRECT_MATRIX.value,
        pop_table=REGIONS.POPULATION_TABLE.value,
        synaptic_matrix=REGIONS.SYNAPTIC_MATRIX.value,
        synapse_dynamics=REGIONS.SYNAPSE_DYNAMICS.value,
        structural_dynamics=REGIONS.STRUCTURAL_DYNAMICS.value,
        bitfield_builder=REGIONS.BIT_FIELD_BUILDER.value,
        bitfield_key_map=REGIONS.BIT_FIELD_KEY_MAP.value,
        bitfield_filter=REGIONS.BIT_FIELD_FILTER.value,
        connection_builder=REGIONS.CONNECTOR_BUILDER.value
    )

    _PROFILE_TAG_LABELS = {
        0: "TIMER_SYNAPSES",
        1: "DMA_READ",
        2: "INCOMING_SPIKE",
        3: "PROCESS_FIXED_SYNAPSES",
        4: "PROCESS_PLASTIC_SYNAPSES"}

    def __init__(
            self, resources_required, label, constraints, app_vertex,
            vertex_slice):
        """
        :param ~pacman.model.resources.ResourceContainer resources_required:
            The resources used by the vertex
        :param str label: The label of the vertex
        :param list(~pacman.model.constraints.AbstractConstraint) constraints:
            Constraints for the vertex
        :param AbstractPopulationVertex app_vertex:
            The associated application vertex
        :param ~pacman.model.graphs.common.Slice vertex_slice:
            The slice of the population that this implements
        """
        super(PopulationSynapsesMachineVertexCommon, self).__init__(
            label, constraints, app_vertex, vertex_slice, resources_required,
            self.COMMON_REGIONS,
            SynapseProvenance.N_ITEMS,
            self._PROFILE_TAG_LABELS, self.__get_binary_file_name(app_vertex))
        self.__sdram_partition = None

    def set_sdram_partition(self, sdram_partition):
        """ Set the SDRAM partition.  Must only be called once per instance

        :param ~pacman.model.graphs.machine\
                .SourceSegmentedSDRAMMachinePartition sdram_partition:
            The SDRAM partition to receive synapses from
        """
        if self.__sdram_partition is not None:
            raise SynapticConfigurationException(
                "Trying to set SDRAM partition more than once")
        self.__sdram_partition = sdram_partition

    @staticmethod
    def __get_binary_file_name(app_vertex):
        """ Get the local binary filename for this vertex.  Static because at
            the time this is needed, the local app_vertex is not set.

        :param AbstractPopulationVertex app_vertex:
            The associated application vertex
        :rtype: str
        """

        # Reunite title and extension and return
        return "synapses" + app_vertex.synapse_executable_suffix + ".aplx"

    @overrides(PopulationMachineCommon._append_additional_provenance)
    def _append_additional_provenance(
            self, provenance_items, prov_list_from_machine, placement):
        # translate into provenance data items
        self._append_synapse_provenance(
            provenance_items, prov_list_from_machine, 0, placement)

    @abstractmethod
    def _append_synapse_provenance(
            self, provenance_items, prov_list_from_machine, offset, placement):
        """ Extract and add synapse provenance to the list of provenance items

        :param
            list(~spinn_front_end_common.utilities.utility_objs.ProvenanceDataItem)\
            provenance_items: The items already read, to append to
        :param list(int) prov_list_from_machine:
            The values read from the machine to be decoded
        :param int offset: Where in the list from the machine to start reading
        :param ~pacman.model.placements.Placement placement:
            Which vertex are we retrieving from, and where was it
        :return: The number of items read from prov_list_from_machine
        :rtype: int
        """

    @overrides(PopulationMachineCommon.get_recorded_region_ids)
    def get_recorded_region_ids(self):
        ids = self._app_vertex.synapse_recorder.recorded_ids_by_slice(
            self.vertex_slice)
        return ids

    def _write_sdram_edge_spec(self, spec):
        """ Write information about SDRAM Edge

        :param DataSpecificationGenerator spec:
            The generator of the specification to write
        """
        send_size = self.__sdram_partition.get_sdram_size_of_region_for(self)
        n_send_cores = len(self.__sdram_partition.pre_vertices)
        spec.reserve_memory_region(
            region=self.REGIONS.SDRAM_EDGE_PARAMS.value,
            size=SDRAM_PARAMS_SIZE, label="SDRAM Params")
        spec.switch_write_focus(self.REGIONS.SDRAM_EDGE_PARAMS.value)
        spec.write_value(
            self.__sdram_partition.get_sdram_base_address_for(self))
        spec.write_value(send_size)
        spec.write_value(TIME_TO_CLEAR_SPIKES +
                         get_time_to_write_us(send_size, n_send_cores))

    @overrides(SendsSynapticInputsOverSDRAM.sdram_requirement)
    def sdram_requirement(self, sdram_machine_edge):
        if isinstance(sdram_machine_edge.post_vertex,
                      ReceivesSynapticInputsOverSDRAM):
            return sdram_machine_edge.post_vertex.n_bytes_for_transfer
        raise SynapticConfigurationException(
            "Unknown post vertex type in edge {}".format(sdram_machine_edge))