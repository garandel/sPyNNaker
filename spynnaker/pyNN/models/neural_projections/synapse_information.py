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

from spinn_front_end_common.utilities.globals_variables import get_simulator


class SynapseInformation(object):
    """ Contains the synapse information including the connector, synapse type\
        and synapse dynamics
    """
    __slots__ = [
        "__connector",
        "__pre_population",
        "__post_population",
        "__prepop_is_view",
        "__postpop_is_view",
        "__rng",
        "__synapse_dynamics",
        "__synapse_type",
        "__weight",
        "__delay"]

    def __init__(self, connector, pre_population, post_population,
                 prepop_is_view, postpop_is_view, rng,
                 synapse_dynamics, synapse_type,
                 weight=None, delay=None):
        self.__connector = connector
        self.__pre_population = pre_population
        self.__post_population = post_population
        self.__prepop_is_view = prepop_is_view
        self.__postpop_is_view = postpop_is_view
        self.__rng = (rng or get_simulator().get_pynn_NumpyRNG()())
        self.__synapse_dynamics = synapse_dynamics
        self.__synapse_type = synapse_type
        self.__weight = weight
        self.__delay = delay

    @property
    def connector(self):
        return self.__connector

    @property
    def pre_population(self):
        return self.__pre_population

    @property
    def post_population(self):
        return self.__post_population

    @property
    def prepop_is_view(self):
        return self.__prepop_is_view

    @property
    def postpop_is_view(self):
        return self.__postpop_is_view

    @property
    def rng(self):
        return self.__rng

    @property
    def synapse_dynamics(self):
        return self.__synapse_dynamics

    @property
    def synapse_type(self):
        return self.__synapse_type

    @property
    def weight(self):
        return self.__weight

    @property
    def delay(self):
        return self.__delay
