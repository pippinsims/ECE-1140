"""
test_wayside_controller.py
==========================
Unit tests for wayside_controller.py logic functions.
Tests cover:
  - build_switch_map
  - authority_reach
  - compute_signal_blocks
  - compute_wayside_outputs (signals, switches, crossings, reach)
  - Unit conversion helpers (kmh_to_mph, mph_to_kmh, km_to_miles, miles_to_km)
  - WAYSIDE_CONFIGS / BLOCK_TO_WAYSIDE / LINE_WAYSIDES data integrity
  - _slice, _slice_switches, _slice_crossings helpers

No CTC, no UI, no tkinter display required.
Run with:  python -m pytest test_wayside_controller.py -v
"""

import unittest
from wayside_controller import (
    build_switch_map,
    authority_reach,
    compute_signal_blocks,
    compute_wayside_outputs,
    kmh_to_mph, mph_to_kmh,
    km_to_miles, miles_to_km,
    WAYSIDE_CONFIGS,
    BLOCK_TO_WAYSIDE,
    LINE_WAYSIDES,
    GREEN_BLOCK_LENGTHS, GREEN_SWITCHES, GREEN_CROSSINGS, GREEN_STATIONS,
    RED_BLOCK_LENGTHS,   RED_SWITCHES,   RED_CROSSINGS,   RED_STATIONS,
    _slice, _slice_switches, _slice_crossings,
    WG1_BLOCKS, WG2_BLOCKS, WR1_BLOCKS, WR2_BLOCKS,
)


# =============================================================================
# HELPERS  —  reusable minimal track fixtures
# =============================================================================

def _empty_state(block_lengths):
    """Return a block_state where every block is unoccupied with zero speed/authority."""
    return {b: {"occupied": False, "cmd_speed": 0.0, "authority": 0.0}
            for b in block_lengths}

def _occupy(block_state, blk, cmd_speed=50.0, authority=1.0):
    """Mark one block as occupied in a copy of block_state."""
    s = {b: dict(v) for b, v in block_state.items()}
    s[blk] = {"occupied": True, "cmd_speed": cmd_speed, "authority": authority}
    return s

# Minimal straight track: 5 blocks, each 100 m, no switches, no crossings
STRAIGHT_LENGTHS  = {1: 100, 2: 100, 3: 100, 4: 100, 5: 100}
STRAIGHT_SWITCHES = {}
STRAIGHT_CROSSINGS = []

# Minimal track with one switch at block 3 branching to 4 (normal) or 10 (reverse)
BRANCH_LENGTHS  = {1:100, 2:100, 3:100, 4:100, 5:100, 10:100, 11:100}
BRANCH_SWITCHES = {
    "SW3": {"host": 3, "normal": (4, "3->4"), "reverse": (10, "3->10"),
            "description": "Test branch switch"}
}
BRANCH_CROSSINGS = []


# =============================================================================
# 1.  build_switch_map
# =============================================================================

class TestBuildSwitchMap(unittest.TestCase):

    def test_empty_switches_returns_empty_map(self):
        # With no switches defined the map should be empty
        result = build_switch_map({})
        self.assertEqual(result, {})

    def test_single_switch_maps_host_to_both_branches(self):
        # Host block 3 should map to both branch targets [4, 10]
        sw = {"SW3": {"host": 3, "normal": (4, "3->4"), "reverse": (10, "3->10"),
                      "description": ""}}
        result = build_switch_map(sw)
        self.assertIn(3, result)
        self.assertIn(4,  result[3])
        self.assertIn(10, result[3])

    def test_yard_switch_with_reverse_zero_excluded(self):
        # A yard switch whose reverse target is block 0 should not include 0
        sw = {"SW9": {"host": 9, "normal": (10, "9->10"), "reverse": (0, "Yard"),
                      "description": ""}}
        result = build_switch_map(sw)
        self.assertNotIn(0, result[9])
        self.assertIn(10, result[9])

    def test_multiple_switches_all_present(self):
        # All switch host blocks should appear as keys in the map
        result = build_switch_map(GREEN_SWITCHES)
        for sw in GREEN_SWITCHES.values():
            self.assertIn(sw["host"], result)

    def test_green_sw12_branches_correct(self):
        # SW12 connects host 12 to normal=13 and reverse=1
        result = build_switch_map(GREEN_SWITCHES)
        self.assertIn(13, result[12])
        self.assertIn(1,  result[12])

    def test_red_sw27_branches_correct(self):
        # SW27 connects host 27 to normal=28 and reverse=76
        result = build_switch_map(RED_SWITCHES)
        self.assertIn(28, result[27])
        self.assertIn(76, result[27])


# =============================================================================
# 2.  authority_reach
# =============================================================================

