# mypy: ignore-errors
import re
from datetime import datetime

from sqlmodel import Session, select, update

from ktem.db.base_models import ScenarioType
from ktem.db.models import Scenario
from ktem.tags.crud import TagCRUD


class ScenarioValidator:
    def __init__(self, engine):
        self._engine = engine
        self._tag_crud = TagCRUD(engine)

    @staticmethod
    def validate_name(name: str | None) -> bool:
        if name is None or name.strip() == "":
            raise Exception("Scenario name is empty or None")
        return True

    @staticmethod
    def validate_type(type: str | ScenarioType) -> bool:
        if type is None or type not in ScenarioType.get_types():
            raise Exception(f"Invalid type. "
                            f"Expected: {','.join(ScenarioType.get_types())}. "
                            f"Got: {type}")
        return True

    @staticmethod
    def validate_prompt(prompt: str) -> bool:
        if prompt is None or prompt.strip() == "":
            raise Exception("Scenario prompt is empty or None")
        return True

    def validate_tags(self, content: str) -> bool:
        """
        Extract the tags from content.
        IF tags exist, it should be valid otherwise error will be raised
        """
        tags = re.findall(r'#\w+', content)

        if len(tags) > 0:
            for tag in tags:
                tag_name = tag[1:] if tag.startswith('#') else tag
                tag_result = self._tag_crud.query_by_name(tag_name=tag_name)

                if tag_result is None:
                    raise Exception(f"Tag {tag_name} does not exist")

        return True


class ScenarioCRUD:
    def __init__(self, engine):
        self._engine = engine
        self.validator = ScenarioValidator(engine)

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
        valid_tags: bool = False
    ) -> str:
        if isinstance(scenario_type, ScenarioType):
            scenario_type = scenario_type.value

        self.validator.validate_name(name)
        self.validator.validate_type(scenario_type)

        if valid_tags:
            self.validator.validate_tags(base_prompt)
            self.validator.validate_tags(retrieval_validator)

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
        scenario_type: str | None = None,
        specification: str | None = None,
        base_prompt: str | None = None,
        retrieval_validator: str | None = None,
        valid_tags: bool = False
    ) -> bool:

        self.validator.validate_type(scenario_type)
        if valid_tags:
            self.validator.validate_tags(base_prompt)
            self.validator.validate_tags(retrieval_validator)

        fields_to_update = {
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
