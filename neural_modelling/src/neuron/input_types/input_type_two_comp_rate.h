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


/*
 * SUMMARY
 * \brief input type for rate based Bern multicompartment model
 *
 *
 */

#ifndef _INPUT_TYPE_TWO_COMP_RATE_H_
#define _INPUT_TYPE_TWO_COMP_RATE_H_

#ifndef NUM_EXCITATORY_RECEPTORS
#define NUM_EXCITATORY_RECEPTORS 1
#error NUM_EXCITATORY_RECEPTORS was undefined.  It should be defined by a synapse\
	shaping include
#endif

#ifndef NUM_INHIBITORY_RECEPTORS
#define NUM_INHIBITORY_RECEPTORS 1
#error NUM_INHIBITORY_RECEPTORS was undefined.  It should be defined by a synapse\
	shaping include
#endif

#include "input_type.h"

typedef struct input_type_t {
} input_type_t;


static inline input_t* input_type_get_input_value(
        input_t* value, input_type_pointer_t input_type, uint16_t num_receptors) {
    use(input_type);
    use(num_receptors);
    //for (int i = 0; i < num_receptors; i++) {
    //    value[i] = value[i] >> 10;
    //}
    return &value[0];
}

static inline void input_type_convert_excitatory_input_to_current(
        input_t* exc_input, input_type_pointer_t input_type,
        state_t somatic_conductance) {

    use(input_type);
//    for (int i=0; i < NUM_EXCITATORY_RECEPTORS; i++) {
//        exc_input[i] = exc_input[i] *
//                (input_type->V_rev_E - membrane_voltage);
//    }

	// Convert conductance based (teacher) input
	exc_input[0] = exc_input[0] * somatic_conductance;


}

static inline void input_type_convert_inhibitory_input_to_current(
        input_t* inh_input, input_type_pointer_t input_type,
        state_t somatic_conductance) {

    use(input_type);
//    for (int i=0; i < NUM_INHIBITORY_RECEPTORS; i++) {
//        inh_input[i] = -inh_input[i] *
//                (input_type->V_rev_I - membrane_voltage);
//    }


	// Convert conductance based (teacher) input
	inh_input[0] = inh_input[0] * somatic_conductance;

}

#endif // _INPUT_TYPE_TWO_COMP_RATE_H_
