# SPDX-FileCopyrightText: 2026 Pedro Sordo Martínez <amurlaniakea@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Copyright (C) 2026 Pedro Sordo Martínez
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program. If not, see
# <https://www.gnu.org/licenses/>.

from __future__ import annotations

import json
from pathlib import Path

import pytest

DATA_FILE = Path(__file__).resolve().parents[1] / "backend" / "data" / "decay_chains.json"
VALID_MODES = {"alpha", "beta-", "beta+", "ec", "gamma", "sf"}
ARITHMETIC_MODES = {"alpha", "beta-", "beta+", "ec"}


@pytest.fixture(scope="module")
def payload():
    assert DATA_FILE.exists(), f"Missing data file: {DATA_FILE}"
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def chains(payload):
    return payload["chains"]


def test_metadata_present(payload):
    assert "metadata" in payload
    assert "version" in payload["metadata"]


def test_chain_ids_are_unique(chains):
    ids = [chain["id"] for chain in chains]
    assert len(ids) == len(set(ids))


def test_nuclide_ids_are_unique_per_chain(chains):
    for chain in chains:
        ids = [nuclide["id"] for nuclide in chain["nuclides"]]
        assert len(ids) == len(set(ids)), f"Duplicated nuclide ids in {chain['id']}"


def test_parent_exists_in_chain(chains):
    for chain in chains:
        ids = {nuclide["id"] for nuclide in chain["nuclides"]}
        assert chain["parent"] in ids


def test_edges_reference_existing_nuclides(chains):
    for chain in chains:
        ids = {nuclide["id"] for nuclide in chain["nuclides"]}
        for edge in chain["edges"]:
            assert edge["from"] in ids
            assert edge["to"] in ids
            assert edge["mode"] in VALID_MODES
            branch = edge.get("branch", 100)
            assert 0 <= branch <= 100


def test_outgoing_branches_do_not_exceed_100_percent(chains):
    for chain in chains:
        totals: dict[str, float] = {}
        for edge in chain["edges"]:
            totals[edge["from"]] = totals.get(edge["from"], 0.0) + float(edge.get("branch", 100))
        for source, total in totals.items():
            assert total <= 100.0001, f"Branch sum for {source} in {chain['id']} is {total}"


def test_decay_arithmetic_for_simple_modes(chains):
    for chain in chains:
        by_id = {nuclide["id"]: nuclide for nuclide in chain["nuclides"]}
        for edge in chain["edges"]:
            if edge["mode"] not in ARITHMETIC_MODES:
                continue

            source = by_id[edge["from"]]
            target = by_id[edge["to"]]

            if edge["mode"] == "alpha":
                assert target["a"] == source["a"] - 4
                assert target["z"] == source["z"] - 2
            elif edge["mode"] == "beta-":
                assert target["a"] == source["a"]
                assert target["z"] == source["z"] + 1
            else:  # beta+ or ec
                assert target["a"] == source["a"]
                assert target["z"] == source["z"] - 1


def test_stable_nuclides_have_no_outgoing_decay(chains):
    for chain in chains:
        outgoing = {edge["from"] for edge in chain["edges"]}
        for nuclide in chain["nuclides"]:
            if nuclide.get("stable"):
                assert nuclide["id"] not in outgoing
                assert not nuclide.get("decay_modes")


def test_radioactive_nuclides_have_outgoing_decay(chains):
    for chain in chains:
        outgoing = {edge["from"] for edge in chain["edges"]}
        for nuclide in chain["nuclides"]:
            if not nuclide.get("stable"):
                assert nuclide["id"] in outgoing
                assert nuclide.get("decay_modes")