class TestAuthorityReach(unittest.TestCase):

    def test_zero_authority_returns_empty(self):
        # With 0 km authority nothing should be reachable
        sw_map = build_switch_map(STRAIGHT_SWITCHES)
        result = authority_reach(1, 0.0, STRAIGHT_LENGTHS, sw_map)
        self.assertEqual(result, set())

    def test_negative_authority_returns_empty(self):
        # Negative authority should also return empty
        sw_map = build_switch_map(STRAIGHT_SWITCHES)
        result = authority_reach(1, -1.0, STRAIGHT_LENGTHS, sw_map)
        self.assertEqual(result, set())

    def test_exact_one_block_authority(self):
        # 0.1 km = 100 m authority exactly covers block 1 (100 m)
        # block 1 is included (train begins to enter it), block 2 is not
        sw_map = build_switch_map(STRAIGHT_SWITCHES)
        result = authority_reach(1, 0.1, STRAIGHT_LENGTHS, sw_map)
        self.assertIn(1, result)
        self.assertNotIn(2, result)

    def test_authority_covers_multiple_sequential_blocks(self):
        # 0.25 km = 250 m authority covers blocks 1 and 2 (100 m each) and begins 3
        sw_map = build_switch_map(STRAIGHT_SWITCHES)
        result = authority_reach(1, 0.25, STRAIGHT_LENGTHS, sw_map)
        self.assertIn(1, result)
        self.assertIn(2, result)
        self.assertIn(3, result)

    def test_authority_does_not_exceed_limit(self):
        # 0.15 km = 150 m covers block 1 fully and begins block 2; block 3 should not be reached
        sw_map = build_switch_map(STRAIGHT_SWITCHES)
        result = authority_reach(1, 0.15, STRAIGHT_LENGTHS, sw_map)
        self.assertIn(1,    result)
        self.assertIn(2,    result)
        self.assertNotIn(3, result)

    def test_authority_explores_both_switch_branches(self):
        # At a switch both normal and reverse branches should be in reach
        sw_map = build_switch_map(BRANCH_SWITCHES)
        # Start at block 3 (the switch host), authority covers 2 blocks beyond
        result = authority_reach(3, 0.25, BRANCH_LENGTHS, sw_map)
        self.assertIn(4,  result)   # normal branch
        self.assertIn(10, result)   # reverse branch

    def test_invalid_block_zero_skipped(self):
        # Yard switch reverse=0 should never appear in reach
        sw = {"SW9": {"host": 9, "normal": (10, ""), "reverse": (0, ""),
                      "description": ""}}
        lengths = {b: 50 for b in range(1, 15)}
        sw_map  = build_switch_map(sw)
        result  = authority_reach(9, 1.0, lengths, sw_map)
        self.assertNotIn(0, result)

    def test_large_authority_reaches_far(self):
        # 10 km authority on a 5-block 100 m track should reach all 5 blocks
        sw_map = build_switch_map(STRAIGHT_SWITCHES)
        result = authority_reach(1, 10.0, STRAIGHT_LENGTHS, sw_map)
        for b in [1, 2, 3, 4, 5]:
            self.assertIn(b, result)

    def test_no_revisit_cycles(self):
        # A looping switch graph should not cause infinite BFS
        # Block 1 -> 2 -> 3 -> 1 (artificial loop)
        loop_lengths = {1: 100, 2: 100, 3: 100}
        loop_sw_map  = {1: [2], 2: [3], 3: [1]}
        result = authority_reach(1, 10.0, loop_lengths, loop_sw_map)
        # Should terminate and include reachable blocks without hanging
        self.assertIsInstance(result, set)


# =============================================================================
# 3.  compute_signal_blocks
# =============================================================================

class TestComputeSignalBlocks(unittest.TestCase):

    def test_switch_host_gets_signal(self):
        # The host block of every switch should be in signal_blocks
        result = compute_signal_blocks(set(), BRANCH_SWITCHES, BRANCH_LENGTHS)
        self.assertIn(3, result)   # SW3 host

    def test_switch_normal_branch_gets_signal(self):
        # The normal branch block of a switch should get a signal
        result = compute_signal_blocks(set(), BRANCH_SWITCHES, BRANCH_LENGTHS)
        self.assertIn(4, result)   # SW3 normal branch

    def test_switch_reverse_branch_gets_signal(self):
        # The reverse branch block of a switch should get a signal
        result = compute_signal_blocks(set(), BRANCH_SWITCHES, BRANCH_LENGTHS)
        self.assertIn(10, result)  # SW3 reverse branch

    def test_block_before_station_gets_signal(self):
        # One block before each station should be in signal_blocks
        stations = {3}
        result   = compute_signal_blocks(stations, {}, STRAIGHT_LENGTHS)
        self.assertIn(2, result)

    def test_block_after_station_gets_signal(self):
        # One block after each station should be in signal_blocks
        stations = {3}
        result   = compute_signal_blocks(stations, {}, STRAIGHT_LENGTHS)
        self.assertIn(4, result)

    def test_station_itself_not_included(self):
        # The station block itself does NOT get a signal (only its neighbours do)
        stations = {3}
        result   = compute_signal_blocks(stations, {}, STRAIGHT_LENGTHS)
        self.assertNotIn(3, result)

    def test_result_only_contains_existing_blocks(self):
        # Out-of-range blocks should never appear in signal_blocks
        stations = {99}   # block 99 not in STRAIGHT_LENGTHS
        result   = compute_signal_blocks(stations, {}, STRAIGHT_LENGTHS)
        for b in result:
            self.assertIn(b, STRAIGHT_LENGTHS)

    def test_no_stations_no_switches_empty(self):
        # With no stations and no switches there should be no signal blocks
        result = compute_signal_blocks(set(), {}, STRAIGHT_LENGTHS)
        self.assertEqual(result, set())

    def test_green_wg1_signal_blocks_contains_sw12_host(self):
        # SW12 host (block 12) should be in WG1 signal blocks
        from wayside_controller import _WG1_SB
        self.assertIn(12, _WG1_SB)

    def test_red_wr1_signal_blocks_contains_station_neighbours(self):
        # Station 7 on Red line: blocks 6 and 8 should be in WR1 signal blocks
        from wayside_controller import _WR1_SB
        self.assertIn(6, _WR1_SB)
        self.assertIn(8, _WR1_SB)


# =============================================================================
# 4.  compute_wayside_outputs — SIGNALS
# =============================================================================

