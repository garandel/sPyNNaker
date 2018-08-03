#include "spike_processing.h"
#include "population_table/population_table.h"
#include "synapse_row.h"
#include "synapses.h"
#include "structural_plasticity/synaptogenesis_dynamics.h"
#include <simulation.h>
#include <spin1_api.h>
#include <debug.h>

// The number of DMA Buffers to use
#define N_DMA_BUFFERS 2

// DMA tags
#define DMA_TAG_READ_SYNAPTIC_ROW 0
#define DMA_TAG_WRITE_PLASTIC_REGION 1

extern uint32_t time;

// True if the DMA "loop" is currently running
static bool dma_busy;

// The DTCM buffers for the synapse rows
static dma_buffer dma_buffers[N_DMA_BUFFERS];

// The index of the next buffer to be filled by a DMA
static uint32_t next_buffer_to_fill;

// The index of the buffer currently being filled by a DMA read
static uint32_t buffer_being_read;

static uint32_t max_n_words;

static spike_t spike=-1;

static uint32_t single_fixed_synapse[4];

uint32_t number_of_rewires=0;
bool any_spike = false;

// counter for number of spikes between timer events
uint32_t spikes_this_tick = 0;
uint32_t dmas_this_tick = 0;
uint32_t pipeline_restarts_this_tick = 0;
uint32_t spike_pipeline_deactivation_time = 0;


/* PRIVATE FUNCTIONS - static for inlining */


static inline void _do_dma_read(
        address_t row_address, size_t n_bytes_to_transfer) {

    // Write the SDRAM address of the plastic region and the
    // Key of the originating spike to the beginning of DMA buffer
    dma_buffer *next_buffer = &dma_buffers[next_buffer_to_fill];
    next_buffer->sdram_writeback_address = row_address;
    next_buffer->originating_spike = spike;
    next_buffer->n_bytes_transferred = n_bytes_to_transfer;

    // Start a DMA transfer to fetch this synaptic row into current
    // buffer
    buffer_being_read = next_buffer_to_fill;
    spin1_dma_transfer(
        DMA_TAG_READ_SYNAPTIC_ROW, row_address, next_buffer->row, DMA_READ,
        n_bytes_to_transfer);
    next_buffer_to_fill = (next_buffer_to_fill + 1) % N_DMA_BUFFERS;
}


static inline void _do_direct_row(address_t row_address) {
    single_fixed_synapse[3] = (uint32_t) row_address[0];
    synapses_process_synaptic_row(time, single_fixed_synapse, false, 0);
}

void _setup_synaptic_dma_read() {


	// put spike counter here, to avoid packet-received callback becoming bloated
	//spikes_this_tick+=1;

	// Set up to store the DMA location and size to read
    address_t row_address;
    size_t n_bytes_to_transfer;

    bool setup_done = false;
    bool finished = false;
    uint cpsr = 0;
    while (!setup_done && !finished) {
        if (number_of_rewires) {
            number_of_rewires--;
            synaptogenesis_dynamics_rewire(time);
            setup_done = true;
        }

        // If there's more rows to process from the previous spike
        while (!setup_done && population_table_get_next_address(
                &row_address, &n_bytes_to_transfer)) {

            // This is a direct row to process
            if (n_bytes_to_transfer == 0) {
                _do_direct_row(row_address);
            } else {
                _do_dma_read(row_address, n_bytes_to_transfer);
                setup_done = true;
            }
        }

        // If there's more incoming spikes
        cpsr = spin1_int_disable();
        while (!setup_done && in_spikes_get_next_spike(&spike)) {
            spin1_mode_restore(cpsr);
            log_debug("Checking for row for spike 0x%.8x\n", spike);

            // Decode spike to get address of destination synaptic row
            if (population_table_get_first_address(
                    spike, &row_address, &n_bytes_to_transfer)) {

                // This is a direct row to process
                if (n_bytes_to_transfer == 0) {
                    _do_direct_row(row_address);
                } else {
                    _do_dma_read(row_address, n_bytes_to_transfer);
                    setup_done = true;
                }
            }
            cpsr = spin1_int_disable();
        }

        if (!setup_done) {
            finished = true;
        }
        cpsr = spin1_int_disable();
    }

    // If the setup was not done, and there are no more spikes,
    // stop trying to set up synaptic DMAs
    if (!setup_done) {
        log_debug("DMA not busy");
        dma_busy = false;
		spike_pipeline_deactivation_time = tc[T1_COUNT];

    }
    spin1_mode_restore(cpsr);
}

static inline void _setup_synaptic_dma_write(uint32_t dma_buffer_index) {

    // Get pointer to current buffer
    dma_buffer *buffer = &dma_buffers[dma_buffer_index];

    // Get the number of plastic bytes and the write back address from the
    // synaptic row
    size_t n_plastic_region_bytes =
        synapse_row_plastic_size(buffer->row) * sizeof(uint32_t);

    log_debug("Writing back %u bytes of plastic region to %08x",
              n_plastic_region_bytes, buffer->sdram_writeback_address + 1);

    // Start transfer
    spin1_dma_transfer(
        DMA_TAG_WRITE_PLASTIC_REGION, buffer->sdram_writeback_address + 1,
        synapse_row_plastic_region(buffer->row),
        DMA_WRITE, n_plastic_region_bytes);
}


/* CALLBACK FUNCTIONS - cannot be static */

