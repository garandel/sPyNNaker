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
 * \file
 * \brief implementation of synapse_types.h for a simple duel exponential decay
 * to synapses.
 *
 * \details If we have combined excitatory_one/excitatory_two/inhibitory
 * synapses it will be because both excitatory and inhibitory synaptic
 * time-constants (and thus propogators) are identical.
 */

#ifndef _SYNAPSE_TYPES_DUAL_EXCITATORY_EXPONENTIAL_IMPL_H_
#define _SYNAPSE_TYPES_DUAL_EXCITATORY_EXPONENTIAL_IMPL_H_

//---------------------------------------
// Macros
//---------------------------------------
//! \brief Number of bits to encode the synapse type
//! \details <tt>ceil(log2(#SYNAPSE_TYPE_COUNT))</tt>
#define SYNAPSE_TYPE_BITS 2
//! \brief Number of synapse types
//! \details <tt>#NUM_EXCITATORY_RECEPTORS + #NUM_INHIBITORY_RECEPTORS</tt>
#define SYNAPSE_TYPE_COUNT 3

//! Number of excitatory receptors
#define NUM_EXCITATORY_RECEPTORS 2
//! Number of inhibitory receptors
#define NUM_INHIBITORY_RECEPTORS 1

#include <neuron/decay.h>
#include <debug.h>
#include "synapse_types.h"

//---------------------------------------
// Synapse parameters
//---------------------------------------
//! Buffer used for result of synapse_types_get_excitatory_input()
input_t excitatory_response[NUM_EXCITATORY_RECEPTORS];
//! Buffer used for result of synapse_types_get_inhibitory_input()
input_t inhibitory_response[NUM_INHIBITORY_RECEPTORS];

//! Parameters for an exponential decay
typedef struct exp_params_t {
    decay_t decay;                  //!< Decay multiplier per timestep
    decay_t init;                   //!< Initial decay factor
    input_t synaptic_input_value;   //!< The actual synaptic contribution
} exp_params_t;

struct synapse_param_t {
    exp_params_t exc;           //!< First excitatory synaptic input
    exp_params_t exc2;          //!< Second excitatory synaptic input
    exp_params_t inh;           //!< Inhibitory synaptic input
};

//! The supported synapse type indices
typedef enum {
    EXCITATORY_ONE,             //!< First excitatory synaptic input
    EXCITATORY_TWO,             //!< Second excitatory synaptic input
    INHIBITORY,                 //!< Inhibitory synaptic input
} synapse_dual_input_buffer_regions;

//---------------------------------------
// Synapse shaping inline implementation
//---------------------------------------

//! \brief Shape a single parameter
//! \param[in,out] exp_param: The parameter to shape
static inline void exp_shaping(exp_params_t *exp_param) {
    // decay value according to decay constant
	exp_param->synaptic_input_value =
			decay_s1615(exp_param->synaptic_input_value, exp_param->decay);
}

//! \brief Decay the stuff thats sitting in the input buffers as these have not
//!     yet been processed and applied to the neuron.
//! \details
//!     This is to compensate for the valve behaviour of a synapse in biology
//!     (spike goes in, synapse opens, then closes slowly) plus the leaky
//!     aspect of a neuron.
//! \param[in,out] parameters: the parameters to update
static inline void synapse_types_shape_input(synapse_param_t *parameters) {
	exp_shaping(&parameters->exc);
	exp_shaping(&parameters->exc2);
	exp_shaping(&parameters->inh);
}

//! \brief Add input for a given timer period to a given neuron
//! \param[in,out] exp_param: the parameter to be updated
//! \param[in] input: the input to add.
static inline void add_input_exp(exp_params_t *exp_param, input_t input) {
	exp_param->synaptic_input_value = exp_param->synaptic_input_value +
			decay_s1615(input, exp_param->init);
}