class TestSignalLogic(unittest.TestCase):

    def _run(self, block_state, lengths=None, switches=None,
             crossings=None, signal_blocks=None):
        """Convenience wrapper to call compute_wayside_outputs."""
        return compute_wayside_outputs(
            block_state,
            lengths    or STRAIGHT_LENGTHS,
            switches   or STRAIGHT_SWITCHES,
            crossings  or STRAIGHT_CROSSINGS,
            signal_blocks,
        )

    def test_all_unoccupied_all_green(self):
        # With no trains every signal block should be green
        state  = _empty_state(STRAIGHT_LENGTHS)
        result = self._run(state)
        for sig in result["signals"].values():
            self.assertEqual(sig, "green")

    def test_none_returned_for_non_signal_block(self):
        # Blocks not in signal_blocks must return None
        state  = _empty_state(STRAIGHT_LENGTHS)
        result = self._run(state, signal_blocks={1, 2})   # only 1 and 2 have signals
        self.assertIsNone(result["signals"][3])
        self.assertIsNone(result["signals"][4])
        self.assertIsNone(result["signals"][5])

    def test_signal_blocks_get_colour_not_none(self):
        # Blocks in signal_blocks must never return None
        state  = _empty_state(STRAIGHT_LENGTHS)
        result = self._run(state, signal_blocks={1, 2})
        self.assertIsNotNone(result["signals"][1])
        self.assertIsNotNone(result["signals"][2])

    def test_unoccupied_block_red_when_next_occupied(self):
        # An unoccupied block whose immediate next block is occupied → red
        state  = _occupy(_empty_state(STRAIGHT_LENGTHS), 3)
        result = self._run(state)
        self.assertEqual(result["signals"][2], "red")

    def test_unoccupied_block_yellow_when_two_ahead_occupied(self):
        # An unoccupied block with second-next block occupied → yellow
        state  = _occupy(_empty_state(STRAIGHT_LENGTHS), 4)
        result = self._run(state)
        self.assertEqual(result["signals"][2], "yellow")

    def test_unoccupied_block_green_when_two_clear(self):
        # An unoccupied block with two clear blocks ahead → green
        state  = _empty_state(STRAIGHT_LENGTHS)
        result = self._run(state)
        self.assertEqual(result["signals"][1], "green")

    def test_occupied_block_red_when_next_also_occupied(self):
        # Train on block 3 with another train on block 4 (immediately ahead) → red
        # Signal logic for occupied block checks next1 = blk+1, so the blocking
        # train must be ahead of (not behind) the occupied block being tested
        state  = _occupy(_empty_state(STRAIGHT_LENGTHS), 4)   # train ahead
        state  = _occupy(state, 3, cmd_speed=50, authority=1.0)  # train under test
        result = self._run(state)
        self.assertEqual(result["signals"][3], "red")

    def test_occupied_block_red_when_zero_authority(self):
        # An occupied block with authority=0 → red regardless of clear track
        state  = _occupy(_empty_state(STRAIGHT_LENGTHS), 2, cmd_speed=50, authority=0.0)
        result = self._run(state)
        self.assertEqual(result["signals"][2], "red")

    def test_occupied_block_red_when_zero_speed(self):
        # An occupied block with cmd_speed=0 → red
        state  = _occupy(_empty_state(STRAIGHT_LENGTHS), 2, cmd_speed=0.0, authority=1.0)
        result = self._run(state)
        self.assertEqual(result["signals"][2], "red")

    def test_occupied_block_green_with_sufficient_authority(self):
        # Train with enough authority to clear 2 blocks ahead → green
        # Blocks 3 and 4 are each 100 m; authority 0.25 km = 250 m clears both
        state  = _occupy(_empty_state(STRAIGHT_LENGTHS), 2, cmd_speed=50, authority=0.25)
        result = self._run(state)
        self.assertEqual(result["signals"][2], "green")

    def test_occupied_block_yellow_when_authority_clears_only_one(self):
        # Authority exactly 0.1 km = 100 m — clears block 3 but not block 4 → yellow
        state  = _occupy(_empty_state(STRAIGHT_LENGTHS), 2, cmd_speed=50, authority=0.11)
        result = self._run(state)
        self.assertEqual(result["signals"][2], "yellow")

    def test_occupied_block_red_when_authority_too_short_for_next(self):
        # Authority 0.05 km = 50 m — cannot clear next 100 m block → red
        state  = _occupy(_empty_state(STRAIGHT_LENGTHS), 2, cmd_speed=50, authority=0.05)
        result = self._run(state)
        self.assertEqual(result["signals"][2], "red")

    def test_all_signal_keys_present_in_output(self):
        # compute_wayside_outputs must return a signal entry for every block
        state  = _empty_state(STRAIGHT_LENGTHS)
        result = self._run(state)
        for b in STRAIGHT_LENGTHS:
            self.assertIn(b, result["signals"])

    def test_signal_values_are_valid(self):
        # Every signal value must be green/yellow/red/None — nothing else
        state  = _occupy(_empty_state(STRAIGHT_LENGTHS), 3)
        result = self._run(state)
        valid  = {"green", "yellow", "red", None}
        for sig in result["signals"].values():
            self.assertIn(sig, valid)


# =============================================================================
# 5.  compute_wayside_outputs — SWITCHES
# =============================================================================

