import random
import uuid
from datetime import datetime
from typing import Any, Dict

from sample_dataset import SampleDataset


class AxiosDataset(SampleDataset):
    def __init__(self) -> None:
        self.inference_id = uuid.uuid4()
        self.date_formatting = "year=%Y/month=%m/day=%d/hour=%H/minute=%M/second=%S"
        self.cities = [
            "atlanta",
            "austin",
            "boston",
            "charlotte",
            "chicago",
            "cleveland",
            "columbus",
            "dallas",
            "denver",
            "des-moines",
            "detroit",
            "houston",
            "indianapolis",
            "miami",
            "nashville",
            "new-orleans",
            "nw-arkansas",
            "philadelphia",
            "phoenix",
            "portland",
            "raleigh",
            "richmond",
            "salt-lake-city",
            "san-antonio",
            "san-diego",
            "san-francisco",
            "seattle",
            "tampa-bay",
            "twin-cities",
            "washington-dc",
        ]  # cities in sample data, will be one-hot encoded

    @property
    def inferences_per_file(self) -> int:
        return 1

    def file_name(self, date: datetime) -> str:
        date_str = date.strftime(self.date_formatting)
        return f"subject-line-open-rate/inferences/{date_str}/{self.inference_id}.json"

    def generate_sample(self, timestamp: datetime) -> Dict[str, Any]:
        # generate base metrics
        self.inference_id = (
            uuid.uuid4()
        )  # will be used in file_name retrieval so file name UUID matches inference_id
        prediction_range_start, prediction_range_end = (
            self.generate_prediction_range_from_timestamp(timestamp)
        )
        predicted_open_rate = random.uniform(
            prediction_range_start,
            prediction_range_end,
        )
        mean_open_rate = (
            predicted_open_rate + random.uniform(0, 0.1)
            if predicted_open_rate <= 0.9
            else predicted_open_rate
        )
        confirmed_open_rate = predicted_open_rate + random.normalvariate(sigma=0.2)
        sample = {
            "audience_map_version": self.file_name(timestamp),
            "inference_id": str(self.inference_id),
            "inference_time": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "mean_open_rate": mean_open_rate,
            "model_version": timestamp.strftime(
                f"subject-line-open-rate/model/{self.date_formatting}/ebm.pkl",
            ),
            "predicted_open_rate": predicted_open_rate,
            "confirmed_open_rate": confirmed_open_rate,
            "score": random.randint(0, 100),
            "subject_line": f"My random subject line: {''.join((random.choice('abcdxyzpqr') for i in range(7)))}",
            # not randomized because axios says irrelevant to arthur anyway, and strings will be hard to make readable
            "guidance": {
                "brief": {
                    "negative_factors": ["No long sentences"],
                    "positive_factors": [
                        "Thirty five characters or fewer",
                    ],
                    "score": random.randint(0, 100),
                },
                "clear": {
                    "negative_factors": ["No complex words"],
                    "positive_factors": [
                        "Less than three syllables per word",
                        "Reasonable readability",
                    ],
                    "score": random.randint(0, 100),
                },
                "smart": {
                    "negative_factors": ["No common incorrect word usages"],
                    "positive_factors": [
                        "Sentence case",
                        "Active voice",
                        "Starts with emoji",
                    ],
                    "score": random.randint(0, 100),
                },
            },
            "features": self._generate_features(),
        }

        # one-hot encode cities
        for city in self.cities:
            sample["features"][city] = 0
        hot_city = random.sample(self.cities, 1)[0]  # randomly select a city to be true
        sample["features"][hot_city] = 1
        sample["audience_slug"] = hot_city
        sample["nullable_col"] = random.choice(["present", None])

        return sample

    @staticmethod
    def _generate_features() -> Dict[str, Any]:
        features = {
            "emoji_count": random.randint(1, 5),
            "energy-policy": random.choice([0, 1]),
            "finish-line": random.choice([0, 1]),
            "fintech-deals": random.choice([0, 1]),
            "flesch": round(random.uniform(30, 90), 2),
            "future-of-defense": random.choice([0, 1]),
            "future-of-health-care": random.choice([0, 1]),
            "generate": random.choice([0, 1]),
            "gunningfog": round(random.uniform(10, 18), 2),
            "health-care-policy": random.choice([0, 1]),
            "health-tech-deals": random.choice([0, 1]),
            "hill-leaders": random.choice([0, 1]),
            "is_passive_voice": random.choice([True, False]),
            "is_past_tense": random.choice([True, False]),
            "is_sentence_case": random.choice([True, False]),
            "kincaid": round(random.uniform(8, 16), 2),
            "latino": random.choice([0, 1]),
            "length_char_count_suffix": random.randint(10, 50),
            "length_char_count_total": random.randint(50, 300),
            "length_sixty_chars_or_less": random.choice([True, False]),
            "length_thirtyfive_chars_or_less": random.choice([True, False]),
            "length_three_words": random.choice([True, False]),
            "length_word_count_suffix": random.randint(2, 10),
            "length_word_count_total": random.randint(5, 30),
            "lix": round(random.uniform(1, 50), 2),
            "long_words": random.choice([0, 1]),
            "macro": random.choice([0, 1]),
            "markets": random.choice([0, 1]),
            "media-deals": random.choice([0, 1]),
            "media-trends": random.choice([0, 1]),
            "pm": random.choice([0, 1]),
            "polarity": round(random.uniform(-1.0, 1.0), 2),
            "pro-rata": random.choice([0, 1]),
            "retail-deals": random.choice([0, 1]),
            "rix": random.choice([0, 1]),
            "science": random.choice([0, 1]),
            "sentences": random.randint(1, 5),
            "smog": round(random.uniform(8.0, 18.0), 2),
            "start_article": random.choice([0, 1]),
            "start_conjunction": random.choice([0, 1]),
            "start_interrogative": random.choice([0, 1]),
            "start_preposition": random.choice([0, 1]),
            "start_pronoun": random.choice([0, 1]),
            "start_subordination": random.choice([0, 1]),
            "subjectivity": round(random.uniform(0.0, 1.0), 2),
            "syllable_count": random.randint(10, 100),
            "tech-policy": random.choice([0, 1]),
            "thought-bubble": random.choice([0, 1]),
            "tn-50": random.choice([0, 1]),
            "type_token_ratio": round(random.uniform(0.3, 0.9), 2),
            "vitals": random.choice([0, 1]),
            "wordtypes": random.randint(5, 30),
        }
        features["emoji_end"] = random.randint(0, 1) if features["emoji_count"] else 0
        features["emoji_start"] = random.randint(0, 1) if features["emoji_count"] else 0
        words = round(random.randint(5, 50))
        features["words_per_sentence"] = round(words / features["sentences"], 2)
        features["syll_per_word"] = round(features["syllable_count"] / words, 2)
        features["is_present_tense"] = not features["is_past_tense"]
        features["is_title_case"] = not features["is_sentence_case"]

        # add embeddings
        for i in range(255):
            features[f"embedding_{i}"] = round(random.uniform(-0.2, 0.2), 2)
        return features

    @staticmethod
    def format_row_as_json(data: Dict[str, Any]) -> Dict[str, Any]:
        # not needed for axios
        raise NotImplementedError
