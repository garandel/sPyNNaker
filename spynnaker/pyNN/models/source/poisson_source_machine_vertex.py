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
from pacman.executor.injection_decorator import inject_items
from pacman.model.graphs.machine import MachineVertex
from spinn_front_end_common.abstract_models import (
    AbstractSupportsDatabaseInjection)
from spinn_front_end_common.interface.provenance import (
    ProvidesProvenanceDataFromMachineImpl)
from spinn_front_end_common.utilities.exceptions import ConfigurationException
from spynnaker.pyNN.utilities.constants import (
    LIVE_POISSON_CONTROL_PARTITION_ID)


class PoissonSourceMachineVertex(
        MachineVertex, ProvidesProvenanceDataFromMachineImpl,
        AbstractSupportsDatabaseInjection):

    __slots__ = [
        "__buffered_sdram_per_timestep",
        "__minimum_buffer_sdram",
        "__resources",
        "_vertex_index"]

    POISSON_SOURCE_REGIONS = Enum(
        value="POISSON_SOURCE_REGIONS",
        names=[('SYSTEM_REGION', 0),
               ('POISSON_PARAMS_REGION', 1),
               ('PROVENANCE_REGION', 2)])

    def __init__(
            self, resources_required, constraints=None,
            label=None):
        # pylint: disable=too-many-arguments
        super(PoissonSourceMachineVertex, self).__init__(
            label, constraints=constraints)
        self.__resources = resources_required
        self._vertex_index = None

    @property
    @overrides(MachineVertex.resources_required)
    def resources_required(self):
        return self.__resources

    @property
    @overrides(ProvidesProvenanceDataFromMachineImpl._provenance_region_id)
    def _provenance_region_id(self):
        return self.POISSON_SOURCE_REGIONS.PROVENANCE_REGION.value

    @property
    @overrides(
        ProvidesProvenanceDataFromMachineImpl._n_additional_data_items)
    def _n_additional_data_items(self):
        return 0

    @property
    def vertex_index(self):
        return self._vertex_index

    @vertex_index.setter
    def vertex_index(self, vertex_index):
        self._vertex_index = vertex_index

    @inject_items({"graph": "MemoryMachineGraph"})
    @overrides(
        AbstractSupportsDatabaseInjection.is_in_injection_mode,
        additional_arguments=["graph"])
    def is_in_injection_mode(self, graph):
        # pylint: disable=arguments-differ
        in_edges = graph.get_edges_ending_at_vertex_with_partition_name(
            self, LIVE_POISSON_CONTROL_PARTITION_ID)
        if len(in_edges) > 1:
            raise ConfigurationException(
                "Poisson source can only have one incoming control")
        return len(in_edges) == 1