class TestSwitchLogic(unittest.TestCase):

    def _run(self, block_state):
        return compute_wayside_outputs(
            block_state, BRANCH_LENGTHS, BRANCH_SWITCHES, BRANCH_CROSSINGS)

    def test_switch_defaults_to_normal_when_no_trains(self):
        # With no trains anywhere the switch should sit at normal
        state  = _empty_state(BRANCH_LENGTHS)
        result = self._run(state)
        self.assertEqual(result["switches"]["SW3"], "normal")

    def test_switch_normal_when_only_normal_branch_occupied(self):
        # Train only on normal branch → switch stays normal (no merging needed)
        state  = _occupy(_empty_state(BRANCH_LENGTHS), 4)
        result = self._run(state)
        self.assertEqual(result["switches"]["SW3"], "normal")

    def test_switch_reverse_when_only_reverse_branch_occupied(self):
        # Train on reverse branch and not on normal branch → switch goes reverse
        state  = _occupy(_empty_state(BRANCH_LENGTHS), 10)
        result = self._run(state)
        self.assertEqual(result["switches"]["SW3"], "reverse")

    def test_switch_normal_when_both_branches_occupied(self):
        # Train on both branches → normal wins (cannot serve both, default to normal)
        state  = _occupy(_empty_state(BRANCH_LENGTHS), 4)
        state  = _occupy(state, 10)
        result = self._run(state)
        self.assertEqual(result["switches"]["SW3"], "normal")

    def test_switch_safety_lock_when_host_occupied(self):
        # Train on the host block itself → switch locked to normal (safety rule)
        state  = _occupy(_empty_state(BRANCH_LENGTHS), 3)
        result = self._run(state)
        self.assertEqual(result["switches"]["SW3"], "normal")

    def test_switch_safety_lock_overrides_reverse_branch(self):
        # Even with a train on the reverse branch, if host is occupied → normal
        state  = _occupy(_empty_state(BRANCH_LENGTHS), 3)   # host
        state  = _occupy(state, 10)                          # reverse branch
        result = self._run(state)
        self.assertEqual(result["switches"]["SW3"], "normal")

    def test_all_switch_keys_present_in_output(self):
        # Every switch in switches_def must appear in the output
        state  = _empty_state(BRANCH_LENGTHS)
        result = self._run(state)
        self.assertIn("SW3", result["switches"])

    def test_switch_values_are_valid(self):
        # Switch values must be exactly "normal" or "reverse"
        state  = _occupy(_empty_state(BRANCH_LENGTHS), 10)
        result = self._run(state)
        for pos in result["switches"].values():
            self.assertIn(pos, {"normal", "reverse"})

    def test_green_sw12_defaults_normal_no_trains(self):
        # SW12 on full Green line WG1 should default to normal with no trains
        lengths   = _slice(GREEN_BLOCK_LENGTHS, WG1_BLOCKS)
        switches  = _slice_switches(GREEN_SWITCHES, WG1_BLOCKS)
        crossings = _slice_crossings(GREEN_CROSSINGS, WG1_BLOCKS)
        state     = _empty_state(lengths)
        result    = compute_wayside_outputs(state, lengths, switches, crossings)
        self.assertEqual(result["switches"]["SW12"], "normal")

    def test_red_sw27_reverse_when_block_76_occupied(self):
        # SW27 on Red WR1: block 76 is the reverse branch; occupying it → reverse
        # NOTE: SW27 reverse=(76,...) but block 76 is in WR2 range — SW27 host=27 is in WR1
        # We test with a custom setup matching the WR1 slice
        lengths   = _slice(RED_BLOCK_LENGTHS, WR1_BLOCKS)
        switches  = _slice_switches(RED_SWITCHES, WR1_BLOCKS)
        crossings = _slice_crossings(RED_CROSSINGS, WR1_BLOCKS)
        # Add block 76 to lengths so it can be occupied
        lengths[76] = RED_BLOCK_LENGTHS[76]
        state     = _empty_state(lengths)
        state[76] = {"occupied": True, "cmd_speed": 0.0, "authority": 0.0}
        result    = compute_wayside_outputs(state, lengths, switches, crossings)
        self.assertEqual(result["switches"]["SW27"], "reverse")


# =============================================================================
# 6.  compute_wayside_outputs — CROSSINGS
# =============================================================================