//! \brief Add the inputs for a give timer period to a given neuron that is
//!     being simulated by this model
//! \param[in] synapse_type_index: the type of input that this input is to be
//!     considered (aka excitatory or inhibitory etc)
//! \param[in,out] parameters: the pointer to the parameters to use
//! \param[in] input: the inputs for that given synapse_type.
static inline void synapse_types_add_neuron_input(
        index_t synapse_type_index, synapse_param_t *parameters,
        input_t input) {
    switch (synapse_type_index) {
    case EXCITATORY_ONE:
    	add_input_exp(&parameters->exc, input);
    	break;
    case EXCITATORY_TWO:
    	add_input_exp(&parameters->exc2, input);
    	break;
    case INHIBITORY:
    	add_input_exp(&parameters->inh, input);
    	break;
    }
}

//! \brief Extract the excitatory input buffers from the buffers available
//!     for a given parameter set
//! \param[in] parameters: the pointer to the parameters to use
//! \return the excitatory input buffers for a given neuron ID.
static inline input_t* synapse_types_get_excitatory_input(
        synapse_param_t *parameters) {
    excitatory_response[0] = parameters->exc.synaptic_input_value;
    excitatory_response[1] = parameters->exc2.synaptic_input_value;
    return &excitatory_response[0];
}

//! \brief Extract the inhibitory input buffers from the buffers available
//!     for a given parameter set
//! \param[in] parameters: the pointer to the parameters to use
//! \return the inhibitory input buffers for a given neuron ID.
static inline input_t* synapse_types_get_inhibitory_input(
        synapse_param_t *parameters) {
    inhibitory_response[0] = parameters->inh.synaptic_input_value;
    return &inhibitory_response[0];
}

//! \brief Get a human readable string for the type of synapse.
//! \details
//!     Examples would be `X` = excitatory types, `I` = inhibitory types, etc.
//! \param[in] synapse_type_index: the synapse type index
//!     (there is a specific index interpretation in each synapse type)
//! \return a human readable short string representing the synapse type.
static inline const char *synapse_types_get_type_char(
        index_t synapse_type_index) {
    switch (synapse_type_index) {
    case EXCITATORY_ONE:
        return "X1";
    case EXCITATORY_TWO:
        return "X2";
    case INHIBITORY:
        return "I";
    default:
        log_debug("did not recognise synapse type %i", synapse_type_index);
        return "?";
    }
}

//! \brief Print the input for a neuron ID given the available inputs
//!     currently only executed when the models are in debug mode, as the prints
//!     are controlled from the synapses.c print_inputs() method.
//! \param[in] parameters: the pointer to the parameters to use
static inline void synapse_types_print_input(
        synapse_param_t *parameters) {
    io_printf(IO_BUF, "%12.6k + %12.6k - %12.6k",
            parameters->exc.synaptic_input_value,
            parameters->exc2.synaptic_input_value,
            parameters->inh.synaptic_input_value);
}

//! \brief Print the synapse type model parameters
//! \param[in] parameters: the pointer to the parameters to print
static inline void synapse_types_print_parameters(
        synapse_param_t *parameters) {
    log_info("exc_decay  = %11.4k\n", parameters->exc.decay);
    log_info("exc_init   = %11.4k\n", parameters->exc.init);
    log_info("exc2_decay = %11.4k\n", parameters->exc2.decay);
    log_info("exc2_init  = %11.4k\n", parameters->exc2.init);
    log_info("inh_decay  = %11.4k\n", parameters->inh.decay);
    log_info("inh_init   = %11.4k\n", parameters->inh.init);
    log_info("gsyn_excitatory_initial_value = %11.4k\n",
            parameters->exc.synaptic_input_value);
    log_info("gsyn_excitatory2_initial_value = %11.4k\n",
            parameters->exc2.synaptic_input_value);
    log_info("gsyn_inhibitory_initial_value = %11.4k\n",
            parameters->inh.synaptic_input_value);
}

#endif  // _SYNAPSE_TYPES_DUAL_EXCITATORY_EXPONENTIAL_IMPL_H_
