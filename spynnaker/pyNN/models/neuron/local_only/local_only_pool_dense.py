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
import numpy
from collections import defaultdict
from spinn_utilities.overrides import overrides
from data_specification.enums.data_type import DataType
from spinn_front_end_common.utilities.constants import BYTES_PER_WORD
from spinn_front_end_common.utilities.globals_variables import (
    machine_time_step_ms)
from spynnaker.pyNN.exceptions import SynapticConfigurationException
from spynnaker.pyNN.models.neural_projections.connectors import (
    PoolDenseConnector)
from spynnaker.pyNN.models.neuron.synapse_dynamics import (
    AbstractSupportsSignedWeights)
from .abstract_local_only import AbstractLocalOnly


class LocalOnlyPoolDense(AbstractLocalOnly, AbstractSupportsSignedWeights):
    """ A convolution synapse dynamics that can process spikes with only DTCM
    """

    @overrides(AbstractLocalOnly.merge)
    def merge(self, synapse_dynamics):
        if not isinstance(synapse_dynamics, LocalOnlyPoolDense):
            raise SynapticConfigurationException(
                "All Projections of this Population must have a synapse_type"
                " of LocalOnlyPoolDense")
        return synapse_dynamics

    @overrides(AbstractLocalOnly.get_vertex_executable_suffix)
    def get_vertex_executable_suffix(self):
        return "_pool_dense"

    @property
    @overrides(AbstractLocalOnly.changes_during_run)
    def changes_during_run(self):
        return False

    @overrides(AbstractLocalOnly.get_parameters_usage_in_bytes)
    def get_parameters_usage_in_bytes(
            self, vertex_slice, incoming_projections):
        n_bytes = 0
        for incoming in incoming_projections:
            s_info = incoming._synapse_information
            if not isinstance(s_info.connector, PoolDenseConnector):
                raise SynapticConfigurationException(
                    "Only PoolDenseConnector can be used with a synapse type"
                    " of PoolDense")
            app_edge = incoming._projection_edge
            in_slices = app_edge.pre_vertex.splitter.get_out_going_slices()[0]
            n_bytes += s_info.connector.local_only_n_bytes(
                in_slices, vertex_slice)

        return (2 * BYTES_PER_WORD) + n_bytes

    @overrides(AbstractLocalOnly.write_parameters)
    def write_parameters(
            self, spec, region, routing_info, incoming_projections,
            machine_vertex, weight_scales):

        # Get all the incoming vertices and keys so we can sort
        edge_info = list()
        for incoming in incoming_projections:
            app_edge = incoming._projection_edge
            # Keep track of all the same source squares, so they can be
            # merged; this will make sure the keys line up!
            edges_for_source = defaultdict(list)
            for edge in app_edge.machine_edges:
                if edge.post_vertex == machine_vertex:
                    r_info = routing_info.get_routing_info_for_edge(edge)
                    vertex_slice = edge.pre_vertex.vertex_slice
                    key = (app_edge.pre_vertex, vertex_slice)
                    edges_for_source[key].append((edge, r_info))

            # Merge edges with the same source
            for (_, vertex_slice), edge_list in edges_for_source.items():
                group_key = edge_list[0][1].first_key
                group_mask = edge_list[0][1].first_mask
                for edge, r_info in edge_list:
                    group_key, group_mask = self.__merge_key_and_mask(
                        group_key, group_mask, r_info.first_key,
                        r_info.first_mask)
                edge_info.append(
                    (incoming, vertex_slice, group_key, group_mask))

        size = self.get_parameters_usage_in_bytes(
            machine_vertex.vertex_slice, incoming_projections)
        spec.reserve_memory_region(region, size, label="LocalOnlyConvolution")
        spec.switch_write_focus(region)

        # Write the common spec
        post_slice = machine_vertex.vertex_slice
        n_post = numpy.prod(post_slice.shape)
        spec.write_value(n_post, data_type=DataType.UINT32)
        spec.write_value(len(edge_info), data_type=DataType.UINT32)

        # Write spec for each connector, sorted by key
        edge_info.sort(key=lambda e: e[3])
        for incoming, vertex_slice, key, mask in edge_info:
            s_info = incoming._synapse_information
            app_edge = incoming._projection_edge
            s_info.connector.write_local_only_data(
                spec, app_edge, vertex_slice, post_slice, key, mask,
                weight_scales)

    def __merge_key_and_mask(self, key_a, mask_a, key_b, mask_b):
        new_xs = ~(key_a ^ key_b)
        mask = mask_a & mask_b & new_xs
        key = (key_a | key_b) & mask
        return key, mask

    @property
    @overrides(AbstractLocalOnly.delay)
    def delay(self):
        return machine_time_step_ms()

    @overrides(AbstractLocalOnly.set_delay)
    def set_delay(self, delay):
        # We don't need no stinking delay
        pass

    @property
    @overrides(AbstractLocalOnly.weight)
    def weight(self):
        # We don't have a weight here, it is in the connector
        return 0

    @overrides(AbstractSupportsSignedWeights.get_positive_synapse_index)
    def get_positive_synapse_index(self, incoming_projection):
        post = incoming_projection._projection_edge.post_vertex
        conn = incoming_projection._synapse_information.connector
        return post.get_synapse_id_by_target(conn.positive_receptor_type)

    @overrides(AbstractSupportsSignedWeights.get_negative_synapse_index)
    def get_negative_synapse_index(self, incoming_projection):
        post = incoming_projection._projection_edge.post_vertex
        conn = incoming_projection._synapse_information.connector
        return post.get_synapse_id_by_target(conn.negative_receptor_type)

    @overrides(AbstractSupportsSignedWeights.get_maximum_positive_weight)
    def get_maximum_positive_weight(self, incoming_projection):
        conn = incoming_projection._synapse_information.connector
        # We know the connector doesn't care about the argument
        max_weight = numpy.amax(conn.weights)
        return max_weight if max_weight > 0 else 0

    @overrides(AbstractSupportsSignedWeights.get_minimum_negative_weight)
    def get_minimum_negative_weight(self, incoming_projection):
        conn = incoming_projection._synapse_information.connector
        # This is different because the connector happens to support this
        min_weight = numpy.amin(conn.weights)
        return min_weight if min_weight < 0 else 0

    @overrides(AbstractSupportsSignedWeights.get_mean_positive_weight)
    def get_mean_positive_weight(self, incoming_projection):
        conn = incoming_projection._synapse_information.connector
        pos_weights = conn.weights[conn.weights > 0]
        if not len(pos_weights):
            return 0
        return numpy.mean(pos_weights)

    @overrides(AbstractSupportsSignedWeights.get_mean_negative_weight)
    def get_mean_negative_weight(self, incoming_projection):
        conn = incoming_projection._synapse_information.connector
        neg_weights = conn.weights[conn.weights < 0]
        if not len(neg_weights):
            return 0
        return numpy.mean(neg_weights)

    @overrides(AbstractSupportsSignedWeights.get_variance_positive_weight)
    def get_variance_positive_weight(self, incoming_projection):
        conn = incoming_projection._synapse_information.connector
        pos_weights = conn.weights[conn.weights > 0]
        if not len(pos_weights):
            return 0
        return numpy.var(pos_weights)

    @overrides(AbstractSupportsSignedWeights.get_variance_negative_weight)
    def get_variance_negative_weight(self, incoming_projection):
        conn = incoming_projection._synapse_information.connector
        neg_weights = conn.weights[conn.weights < 0]
        if not len(neg_weights):
            return 0
        return numpy.var(neg_weights)