class TestCrossingLogic(unittest.TestCase):

    # Simple 5-block track with a crossing at block 3
    CX_LENGTHS   = {1:100, 2:100, 3:100, 4:100, 5:100}
    CX_SWITCHES  = {}
    CX_CROSSINGS = [3]

    def _run(self, block_state):
        return compute_wayside_outputs(
            block_state, self.CX_LENGTHS, self.CX_SWITCHES, self.CX_CROSSINGS)

    def test_crossing_inactive_when_no_trains(self):
        # No trains anywhere → crossing should be inactive
        state  = _empty_state(self.CX_LENGTHS)
        result = self._run(state)
        self.assertEqual(result["crossings"][3], "inactive")

    def test_crossing_active_when_train_on_crossing_block(self):
        # Train on the crossing block itself → active
        state  = _occupy(_empty_state(self.CX_LENGTHS), 3)
        result = self._run(state)
        self.assertEqual(result["crossings"][3], "active")

    def test_crossing_active_when_train_approaching_with_authority(self):
        # Train one block before the crossing with enough authority to reach it → active
        # Block 2 is one before crossing at 3; authority 0.15 km = 150 m reaches block 3
        state  = _occupy(_empty_state(self.CX_LENGTHS), 2, cmd_speed=50, authority=0.15)
        result = self._run(state)
        self.assertEqual(result["crossings"][3], "active")

    def test_crossing_inactive_when_train_approaching_no_authority(self):
        # Train one block before crossing but with zero authority → inactive
        state  = _occupy(_empty_state(self.CX_LENGTHS), 2, cmd_speed=50, authority=0.0)
        result = self._run(state)
        self.assertEqual(result["crossings"][3], "inactive")

    def test_crossing_inactive_when_train_far_away(self):
        # Train far from crossing with insufficient authority to reach it → inactive
        state  = _occupy(_empty_state(self.CX_LENGTHS), 1, cmd_speed=50, authority=0.05)
        result = self._run(state)
        self.assertEqual(result["crossings"][3], "inactive")

    def test_crossing_keys_in_output(self):
        # The crossing block number must appear as a key in the output
        state  = _empty_state(self.CX_LENGTHS)
        result = self._run(state)
        self.assertIn(3, result["crossings"])

    def test_crossing_values_are_valid(self):
        # Crossing values must be exactly "active" or "inactive"
        state  = _occupy(_empty_state(self.CX_LENGTHS), 3)
        result = self._run(state)
        for val in result["crossings"].values():
            self.assertIn(val, {"active", "inactive"})

    def test_green_crossing_block_19_inactive_no_trains(self):
        # Green line crossing at block 19 — inactive with no trains
        lengths   = _slice(GREEN_BLOCK_LENGTHS, WG1_BLOCKS)
        switches  = _slice_switches(GREEN_SWITCHES, WG1_BLOCKS)
        crossings = _slice_crossings(GREEN_CROSSINGS, WG1_BLOCKS)
        state     = _empty_state(lengths)
        result    = compute_wayside_outputs(state, lengths, switches, crossings)
        self.assertEqual(result["crossings"][19], "inactive")

    def test_green_crossing_block_19_active_when_occupied(self):
        # Green line crossing at block 19 — active when that block is occupied
        lengths   = _slice(GREEN_BLOCK_LENGTHS, WG1_BLOCKS)
        switches  = _slice_switches(GREEN_SWITCHES, WG1_BLOCKS)
        crossings = _slice_crossings(GREEN_CROSSINGS, WG1_BLOCKS)
        state     = _occupy(_empty_state(lengths), 19)
        result    = compute_wayside_outputs(state, lengths, switches, crossings)
        self.assertEqual(result["crossings"][19], "active")


# =============================================================================
# 7.  compute_wayside_outputs — REACH
# =============================================================================

class TestReachOutput(unittest.TestCase):

    def test_no_trains_reach_is_empty(self):
        # With no occupied blocks the reach dict should be empty
        state  = _empty_state(STRAIGHT_LENGTHS)
        result = compute_wayside_outputs(
            state, STRAIGHT_LENGTHS, STRAIGHT_SWITCHES, STRAIGHT_CROSSINGS)
        self.assertEqual(result["reach"], {})

    def test_occupied_block_generates_reach_entry(self):
        # An occupied block should produce a reach entry keyed by that block number
        state  = _occupy(_empty_state(STRAIGHT_LENGTHS), 2, authority=0.2)
        result = compute_wayside_outputs(
            state, STRAIGHT_LENGTHS, STRAIGHT_SWITCHES, STRAIGHT_CROSSINGS)
        self.assertIn(2, result["reach"])

    def test_reach_starts_from_block_ahead(self):
        # Reach is computed from blk+1 onward, so the occupied block itself is not in reach
        state  = _occupy(_empty_state(STRAIGHT_LENGTHS), 2, authority=0.2)
        result = compute_wayside_outputs(
            state, STRAIGHT_LENGTHS, STRAIGHT_SWITCHES, STRAIGHT_CROSSINGS)
        self.assertNotIn(2, result["reach"][2])   # train's own block not in its reach

    def test_reach_contains_blocks_within_authority(self):
        # 0.2 km = 200 m from block 3 onward — should reach blocks 3 and 4
        state  = _occupy(_empty_state(STRAIGHT_LENGTHS), 2, authority=0.2)
        result = compute_wayside_outputs(
            state, STRAIGHT_LENGTHS, STRAIGHT_SWITCHES, STRAIGHT_CROSSINGS)
        self.assertIn(3, result["reach"][2])
        self.assertIn(4, result["reach"][2])

    def test_reach_does_not_contain_blocks_beyond_authority(self):
        # 0.11 km = 110 m from block 3; block 3 = 100 m, block 4 should not be fully in reach
        state  = _occupy(_empty_state(STRAIGHT_LENGTHS), 2, authority=0.11)
        result = compute_wayside_outputs(
            state, STRAIGHT_LENGTHS, STRAIGHT_SWITCHES, STRAIGHT_CROSSINGS)
        self.assertNotIn(5, result["reach"][2])

    def test_two_trains_two_reach_entries(self):
        # Two occupied blocks should produce two independent reach entries
        state  = _occupy(_empty_state(STRAIGHT_LENGTHS), 1, authority=0.15)
        state  = _occupy(state, 4, authority=0.15)
        result = compute_wayside_outputs(
            state, STRAIGHT_LENGTHS, STRAIGHT_SWITCHES, STRAIGHT_CROSSINGS)
        self.assertIn(1, result["reach"])
        self.assertIn(4, result["reach"])


# =============================================================================
# 8.  compute_wayside_outputs — OUTPUT STRUCTURE
# =============================================================================

