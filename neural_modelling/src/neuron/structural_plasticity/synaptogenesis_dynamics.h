/*
 * Copyright (c) 2017-2019 The University of Manchester
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

/*!
 * \dir
 * \brief Structural plasticity interface and algorithms
 * \file
 * \brief This file contains the main interface for structural plasticity
 * \author Petrut Bogdan
 */
#ifndef _SYNAPTOGENESIS_DYNAMICS_H_
#define _SYNAPTOGENESIS_DYNAMICS_H_

#include <common/neuron-typedefs.h>

//! \brief Initialisation of synaptic rewiring (synaptogenesis)
//!     parameters (random seed, spread of receptive field etc.)
//! \param[in] sdram_sp_address: Address of the start of the SDRAM region
//!     which contains synaptic rewiring params.
//! \param[in,out] recording_regions_used:
//!     Variable used to track what recording regions have been used
//! \return Whether we were successful.
bool synaptogenesis_dynamics_initialise(
        address_t sdram_sp_address, uint32_t *recording_regions_used);

//! \brief Trigger the process of synaptic rewiring
//! \details Usually called on a timer registered in c_main()
//! \param[in] time: the current timestep
//! \param[out] spike: variable to hold the spike
//! \param[out] synaptic_row: variable to hold the address of the row
//! \param[out] n_bytes: variable to hold the size of the row
//! \return True if a row is to be transferred, false otherwise
bool synaptogenesis_dynamics_rewire(uint32_t time,
        spike_t *spike, synaptic_row_t *synaptic_row, uint32_t *n_bytes);

//! \brief Perform the actual restructuring of a row
//! \param[in] time: The time of the restructure
//! \param[in] row: The row to restructure
//! \return True if the row was changed and needs to be written back
bool synaptogenesis_row_restructure(uint32_t time, synaptic_row_t row);

//! \brief Indicates that a spike has been received
//! \param[in] time: The time that the spike was received at
//! \param[in] spike: The received spike
void synaptogenesis_spike_received(uint32_t time, spike_t spike);

//! \brief Number of updates to do of synaptogenesis this time step
//! \return The number of updates to do this time step
uint32_t synaptogenesis_n_updates(void);

//! \brief Print a certain data object
void print_post_to_pre_entry(void);

#endif // _SYNAPTOGENESIS_DYNAMICS_H_
