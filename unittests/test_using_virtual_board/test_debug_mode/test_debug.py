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

import os
import unittest
import spinn_front_end_common.utilities.report_functions.reports as \
    reports_names
from spinn_front_end_common.utilities.report_functions.network_specification \
    import _FILENAME as network_specification_file_name
from spinn_front_end_common.utilities.globals_variables import (
    report_default_directory)
from spinnaker_testbase import BaseTestCase
from spynnaker.pyNN.extra_algorithms.\
    spynnaker_neuron_network_specification_report import (_GRAPH_NAME)
import spynnaker8 as sim


class TestDebug(BaseTestCase):
    """
    that it does not crash in debug mode. All reports on.
    """

    # NO unittest_setup() as sim.setup is called

    def debug(self):
        reports = [
            # write_energy_report does not happen on a virtual machine
            # "Detailed_energy_report.rpt",
            # "energy_summary_report.rpt",
            # write_text_specs = False
            "data_spec_text_files",
            # write_router_reports
            reports_names._ROUTING_FILENAME,
            # write_partitioner_reports
            reports_names._PARTITIONING_FILENAME,
            # write_application_graph_placer_report
            reports_names._PLACEMENT_VTX_GRAPH_FILENAME,
            reports_names._PLACEMENT_CORE_GRAPH_FILENAME,
            reports_names._SDRAM_FILENAME,
            # write_machine_graph_placer_report
            reports_names._PLACEMENT_VTX_SIMPLE_FILENAME,
            reports_names._PLACEMENT_CORE_SIMPLE_FILENAME,
            # repeats reports_names._SDRAM_FILENAME,
            # write_router_info_report
            reports_names._VIRTKEY_FILENAME,
            # write_routing_table_reports not on a virtual boad
            # reports_names._ROUTING_TABLE_DIR,
            # reports_names._C_ROUTING_TABLE_DIR,
            # reports_names._COMPARED_FILENAME,
            # write_routing_compression_checker_report not on a virtual board
            # "routing_compression_checker_report.rpt",
            # write_routing_tables_from_machine_report not on a virtual board
            # routing_tables_from_machine_report,
            # write_memory_map_report
            # ??? used by MachineExecuteDataSpecification but not called ???
            # write_network_specification_report
            network_specification_file_name,
            # write_provenance_data
            "provenance_data",
            # write_tag_allocation_reports
            reports_names._TAGS_FILENAME,
            # write_algorithm_timings
            # "provenance_data/pacman.xml"  = different test
            # write_board_chip_report not on a virtual board
            # BoardChipReport.AREA_CODE_REPORT_NAME,
            # write_data_speed_up_report not on a virtual board
            # DataSpeedUpPacketGatherMachineVertex.REPORT_NAME
            _GRAPH_NAME,
            # TODO why svg when default is png
            _GRAPH_NAME + ".svg",
            ]
        sim.setup(1.0)
        pop = sim.Population(100, sim.IF_curr_exp, {}, label="pop")
        pop.record("v")
        inp = sim.Population(1, sim.SpikeSourceArray(
            spike_times=[0]), label="input")
        sim.Projection(inp, pop, sim.AllToAllConnector(),
                       synapse_type=sim.StaticSynapse(weight=5))
        sim.run(1000)
        pop.get_data("v")
        sim.end()

        found = os.listdir(report_default_directory())
        print(found)
        for report in reports:
            self.assertIn(report, found)

    def test_debug(self):
        self.runsafe(self.debug)


if __name__ == '__main__':
    unittest.main()