// Called when a multicast packet is received
void _multicast_packet_received_callback(uint key, uint payload) {
    use(payload);
    any_spike = true;
    log_debug("Received spike %x at %d, DMA Busy = %d", key, time, dma_busy);

    spikes_this_tick++;

    // If there was space to add spike to incoming spike queue
    if (in_spikes_add_spike(key)) {

        // If we're not already processing synaptic DMAs,
        // flag pipeline as busy and trigger a feed event
        if (!dma_busy) {

            log_debug("Sending user event for new spike");
            if (spin1_trigger_user_event(0, 0)) {
                dma_busy = true;
            } else {
                log_debug("Could not trigger user event\n");
            }
        }
    } else {
        log_debug("Could not add spike");
    }
}

// Called when a user event is received
void _user_event_callback(uint unused0, uint unused1) {
    use(unused0);
    use(unused1);
    pipeline_restarts_this_tick++;
    _setup_synaptic_dma_read();
}

// Called when a DMA completes
void _dma_complete_callback(uint unused, uint tag) {
    use(unused);

    dmas_this_tick++;

    log_debug("DMA transfer complete with tag %u", tag);

    // Get pointer to current buffer
    uint32_t current_buffer_index = buffer_being_read;
    dma_buffer *current_buffer = &dma_buffers[current_buffer_index];

    // Start the next DMA transfer, so it is complete when we are finished
    _setup_synaptic_dma_read();

    // Process synaptic row repeatedly
    bool subsequent_spikes;
    do {

        // Are there any more incoming spikes from the same pre-synaptic
        // neuron?
        subsequent_spikes = in_spikes_is_next_spike_equal(
            current_buffer->originating_spike);

        // Process synaptic row, writing it back if it's the last time
        // it's going to be processed
        if (!synapses_process_synaptic_row(time, current_buffer->row,
            !subsequent_spikes, current_buffer_index)) {
            log_error(
                "Error processing spike 0x%.8x for address 0x%.8x"
                "(local=0x%.8x)",
                current_buffer->originating_spike,
                current_buffer->sdram_writeback_address,
                current_buffer->row);

            // Print out the row for debugging
            for (uint32_t i = 0;
                    i < (current_buffer->n_bytes_transferred >> 2); i++) {
                log_error("%u: 0x%.8x", i, current_buffer->row[i]);
            }

            rt_error(RTE_SWERR);
        }
    } while (subsequent_spikes);

//    // Start the next DMA transfer, so it is complete when we are finished
//    _setup_synaptic_dma_read();
}


/* INTERFACE FUNCTIONS - cannot be static */

bool spike_processing_initialise(
        size_t row_max_n_words, uint mc_packet_callback_priority,
        uint user_event_priority, uint incoming_spike_buffer_size) {

    // Allocate the DMA buffers
    for (uint32_t i = 0; i < N_DMA_BUFFERS; i++) {
        dma_buffers[i].row = (uint32_t*) spin1_malloc(
                row_max_n_words * sizeof(uint32_t));
        if (dma_buffers[i].row == NULL) {
            log_error("Could not initialise DMA buffers");
            return false;
        }
        log_debug(
            "DMA buffer %u allocated at 0x%08x", i, dma_buffers[i].row);
    }
    dma_busy = false;
    next_buffer_to_fill = 0;
    buffer_being_read = N_DMA_BUFFERS;
    max_n_words = row_max_n_words;

    // Allocate incoming spike buffer
    if (!in_spikes_initialize_spike_buffer(incoming_spike_buffer_size)) {
        return false;
    }

    // Set up for single fixed synapses (data that is consistent per direct row)
    single_fixed_synapse[0] = 0;
    single_fixed_synapse[1] = 1;
    single_fixed_synapse[2] = 0;

    // Set up the callbacks
    spin1_callback_on(MC_PACKET_RECEIVED,
            _multicast_packet_received_callback, mc_packet_callback_priority);
    simulation_dma_transfer_done_callback_on(
        DMA_TAG_READ_SYNAPTIC_ROW, _dma_complete_callback);
    spin1_callback_on(USER_EVENT, _user_event_callback, user_event_priority);

    return true;
}

void spike_processing_finish_write(uint32_t process_id) {
    _setup_synaptic_dma_write(process_id);
}

//! \brief returns the number of times the input buffer has overflowed
//! \return the number of times the input buffer has overloaded
uint32_t spike_processing_get_buffer_overflows() {

    // Check for buffer overflow
    return in_spikes_get_n_buffer_overflows();
}

//! \brief get the address of the circular buffer used for buffering received
//! spikes before processing them
//! \return address of circular buffer
circular_buffer get_circular_buffer(){
    return buffer;
}

//! \brief set the DMA status
//! \param[in] busy: bool
//! \return None
void set_dma_busy(bool busy) {
    dma_busy = busy;
}

//! \brief retrieve the DMA status
//! \return bool
bool get_dma_busy() {
    return dma_busy;
}

//! \brief set the number of times spike_processing has to attempt rewiring
//! \return bool: currently, always true
bool do_rewiring(int number_of_rew) {
    number_of_rewires+=number_of_rew;
    return true;
}

//! \brief has this core received any spikes since the last batch of rewires?
//! \return bool
bool received_any_spike() {
    return any_spike;
}

uint32_t spike_processing_get_and_reset_spikes_this_tick(){

	uint32_t spikes_to_return = spikes_this_tick;
	spikes_this_tick = 0;

	return spikes_to_return;
}

uint32_t spike_processing_get_and_reset_dmas_this_tick(){

	uint32_t dmas_to_return = dmas_this_tick;
	dmas_this_tick = 0;

	return dmas_to_return;
}

uint32_t spike_processing_get_and_reset_pipeline_restarts_this_tick(){
	uint32_t pipeline_restarts_to_return = pipeline_restarts_this_tick;
	pipeline_restarts_this_tick = 0;

	return pipeline_restarts_to_return;
}

uint32_t spike_processing_get_pipeline_deactivation_time(){
	return spike_pipeline_deactivation_time;
}
