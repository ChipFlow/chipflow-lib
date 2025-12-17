import json
from pathlib import Path

from .. import ChipFlowError

def compare_events(gold_path: Path, gate_path: Path):
    with open(gold_path, "r") as f:
        gold = json.load(f)
    with open(gate_path, "r") as f:
        gate = json.load(f)
    if len(gold["events"]) != len(gate["events"]):
        raise ChipFlowError(f"Simulator check failed! Event mismatch: {len(gold['events'])} events in reference, {len(gate['events'])} in test output")
    for ev_gold, ev_gate in zip(gold["events"], gate["events"]):
        if ev_gold["peripheral"] != ev_gate["peripheral"] or \
           ev_gold["event"] != ev_gate["event"] or \
           ev_gold["payload"] != ev_gate["payload"]:
            raise ChipFlowError(f"Simulator check failed! Reference event {ev_gold} mismatches test event {ev_gate}")

    return True