class TestOutputStructure(unittest.TestCase):

    def test_output_has_all_four_keys(self):
        # The return dict must always contain switches, signals, crossings, reach
        state  = _empty_state(STRAIGHT_LENGTHS)
        result = compute_wayside_outputs(
            state, STRAIGHT_LENGTHS, STRAIGHT_SWITCHES, STRAIGHT_CROSSINGS)
        for key in ("switches", "signals", "crossings", "reach"):
            self.assertIn(key, result)

    def test_no_crossings_list_returns_empty_crossings(self):
        # Empty crossings list → empty crossings dict in output
        state  = _empty_state(STRAIGHT_LENGTHS)
        result = compute_wayside_outputs(
            state, STRAIGHT_LENGTHS, STRAIGHT_SWITCHES, [])
        self.assertEqual(result["crossings"], {})

    def test_no_switches_returns_empty_switches(self):
        # Empty switches_def → empty switches dict in output
        state  = _empty_state(STRAIGHT_LENGTHS)
        result = compute_wayside_outputs(
            state, STRAIGHT_LENGTHS, {}, STRAIGHT_CROSSINGS)
        self.assertEqual(result["switches"], {})

    def test_empty_block_state_no_crash(self):
        # Empty block_state should not raise an exception
        result = compute_wayside_outputs(
            {}, STRAIGHT_LENGTHS, STRAIGHT_SWITCHES, STRAIGHT_CROSSINGS)
        self.assertIsInstance(result, dict)

    def test_signals_cover_all_blocks_in_block_lengths(self):
        # Every block in block_lengths must have a signals entry
        state  = _empty_state(STRAIGHT_LENGTHS)
        result = compute_wayside_outputs(
            state, STRAIGHT_LENGTHS, STRAIGHT_SWITCHES, STRAIGHT_CROSSINGS)
        for b in STRAIGHT_LENGTHS:
            self.assertIn(b, result["signals"])


# =============================================================================
# 9.  UNIT CONVERSIONS
# =============================================================================

class TestUnitConversions(unittest.TestCase):

    def test_kmh_to_mph_known_value(self):
        # 100 km/h ≈ 62.1371 mph
        self.assertAlmostEqual(kmh_to_mph(100), 62.1371, places=3)

    def test_mph_to_kmh_known_value(self):
        # 60 mph ≈ 96.5606 km/h
        self.assertAlmostEqual(mph_to_kmh(60), 96.5606, places=2)

    def test_km_to_miles_known_value(self):
        # 1 km ≈ 0.621371 miles
        self.assertAlmostEqual(km_to_miles(1), 0.621371, places=5)

    def test_miles_to_km_known_value(self):
        # 1 mile ≈ 1.60934 km
        self.assertAlmostEqual(miles_to_km(1), 1.60934, places=3)

    def test_kmh_mph_round_trip(self):
        # Converting km/h → mph → km/h should recover the original value
        original = 55.0
        self.assertAlmostEqual(mph_to_kmh(kmh_to_mph(original)), original, places=10)

    def test_km_miles_round_trip(self):
        # Converting km → miles → km should recover the original value
        original = 2.5
        self.assertAlmostEqual(miles_to_km(km_to_miles(original)), original, places=10)

    def test_zero_input_returns_zero(self):
        # All conversions of 0 should return 0
        self.assertEqual(kmh_to_mph(0), 0)
        self.assertEqual(mph_to_kmh(0), 0)
        self.assertEqual(km_to_miles(0), 0)
        self.assertEqual(miles_to_km(0), 0)

    def test_conversions_are_positive_for_positive_input(self):
        # Positive input must produce positive output
        self.assertGreater(kmh_to_mph(10),  0)
        self.assertGreater(mph_to_kmh(10),  0)
        self.assertGreater(km_to_miles(10), 0)
        self.assertGreater(miles_to_km(10), 0)


# =============================================================================
# 10.  WAYSIDE_CONFIGS / BLOCK_TO_WAYSIDE / LINE_WAYSIDES DATA INTEGRITY
# =============================================================================

