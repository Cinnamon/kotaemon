# mypy: ignore-errors
from datetime import datetime

from ktem.db.base_models import ScenarioType
from ktem.db.models import Scenario
from sqlmodel import Session, select, update


class ScenarioCRUD:
    def __init__(self, engine):
        self._engine = engine

    def list_all(self) -> list[Scenario]:
        with Session(self._engine) as session:
            statement = select(Scenario)
            results = session.exec(statement).all()
            return results

    def create(
        self,
        name: str,
        scenario_type: str | ScenarioType,
        specification: str,
        base_prompt: str,
        retrieval_validator: str,
    ) -> str:
        # validate name and prompt
        name = name.strip()
        base_prompt = base_prompt.strip()
        assert (
            name != "" and base_prompt != ""
        ), "Invalid name or prompt: cannot be empty."

        if isinstance(scenario_type, ScenarioType):
            scenario_type = scenario_type.value

        with Session(self._engine) as session:
            # Ensure scenario name is unique
            existing_scenario = self.query_by_name(name)
            if existing_scenario:
                raise Exception(f"Scenario name: {name} already exists!")

            scenario = Scenario(
                name=name,
                scenario_type=scenario_type,
                specification=specification,
                base_prompt=base_prompt,
                retrieval_validator=retrieval_validator,
                last_updated=datetime.now(),
            )
            session.add(scenario)
            session.commit()

            return scenario.id

    def query_by_id(self, scenario_id: str) -> Scenario | None:
        with Session(self._engine) as session:
            statement = select(Scenario).where(Scenario.id == scenario_id)
            result = session.exec(statement).first()
            return result

    def query_by_name(self, scenario_name: str) -> Scenario | None:
        with Session(self._engine) as session:
            statement = select(Scenario).where(Scenario.name == scenario_name)
            result = session.exec(statement).first()
            return result

    def delete_by_name(self, scenario_name: str) -> bool:
        with Session(self._engine) as session:
            statement = select(Scenario).where(Scenario.name == scenario_name)
            result = session.exec(statement).first()

            if result:
                session.delete(result)
                session.commit()
                return True
            else:
                raise Exception(f"Record with name-{scenario_name} does not exist!")

        return False

    def update_by_name(
        self,
        name: str,
        new_name: str | None = None,
        scenario_type: str | None = None,
        specification: str | None = None,
        base_prompt: str | None = None,
        retrieval_validator: str | None = None,
    ) -> bool:
        # validate name and prompt
        new_name = new_name.strip()
        base_prompt = base_prompt.strip()
        assert (
            new_name != "" and base_prompt != ""
        ), "Invalid name or prompt: cannot be empty."

        fields_to_update = {
            "name": new_name,
            "scenario_type": scenario_type,
            "specification": specification,
            "base_prompt": base_prompt,
            "retrieval_validator": retrieval_validator,
        }

        # Ensure only non-None values are updated
        fields_to_update = {k: v for k, v in fields_to_update.items() if v is not None}

        stmt = update(Scenario).where(Scenario.name == name).values(**fields_to_update)

        with Session(self._engine) as session:
            session.execute(stmt)
            session.commit()

        return True
