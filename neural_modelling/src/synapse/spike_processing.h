#ifndef _SPIKE_PROCESSING_H_
#define _SPIKE_PROCESSING_H_

#include <common/neuron-typedefs.h>
#include <common/in_spikes.h>
#include <spin1_api.h>

bool spike_processing_initialise(
    size_t row_max_n_bytes, uint mc_packet_callback_priority,
    uint user_event_priority, uint incoming_spike_buffer_size);

void spike_processing_finish_write(uint32_t process_id);

//! \brief returns the number of times the input buffer has overflowed
//! \return the number of times the input buffer has overflowed
uint32_t spike_processing_get_buffer_overflows();


//! DMA buffer structure combines the row read from SDRAM with
typedef struct dma_buffer {

    // Address in SDRAM to write back plastic region to
    address_t sdram_writeback_address;

    // Key of originating spike
    // (used to allow row data to be re-used for multiple spikes)
    spike_t originating_spike;

    uint32_t n_bytes_transferred;

    // Row data
    uint32_t *row;

} dma_buffer;

//! \brief get the address of the circular buffer used for buffering received
//! spikes before processing them
//! \return address of circular buffer
circular_buffer get_circular_buffer();

//! \brief set the DMA status
//! \param[in] busy: bool
//! \return None
void set_dma_busy(bool busy);

//! \brief retrieve the DMA status
//! \return bool
bool get_dma_busy();

//! \brief set the number of times spike_processing has to attempt rewiring
//! \return bool: currently, always true
bool do_rewiring(int number_of_rew);


//! exposing this so that other classes can call it
void _setup_synaptic_dma_read();

//! \brief has this core received any spikes since the last batch of rewires?
//! \return bool
bool received_any_spike();

//! \brief flush input buffer
//! \return number of flushed spikes
uint32_t spike_processing_flush_in_buffer();

//! \brief get number of spikes received since last timer event
//! \return uint32_t number of spikes
uint32_t spike_processing_get_and_reset_spikes_this_tick();

//! \brief get number of dmas completed since last timer event
//! \return uint32_t number of DMAs
uint32_t spike_processing_get_and_reset_dmas_this_tick();

//! \brief get number of time pipeline was restarted since last timer event
//! \return uint32_t number of pipeline restarts
uint32_t spike_processing_get_and_reset_pipeline_restarts_this_tick();

//! \brief get time from T1 clock at which spike pipeline completed
//! \return uint32_t pipeline deactivation time
uint32_t spike_processing_get_pipeline_deactivation_time();

#endif // _SPIKE_PROCESSING_H_