class TestConfigDataIntegrity(unittest.TestCase):

    def test_all_four_waysides_present(self):
        # WAYSIDE_CONFIGS must contain exactly WG1, WG2, WR1, WR2
        for wid in ("WG1", "WG2", "WR1", "WR2"):
            self.assertIn(wid, WAYSIDE_CONFIGS)

    def test_no_blue_waysides_present(self):
        # Blue line was removed; WB1 and WB2 must not be in WAYSIDE_CONFIGS
        self.assertNotIn("WB1", WAYSIDE_CONFIGS)
        self.assertNotIn("WB2", WAYSIDE_CONFIGS)

    def test_each_wayside_has_required_keys(self):
        # Every wayside config must have all required data keys
        required = {"line", "label", "color", "blocks", "block_lengths",
                    "speed_limits", "switches", "crossings", "signal_blocks"}
        for wid, cfg in WAYSIDE_CONFIGS.items():
            for key in required:
                self.assertIn(key, cfg, msg=f"{wid} missing key '{key}'")

    def test_wg1_block_range_correct(self):
        # WG1 should own blocks 1–75
        self.assertEqual(WAYSIDE_CONFIGS["WG1"]["blocks"], set(range(1, 76)))

    def test_wg2_block_range_correct(self):
        # WG2 should own blocks 76–150
        self.assertEqual(WAYSIDE_CONFIGS["WG2"]["blocks"], set(range(76, 151)))

    def test_wr1_block_range_correct(self):
        # WR1 should own blocks 1–38
        self.assertEqual(WAYSIDE_CONFIGS["WR1"]["blocks"], set(range(1, 39)))

    def test_wr2_block_range_correct(self):
        # WR2 should own blocks 39–76
        self.assertEqual(WAYSIDE_CONFIGS["WR2"]["blocks"], set(range(39, 77)))

    def test_green_waysides_blocks_do_not_overlap(self):
        # WG1 and WG2 blocks must be disjoint
        wg1 = WAYSIDE_CONFIGS["WG1"]["blocks"]
        wg2 = WAYSIDE_CONFIGS["WG2"]["blocks"]
        self.assertEqual(wg1 & wg2, set())

    def test_red_waysides_blocks_do_not_overlap(self):
        # WR1 and WR2 blocks must be disjoint
        wr1 = WAYSIDE_CONFIGS["WR1"]["blocks"]
        wr2 = WAYSIDE_CONFIGS["WR2"]["blocks"]
        self.assertEqual(wr1 & wr2, set())

    def test_green_waysides_together_cover_all_150_blocks(self):
        # WG1 + WG2 must together account for all 150 Green line blocks
        all_green = WAYSIDE_CONFIGS["WG1"]["blocks"] | WAYSIDE_CONFIGS["WG2"]["blocks"]
        self.assertEqual(all_green, set(range(1, 151)))

    def test_red_waysides_together_cover_all_76_blocks(self):
        # WR1 + WR2 must together account for all 76 Red line blocks
        all_red = WAYSIDE_CONFIGS["WR1"]["blocks"] | WAYSIDE_CONFIGS["WR2"]["blocks"]
        self.assertEqual(all_red, set(range(1, 77)))

    def test_each_wayside_line_label_is_correct(self):
        # WG1/WG2 must be labelled Green; WR1/WR2 must be labelled Red
        self.assertEqual(WAYSIDE_CONFIGS["WG1"]["line"], "Green")
        self.assertEqual(WAYSIDE_CONFIGS["WG2"]["line"], "Green")
        self.assertEqual(WAYSIDE_CONFIGS["WR1"]["line"], "Red")
        self.assertEqual(WAYSIDE_CONFIGS["WR2"]["line"], "Red")

    def test_block_to_wayside_covers_all_green_blocks(self):
        # Every Green block 1–150 must be routable via BLOCK_TO_WAYSIDE
        for b in range(1, 151):
            self.assertIn(("Green", b), BLOCK_TO_WAYSIDE)

    def test_block_to_wayside_covers_all_red_blocks(self):
        # Every Red block 1–76 must be routable via BLOCK_TO_WAYSIDE
        for b in range(1, 77):
            self.assertIn(("Red", b), BLOCK_TO_WAYSIDE)

    def test_block_to_wayside_routes_correctly(self):
        # Spot-check: Green block 50 → WG1, Green block 100 → WG2
        # Red block 20 → WR1, Red block 60 → WR2
        self.assertEqual(BLOCK_TO_WAYSIDE[("Green", 50)],  "WG1")
        self.assertEqual(BLOCK_TO_WAYSIDE[("Green", 100)], "WG2")
        self.assertEqual(BLOCK_TO_WAYSIDE[("Red",   20)],  "WR1")
        self.assertEqual(BLOCK_TO_WAYSIDE[("Red",   60)],  "WR2")

    def test_blue_blocks_not_in_block_to_wayside(self):
        # Blue line was removed; no Blue blocks should be routable
        for b in range(1, 16):
            self.assertNotIn(("Blue", b), BLOCK_TO_WAYSIDE)

    def test_line_waysides_has_green_and_red_only(self):
        # LINE_WAYSIDES should only have Green and Red keys
        self.assertIn("Green", LINE_WAYSIDES)
        self.assertIn("Red",   LINE_WAYSIDES)
        self.assertNotIn("Blue", LINE_WAYSIDES)

    def test_line_waysides_green_order(self):
        # Green waysides should be ordered WG1 then WG2
        self.assertEqual(LINE_WAYSIDES["Green"], ["WG1", "WG2"])

    def test_line_waysides_red_order(self):
        # Red waysides should be ordered WR1 then WR2
        self.assertEqual(LINE_WAYSIDES["Red"], ["WR1", "WR2"])

    def test_switches_assigned_to_correct_wayside(self):
        # SW12 host=12 is in WG1 (blocks 1-75); SW76 host=76 is in WG2 (blocks 76-150)
        self.assertIn("SW12", WAYSIDE_CONFIGS["WG1"]["switches"])
        self.assertNotIn("SW12", WAYSIDE_CONFIGS["WG2"]["switches"])
        self.assertIn("SW76", WAYSIDE_CONFIGS["WG2"]["switches"])
        self.assertNotIn("SW76", WAYSIDE_CONFIGS["WG1"]["switches"])

    def test_crossings_assigned_to_correct_wayside(self):
        # Green crossing 19 is in WG1 (blocks 1-75)
        # Green crossing 108 is in WG2 (blocks 76-150)
        self.assertIn(19,  WAYSIDE_CONFIGS["WG1"]["crossings"])
        self.assertNotIn(19,  WAYSIDE_CONFIGS["WG2"]["crossings"])
        self.assertIn(108, WAYSIDE_CONFIGS["WG2"]["crossings"])
        self.assertNotIn(108, WAYSIDE_CONFIGS["WG1"]["crossings"])


# =============================================================================
# 11.  _slice / _slice_switches / _slice_crossings HELPERS
# =============================================================================

