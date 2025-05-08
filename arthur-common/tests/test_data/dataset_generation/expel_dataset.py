import json
import random
import uuid
from datetime import datetime
from typing import Any, Dict

from sample_dataset import SampleDataset


class ExpelDataset(SampleDataset):
    def __init__(self) -> None:
        self.project_uuid = str(uuid.uuid4())
        self.expel_uuid = str(uuid.uuid4())

    @property
    def inferences_per_file(self) -> int:
        return 1

    def file_name(self, date: datetime) -> str:
        date_str = date.strftime("%Y%m%d")
        return (
            f"{self.project_uuid}/{self.expel_uuid}/{date_str}/{str(uuid.uuid4())}.json"
        )

    def generate_sample(self, timestamp: datetime) -> Dict[str, Any]:
        """generate sample dataset"""
        features = ExpelDataset._generate_expel_features()
        # generate prediction range based on date so prediction line doesn't flatten over time
        prediction_range_start, prediction_range_end = (
            self.generate_prediction_range_from_timestamp(timestamp)
        )
        # make prediction higher for certain features so data isn't all over the place
        if (
            features.get("has_sus_sender_domain")
            or features.get("is_bad_corp")
            or features.get("body_count_malicious") > 0
            or features.get("has_attachment_attack_surface")
            or features.get("count_bad_words") > 0
        ):
            if prediction_range_end <= 0.7:
                prediction_range_end += 0.3
                prediction_range_start += 0.3
        prediction = random.uniform(prediction_range_start, prediction_range_end)

        return {
            "expel_alert_id": str(uuid.uuid4()),
            "organization_id": str(uuid.uuid4()),
            "pred_not_marketing": 1 - prediction if prediction > 0.8 else prediction,
            "pred_marketing": prediction if prediction > 0.8 else 1 - prediction,
            "predicted_label": "MARKETING" if prediction > 0.8 else "NOT_MARKETING",
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "features": features,
        }

    @staticmethod
    def format_row_as_json(data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "expel_alert_id": data["expel_alert_id"],
            "organization_id": data["organization_id"],
            "pred_not_marketing": data["pred_not_marketing"],
            "pred_marketing": data["pred_marketing"],
            "predicted_label": data["predicted_label"],
            "timestamp": data["timestamp"],
            "features": json.dumps(data["features"]),
        }

    @staticmethod
    def _generate_expel_features() -> Dict[str, Any]:
        # calculate fields that seem to depend on each other
        has_attachments = random.choice([True, False])
        if has_attachments:
            has_attachment_attack_surface = random.choice([True, False])
            count_attachments = random.randint(0, 5)
        else:
            has_attachment_attack_surface = False
            count_attachments = 0

        subject_has_marketing = random.choice([True, False])
        if subject_has_marketing:
            subject_count_marketing = random.randint(0, 3)
        else:
            subject_count_marketing = 0

        body_count_marketing = random.randint(0, 5)
        body_count_malicious = random.randint(0, body_count_marketing)

        # return sample features
        return {
            "severity": random.choice(["LOW", "MEDIUM", "HIGH"]),
            "email_colorfulness": (
                random.uniform(0, 1) if random.choice([True, False]) else None
            ),
            "domain_age": random.uniform(0, 20000),
            "has_sus_sender_domain": random.choice([True, False]),
            "return_path_match": random.choice([True, False]),
            "is_personal_domain_sender": random.choice([True, False]),
            "is_bad_corp": random.choice([True, False]),
            "count_domains": random.randint(1, 10),
            "count_urls": random.randint(0, 20),
            "subject_has_marketing": subject_has_marketing,
            "sender_has_marketing": random.choice([True, False]),
            "body_count_marketing": body_count_marketing,
            "subject_count_marketing": subject_count_marketing,
            "body_count_malicious": body_count_malicious,
            "unsubscribe_ind": random.choice([True, False]),
            "has_attachments": has_attachments,
            "has_attachment_attack_surface": has_attachment_attack_surface,
            "count_attachments": count_attachments,
            "len_text_body": random.randint(100, 10000),
            "text_body_rendered": random.choice([True, False]),
            "language": random.choice(["en", "es", "fr", "de", "it"]),
            "count_bad_words": random.randint(0, 10),
            "is_phishing_sim": random.choice([True, False]),
        }
