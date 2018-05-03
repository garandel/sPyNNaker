#ifndef _POST_EVENTS_INC_V_H_
#define _POST_EVENTS_INV_V_H_
// Standard includes
#include <stdbool.h>
#include <stdint.h>

// Include debug header for log_info etc
#include <debug.h>

//---------------------------------------
// Macros
//---------------------------------------
#define MAX_POST_SYNAPTIC_EVENTS 16

//---------------------------------------
// Structures
//---------------------------------------
typedef struct {
    uint32_t count_minus_one;
    uint32_t times[MAX_POST_SYNAPTIC_EVENTS];
    input_t v_before_last_teacher_pre[MAX_POST_SYNAPTIC_EVENTS];
    post_trace_t traces[MAX_POST_SYNAPTIC_EVENTS];
} post_event_history_t;

typedef struct {
    post_trace_t prev_trace;
    uint32_t prev_time;
    input_t prev_post_synaptic_v;
    const post_trace_t *next_trace;
    const uint32_t *next_time;
    const input_t *next_post_synaptic_v;
    uint32_t num_events;
} post_event_window_t;

//---------------------------------------
// Inline functions
//---------------------------------------
static inline post_event_history_t *post_events_init_buffers(
        uint32_t n_neurons) {
    post_event_history_t *post_event_history =
        (post_event_history_t*) spin1_malloc(
            n_neurons * sizeof(post_event_history_t));
    log_info("size of post_event_history is: %u", sizeof(post_event_history_t) );

    // Check allocations succeeded
    if (post_event_history == NULL) {
        log_error(
            "Unable to allocate global STDP structures - Out of DTCM: Try "
            "reducing the number of neurons per core to fix this problem ");
        return NULL;
    }

    // Loop through neurons
    for (uint32_t n = 0; n < n_neurons; n++) {

        // Add initial placeholder entry to buffer
        post_event_history[n].times[0] = 0;
        post_event_history[n].traces[0] = timing_get_initial_post_trace();
        post_event_history[n].count_minus_one = 0;
        post_event_history[n].v_before_last_teacher_pre[0] = -65.0k;
    }


    //print_event_history(&post_event_history);

    return post_event_history;
}

static inline post_event_window_t post_events_get_window(
        const post_event_history_t *events, uint32_t begin_time) {

    // Start at end event - beyond end of post-event history
    const uint32_t count = events->count_minus_one + 1;
    const uint32_t *end_event_time = events->times + count;
    const post_trace_t *end_event_trace = events->traces + count;
    const uint32_t *event_time = end_event_time;
    post_event_window_t window;
    do {

        // Cache pointer to this event as potential
        // Next event and go back one event
        // **NOTE** next_time can be invalid
        window.next_time = event_time--;
    }

    // Keep looping while event occurred after start
    // Of window and we haven't hit beginning of array
    while (*event_time > begin_time && event_time != events->times);

    // Deference event to use as previous
    window.prev_time = *event_time;

    // Calculate number of events
    window.num_events = (end_event_time - window.next_time);

    // Using num_events, find next and previous traces
    window.next_trace = (end_event_trace - window.num_events);
    window.prev_trace = *(window.next_trace - 1);




    // Return window
    return window;
}

//---------------------------------------
static inline post_event_window_t post_events_get_window_delayed(
        const post_event_history_t *events, uint32_t begin_time,
        uint32_t end_time) {

    // Start at end event - beyond end of post-event history
    const uint32_t count = events->count_minus_one + 1;
    const uint32_t *end_event_time = events->times + count;
    const uint32_t *event_time = end_event_time;
//    const uint32_t *end_post_synaptic_V =

    post_event_window_t window;
    do {
        // Cache pointer to this event as potential
        // Next event and go back one event
        // **NOTE** next_time can be invalid
        window.next_time = event_time--;

        // If this event is still in the future, set it as the end
        if (*event_time > end_time) {
            end_event_time = event_time;
        }
    }

    // Keep looping while event occurred after start
    // Of window and we haven't hit beginning of array
    while (*event_time > begin_time && event_time != events->times);

    // Deference event to use as previous
    window.prev_time = *event_time;

    // Calculate number of events
    window.num_events = (end_event_time - window.next_time);

    // Using num_events, find next and previous traces
    const post_trace_t *end_event_trace = events->traces + count;
    const input_t *end_post_synaptic_V = events->v_before_last_teacher_pre + count;
    window.next_trace = (end_event_trace - window.num_events);
    window.prev_trace = *(window.next_trace - 1);

    window.next_post_synaptic_v = (end_post_synaptic_V - window.num_events);

    // Return window
    return window;
}