class TestSliceHelpers(unittest.TestCase):

    def test_slice_keeps_only_blocks_in_range(self):
        # _slice should return only keys that are in the given range
        full = {1:100, 2:100, 3:100, 4:100, 5:100}
        result = _slice(full, range(2, 5))
        self.assertEqual(set(result.keys()), {2, 3, 4})

    def test_slice_preserves_values(self):
        # _slice should not alter the values
        full = {1:100, 2:200, 3:300}
        result = _slice(full, range(1, 3))
        self.assertEqual(result[1], 100)
        self.assertEqual(result[2], 200)

    def test_slice_empty_range_returns_empty(self):
        # An empty range should produce an empty dict
        full   = {1:100, 2:100}
        result = _slice(full, range(5, 5))
        self.assertEqual(result, {})

    def test_slice_switches_keeps_switch_with_host_in_range(self):
        # A switch whose host is in the range should be kept
        result = _slice_switches(GREEN_SWITCHES, WG1_BLOCKS)
        self.assertIn("SW12", result)   # SW12 host=12 is in WG1

    def test_slice_switches_excludes_switch_outside_range(self):
        # A switch whose host is outside the range should be excluded
        result = _slice_switches(GREEN_SWITCHES, WG1_BLOCKS)
        self.assertNotIn("SW76", result)   # SW76 host=76 is in WG2

    def test_slice_switches_empty_range_returns_empty(self):
        # Slicing with an empty range should return no switches
        result = _slice_switches(GREEN_SWITCHES, range(0, 0))
        self.assertEqual(result, {})

    def test_slice_crossings_keeps_crossing_in_range(self):
        # Crossing block 19 is in WG1 range (1-75)
        result = _slice_crossings(GREEN_CROSSINGS, WG1_BLOCKS)
        self.assertIn(19, result)

    def test_slice_crossings_excludes_crossing_outside_range(self):
        # Crossing block 108 is in WG2 range (76-150), not WG1
        result = _slice_crossings(GREEN_CROSSINGS, WG1_BLOCKS)
        self.assertNotIn(108, result)

    def test_slice_crossings_empty_list_returns_empty(self):
        # Slicing an empty crossings list should return an empty list
        result = _slice_crossings([], WG1_BLOCKS)
        self.assertEqual(result, [])


# =============================================================================
# 12.  FULL WAYSIDE INTEGRATION — real Green/Red data
# =============================================================================

class TestFullWaysideIntegration(unittest.TestCase):
    """
    Integration tests using actual WAYSIDE_CONFIGS data.
    No CTC or UI involved — just calls compute_wayside_outputs
    directly with realistic block states.
    """

    def _run_wg1(self, state):
        cfg = WAYSIDE_CONFIGS["WG1"]
        return compute_wayside_outputs(
            state, cfg["block_lengths"], cfg["switches"],
            cfg["crossings"], cfg["signal_blocks"])

    def _run_wr1(self, state):
        cfg = WAYSIDE_CONFIGS["WR1"]
        return compute_wayside_outputs(
            state, cfg["block_lengths"], cfg["switches"],
            cfg["crossings"], cfg["signal_blocks"])

    def test_wg1_all_clear_all_signal_blocks_green(self):
        # With no trains every signal block on WG1 should be green
        cfg    = WAYSIDE_CONFIGS["WG1"]
        state  = _empty_state(cfg["block_lengths"])
        result = self._run_wg1(state)
        for blk, sig in result["signals"].items():
            if sig is not None:
                self.assertEqual(sig, "green",
                    msg=f"WG1 block {blk} expected green, got {sig}")

    def test_wg1_all_switches_normal_no_trains(self):
        # With no trains all WG1 switches should be normal
        cfg    = WAYSIDE_CONFIGS["WG1"]
        state  = _empty_state(cfg["block_lengths"])
        result = self._run_wg1(state)
        for sw_id, pos in result["switches"].items():
            self.assertEqual(pos, "normal",
                msg=f"WG1 {sw_id} expected normal, got {pos}")

    def test_wg1_non_signal_blocks_return_none(self):
        # Blocks not in WG1 signal_blocks must return None
        cfg    = WAYSIDE_CONFIGS["WG1"]
        state  = _empty_state(cfg["block_lengths"])
        result = self._run_wg1(state)
        for blk, sig in result["signals"].items():
            if blk not in cfg["signal_blocks"]:
                self.assertIsNone(sig,
                    msg=f"WG1 block {blk} not in signal_blocks but got {sig}")

    def test_wr1_all_clear_all_signal_blocks_green(self):
        # With no trains every signal block on WR1 should be green
        cfg    = WAYSIDE_CONFIGS["WR1"]
        state  = _empty_state(cfg["block_lengths"])
        result = self._run_wr1(state)
        for blk, sig in result["signals"].items():
            if sig is not None:
                self.assertEqual(sig, "green",
                    msg=f"WR1 block {blk} expected green, got {sig}")

    def test_wg1_train_on_block_22_signal_block_21_red(self):
        # Train on block 22 → unoccupied signal block 21 (next1=22) should be red
        # Block 21 is a signal block (station neighbour of station 22).
        # Unoccupied signal logic: if next1 is occupied → red
        cfg    = WAYSIDE_CONFIGS["WG1"]
        state  = _occupy(_empty_state(cfg["block_lengths"]), 22)
        result = self._run_wg1(state)
        self.assertEqual(result["signals"][21], "red")

    def test_wg1_output_has_reach_entry_for_occupied_block(self):
        # An occupied block on WG1 should produce a reach entry
        cfg    = WAYSIDE_CONFIGS["WG1"]
        state  = _occupy(_empty_state(cfg["block_lengths"]), 10, authority=0.5)
        result = self._run_wg1(state)
        self.assertIn(10, result["reach"])

    def test_wr1_crossing_11_active_when_occupied(self):
        # Red crossing at block 11 should be active when block 11 is occupied
        cfg    = WAYSIDE_CONFIGS["WR1"]
        state  = _occupy(_empty_state(cfg["block_lengths"]), 11)
        result = self._run_wr1(state)
        self.assertEqual(result["crossings"][11], "active")

    def test_wr1_sw9_safety_lock_when_host_occupied(self):
        # SW9 host=9; occupying block 9 should lock it to normal
        cfg    = WAYSIDE_CONFIGS["WR1"]
        state  = _occupy(_empty_state(cfg["block_lengths"]), 9)
        result = self._run_wr1(state)
        self.assertEqual(result["switches"]["SW9"], "normal")


if __name__ == "__main__":
    unittest.main(verbosity=2)
