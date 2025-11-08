"""
MIT License

Copyright (c) 2025 VeloSim Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import json
import simpy
from back.models.scenario import Scenario
from back.schemas.scenario import ScenarioInitializationRequest
from sim.entities.inputParameters import InputParameter
from sim.utils.json_parser_strategy import JsonParseStrategy
from sqlalchemy.orm import Session
from typing import Dict, Any


def load_scenario_dict(
    db: Session,
    scenario: ScenarioInitializationRequest | None = None,
    scenario_id: int | None = None,
) -> Dict[str, Any]:
    """
    Load scenario data from either:
    - a valid ScenarioInitializationRequest (JSON) object
    - a valid Scenario ID from database
    Returns a dictionary ready for parsing.
    """
    if scenario and scenario_id:
        raise ValueError("Provide either scenario JSON or scenario_id, not both")

    if scenario_id is not None:
        db_scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
        if not db_scenario:
            raise ValueError("Scenario not found")
        return {
            "id": db_scenario.id,
            "name": db_scenario.name,
            "content": db_scenario.content,
        }

    if scenario is not None:
        return scenario.model_dump(exclude_unset=True, by_alias=True)

    raise ValueError("Must provide either scenario JSON or scenario_id")


def parse_scenario(scenario_dict: dict) -> InputParameter:
    """
    Parse scenario dict into InputParameter.
    Returns the InputParameter for the given scenario ID.
    """
    payload = {"scenarios": [scenario_dict]}
    json_str = json.dumps(payload)
    env = simpy.Environment()
    parser = JsonParseStrategy()
    parsed_scenarios = parser.parse(env, json_str)
    return parsed_scenarios[scenario_dict["id"]]