//---------------------------------------
static inline post_event_window_t post_events_next(post_event_window_t window) {

    // Update previous time and increment next time
    window.prev_time = *window.next_time++;
    window.prev_trace = *window.next_trace++;
    window.prev_post_synaptic_v = *window.next_post_synaptic_v++;

    // Decrement remaining events
    window.num_events--;
    return window;
}

//---------------------------------------
static inline post_event_window_t post_events_next_delayed(
        post_event_window_t window, uint32_t delayed_time) {

    // Update previous time and increment next time
    window.prev_time = delayed_time;
    window.prev_trace = *window.next_trace++;
    window.prev_post_synaptic_v = *window.next_post_synaptic_v++;

    // Go onto next event
    window.next_time++;

    // Decrement remaining events
    window.num_events--;
    return window;
}

//---------------------------------------
static inline void post_events_add(uint32_t time, post_event_history_t *events,
                                   post_trace_t trace) {

    if (events->count_minus_one < (MAX_POST_SYNAPTIC_EVENTS - 1)) {

        // If there's still space, store time at current end
        // and increment count minus 1
        const uint32_t new_index = ++events->count_minus_one;
        events->times[new_index] = time;
        events->traces[new_index] = trace;
    } else {

        // Otherwise Shuffle down elements
        // **NOTE** 1st element is always an entry at time 0
        for (uint32_t e = 2; e < MAX_POST_SYNAPTIC_EVENTS; e++) {
            events->times[e - 1] = events->times[e];
            events->traces[e - 1] = events->traces[e];
        }

        // Stick new time at end
        events->times[MAX_POST_SYNAPTIC_EVENTS - 1] = time;
        events->traces[MAX_POST_SYNAPTIC_EVENTS - 1] = trace;
    }
}

//---------------------------------------
static inline void post_events_add_inc_v(uint32_t time, post_event_history_t *events,
                                   post_trace_t trace, input_t post_synaptic_v) {

    if (events->count_minus_one < (MAX_POST_SYNAPTIC_EVENTS - 1)) {

        // If there's still space, store time at current end
        // and increment count minus 1
        const uint32_t new_index = ++events->count_minus_one;
        events->times[new_index] = time;
        events->traces[new_index] = trace;
        events->v_before_last_teacher_pre[new_index] = post_synaptic_v;
    } else {

        // Otherwise Shuffle down elements
        // **NOTE** 1st element is always an entry at time 0
        for (uint32_t e = 2; e < MAX_POST_SYNAPTIC_EVENTS; e++) {
            events->times[e - 1] = events->times[e];
            events->traces[e - 1] = events->traces[e];
            events->v_before_last_teacher_pre[e - 1] = events->v_before_last_teacher_pre[e];
        }

        // Stick new time at end
        events->times[MAX_POST_SYNAPTIC_EVENTS - 1] = time;
        events->traces[MAX_POST_SYNAPTIC_EVENTS - 1] = trace;
        events->v_before_last_teacher_pre[MAX_POST_SYNAPTIC_EVENTS - 1] = post_synaptic_v;
    }
}

static inline print_event_history(post_event_history_t *events){
	for (int i = 0; i <= events->count_minus_one; i++){
		log_info("Post Spike Number: %u, Time: %u, Trace: %u, mem_V: %k",
				i,
				events->times[i],
				events->traces[i],
				events->v_before_last_teacher_pre[i]);
	}
}

static inline print_delayed_window_events(post_event_history_t *post_event_history,
		uint32_t begin_time, uint32_t end_time, uint32_t delay_dendritic){

    post_event_window_t post_window = post_events_get_window_delayed(
            post_event_history, begin_time, end_time);

    while (post_window.num_events > 0) {
    	const uint32_t delayed_post_time = *post_window.next_time
    	                                           + delay_dendritic;
    	log_info("Spike: %u, Time: %u, Trace: %u, Mem_V: %k",
    			post_window.num_events, delayed_post_time,
				*post_window.next_trace, *post_window.next_post_synaptic_v);

    	post_window = post_events_next_delayed(post_window, delayed_post_time);
    }
}

#endif  // _POST_EVENTS_H_
