# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import platform
from collections import OrderedDict
from typing import Dict, List, Set, Union

from azure.cognitiveservices.language.luis.runtime.models import (
    CompositeEntityModel,
    EntityModel,
    LuisResult,
)

from .. import __title__, __version__
from . import IntentScore, RecognizerResult


class LuisUtil:
    """
    Utility functions used to extract and transform data from Luis SDK
    """

    _metadata_key: str = "$instance"

    @staticmethod
    def normalized_intent(intent: str) -> str:
        return intent.replace(".", "_").replace(" ", "_")

    @staticmethod
    def get_intents(luis_result: LuisResult) -> Dict[str, IntentScore]:
        if luis_result.intents:
            return {
                LuisUtil.normalized_intent(i.intent): IntentScore(i.score or 0)
                for i in luis_result.intents
            }
        else:
            return {
                LuisUtil.normalized_intent(
                    luis_result.top_scoring_intent.intent
                ): IntentScore(luis_result.top_scoring_intent.score or 0)
            }

    @staticmethod
    def extract_entities_and_metadata(
        entities: List[EntityModel],
        composite_entities: List[CompositeEntityModel],
        verbose: bool,
    ) -> Dict:
        entities_and_metadata = {}
        if verbose:
            entities_and_metadata[LuisUtil._metadata_key] = {}

        composite_entity_types = set()

        # We start by populating composite entities so that entities covered by them are removed from the entities list
        if composite_entities:
            composite_entity_types = set(ce.parent_type for ce in composite_entities)
            current = entities
            for compositeEntity in composite_entities:
                current = LuisUtil.populate_composite_entity_model(
                    compositeEntity, current, entities_and_metadata, verbose
                )
            entities = current

        for entity in entities:
            # we'll address composite entities separately
            if entity.type in composite_entity_types:
                continue

            LuisUtil.add_property(
                entities_and_metadata,
                LuisUtil.extract_normalized_entity_name(entity),
                LuisUtil.extract_entity_value(entity),
            )

            if verbose:
                LuisUtil.add_property(
                    entities_and_metadata[LuisUtil._metadata_key],
                    LuisUtil.extract_normalized_entity_name(entity),
                    LuisUtil.extract_entity_metadata(entity),
                )

        return entities_and_metadata

    @staticmethod
    def number(value: object) -> Union[int, float]:
        if value is None:
            return None

        try:
            s = str(value)
            i = int(s)
            return i
        except ValueError:
            f = float(s)
            return f

    @staticmethod
    def extract_entity_value(entity: EntityModel) -> object:
        if (
            entity.additional_properties is None
            or "resolution" not in entity.additional_properties
        ):
            return entity.entity

        resolution = entity.additional_properties["resolution"]
        if entity.type.startswith("builtin.datetime."):
            return resolution
        elif entity.type.startswith("builtin.datetimeV2."):
            if not resolution["values"]:
                return resolution

            resolution_values = resolution["values"]
            val_type = resolution["values"][0]["type"]
            timexes = [val["timex"] for val in resolution_values]
            distinct_timexes = list(OrderedDict.fromkeys(timexes))
            return {"type": val_type, "timex": distinct_timexes}
        else:
            if entity.type in {"builtin.number", "builtin.ordinal"}:
                return LuisUtil.number(resolution["value"])
            elif entity.type == "builtin.percentage":
                svalue = str(resolution["value"])
                if svalue.endswith("%"):
                    svalue = svalue[:-1]

                return LuisUtil.number(svalue)
            elif entity.type in {
                "builtin.age",
                "builtin.dimension",
                "builtin.currency",
                "builtin.temperature",
            }:
                units = str(resolution.unit)
                val = LuisUtil.number(resolution["value"])
                obj = {}
                if val is not None:
                    obj["number"] = val

                obj["units"] = units
                return obj
            else:
                return resolution.get("value") or resolution.get("values")

    @staticmethod
    def extract_entity_metadata(entity: EntityModel) -> Dict:
        obj = dict(
            startIndex=int(entity.start_index),
            endIndex=int(entity.end_index + 1),
            text=entity.entity,
            type=entity.type,
        )

        if entity.additional_properties is not None:
            if "score" in entity.additional_properties:
                obj["score"] = float(entity.additional_properties["score"])

            resolution = entity.additional_properties.get("resolution")
            if resolution is not None and resolution.get("subtype") is not None:
                obj["subtype"] = resolution["subtype"]

        return obj

    @staticmethod
    def extract_normalized_entity_name(entity: EntityModel) -> str:
        # Type::Role -> Role
        type = entity.type.split(":")[-1]
        if type.startswith("builtin.datetimeV2."):
            type = "datetime"

        if type.startswith("builtin.currency"):
            type = "money"

        if type.startswith("builtin."):
            type = type[8:]

        role = (
            entity.additional_properties["role"]
            if entity.additional_properties is not None
            and "role" in entity.additional_properties
            else ""
        )
        if role and not role.isspace():
            type = role

        return type.replace(".", "_").replace(" ", "_")

    @staticmethod
    def populate_composite_entity_model(
        composite_entity: CompositeEntityModel,
        entities: List[EntityModel],
        entities_and_metadata: Dict,
        verbose: bool,
    ) -> List[EntityModel]:
        children_entities = {}
        children_entities_metadata = {}
        if verbose:
            children_entities[LuisUtil._metadata_key] = {}

        # This is now implemented as O(n^2) search and can be reduced to O(2n) using a map as an optimization if n grows
        composite_entity_metadata = next(
            (
                e
                for e in entities
                if e.type == composite_entity.parent_type
                and e.entity == composite_entity.value
            ),
            None,
        )

        # This is an error case and should not happen in theory
        if composite_entity_metadata is None:
            return entities

        if verbose:
            children_entities_metadata = LuisUtil.extract_entity_metadata(
                composite_entity_metadata
            )
            children_entities[LuisUtil._metadata_key] = {}

        covered_set: List[EntityModel] = []
        for child in composite_entity.children:
            for entity in entities:
                # We already covered this entity
                if entity in covered_set:
                    continue

                # This entity doesn't belong to this composite entity
                if child.type != entity.type or not LuisUtil.composite_contains_entity(
                    composite_entity_metadata, entity
                ):
                    continue

                # Add to the set to ensure that we don't consider the same child entity more than once per composite
                covered_set.append(entity)
                LuisUtil.add_property(
                    children_entities,
                    LuisUtil.extract_normalized_entity_name(entity),
                    LuisUtil.extract_entity_value(entity),
                )

                if verbose:
                    LuisUtil.add_property(
                        children_entities[LuisUtil._metadata_key],
                        LuisUtil.extract_normalized_entity_name(entity),
                        LuisUtil.extract_entity_metadata(entity),
                    )

        LuisUtil.add_property(
            entities_and_metadata,
            LuisUtil.extract_normalized_entity_name(composite_entity_metadata),
            children_entities,
        )
        if verbose:
            LuisUtil.add_property(
                entities_and_metadata[LuisUtil._metadata_key],
                LuisUtil.extract_normalized_entity_name(composite_entity_metadata),
                children_entities_metadata,
            )

        # filter entities that were covered by this composite entity
        return [entity for entity in entities if entity not in covered_set]

    @staticmethod
    def composite_contains_entity(
        composite_entity_metadata: EntityModel, entity: EntityModel
    ) -> bool:
        return (
            entity.start_index >= composite_entity_metadata.start_index
            and entity.end_index <= composite_entity_metadata.end_index
        )

    @staticmethod
    def add_property(obj: Dict[str, object], key: str, value: object) -> None:
        # If a property doesn't exist add it to a new array, otherwise append it to the existing array.

        if key in obj:
            obj[key].append(value)
        else:
            obj[key] = [value]

    @staticmethod
    def add_properties(luis: LuisResult, result: RecognizerResult) -> None:
        if luis.sentiment_analysis is not None:
            result.properties["sentiment"] = {
                "label": luis.sentiment_analysis.label,
                "score": luis.sentiment_analysis.score,
            }

    @staticmethod
    def get_user_agent():
        package_user_agent = f"{__title__}/{__version__}"
        uname = platform.uname()
        os_version = f"{uname.machine}-{uname.system}-{uname.version}"
        py_version = f"Python,Version={platform.python_version()}"
        platform_user_agent = f"({os_version}; {py_version})"
        user_agent = f"{package_user_agent} {platform_user_agent}"
        return user_agent
