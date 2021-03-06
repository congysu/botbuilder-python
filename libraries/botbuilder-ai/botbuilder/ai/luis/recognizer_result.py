# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from typing import Dict, NamedTuple

from . import IntentScore


class TopIntent(NamedTuple):
    """The top scoring intent and its score."""

    intent: str
    score: float


class RecognizerResult:
    """
    Contains recognition results generated by a recognizer.
    """

    def __init__(
        self,
        text: str = None,
        altered_text: str = None,
        intents: Dict[str, IntentScore] = None,
        entities: Dict[str, object] = None,
    ):
        self._text: str = text
        self._altered_text: str = altered_text
        self._intents: Dict[str, IntentScore] = intents
        self._entities: Dict[str, object] = entities
        self._properties: Dict[str, object] = {}

    @property
    def text(self) -> str:
        """Gets the input text to recognize.
        
        :return: Original text to recognizer.
        :rtype: str
        """

        return self._text

    @text.setter
    def text(self, value: str) -> None:
        """Sets the input text to recognize.
        
        :param value: Original text to recognizer.
        :type value: str
        :return:
        :rtype: None
        """

        self._text = value

    @property
    def altered_text(self) -> str:
        """Gets the input text as modified by the recognizer, for example for spelling correction.
        
        :return: Text modified by recognizer.
        :rtype: str
        """

        return self._altered_text

    @altered_text.setter
    def altered_text(self, value: str) -> None:
        """Sets the input text as modified by the recognizer, for example for spelling correction.
        
        :param value: Text modified by recognizer.
        :type value: str
        :return:
        :rtype: None
        """

        self._altered_text = value

    @property
    def intents(self) -> Dict[str, IntentScore]:
        """Gets the recognized intents, with the intent as key and the confidence as value.
        
        :return: Mapping from intent to information about the intent.
        :rtype: Dict[str, IntentScore]
        """

        return self._intents

    @intents.setter
    def intents(self, value: Dict[str, IntentScore]) -> None:
        """Sets the recognized intents, with the intent as key and the confidence as value.

        
        :param value: Mapping from intent to information about the intent.
        :type value: Dict[str, IntentScore]
        :return:
        :rtype: None
        """

        self._intents = value

    @property
    def entities(self) -> Dict:
        """Gets the recognized top-level entities.
        
        :return: Object with each top-level recognized entity as a key.
        :rtype: Dict
        """

        return self._entities

    @entities.setter
    def entities(self, value: Dict) -> None:
        """Sets the recognized top-level entities.
        
        :param value: Object with each top-level recognized entity as a key.
        :type value: Dict
        :return:
        :rtype: None
        """

        self._entities = value

    @property
    def properties(self) -> Dict[str, object]:
        """Gets properties that are not otherwise defined by the <see cref="RecognizerResult"/> type but that
        might appear in the REST JSON object.
        
        :return: The extended properties for the object.
        :rtype: Dict[str, object]
        """

        return self._properties

    @properties.setter
    def properties(self, value: Dict[str, object]) -> None:
        """Sets properties that are not otherwise defined by the <see cref="RecognizerResult"/> type but that
        might appear in the REST JSON object.
        
        :param value: The extended properties for the object.
        :type value: Dict[str, object]
        :return:
        :rtype: None
        """

        self._properties = value

    def get_top_scoring_intent(self) -> TopIntent:
        """Return the top scoring intent and its score.
        
        :return: Intent and score.
        :rtype: TopIntent
        """

        if self.intents is None:
            raise TypeError("result.intents can't be None")

        top_intent = TopIntent(intent="", score=0.0)
        for intent_name, intent_score in self.intents.items():
            score = intent_score.score
            if score > top_intent[1]:
                top_intent = TopIntent(intent_name, score)

        return top_intent
