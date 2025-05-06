"""Tests for the DwdPollenApiClient."""

import pytest

from aioresponses import aioresponses
from freezegun import freeze_time

from pollen_api_dwd import PollenApiDwd
from pollen_api_dwd.client import DWD_URL


@pytest.mark.asyncio
@freeze_time("2025-05-04 12:00:00")
async def test_fetch_parses_legend_and_last_update():
    """Test that fetch parses legend and last update correctly."""
    client = PollenApiDwd()

    sample_data = {
        "legend": {
            "id5": "2",
            "id2_desc": "keine bis geringe Belastung",
            "id5_desc": "mittlere Belastung",
            "id1_desc": "keine Belastung",
            "id6": "2-3",
            "id7": "3",
            "id6_desc": "mittlere bis hohe Belastung",
            "id1": "0",
            "id7_desc": "hohe Belastung",
            "id2": "0-1",
            "id3": "1",
            "id4": "1-2",
            "id4_desc": "geringe bis mittlere Belastung",
            "id3_desc": "geringe Belastung",
        },
        "last_update": "2025-05-04 11:00 Uhr",
        "sender": "Deutscher Wetterdienst - Medizin-Meteorologie",
        "name": "Pollenflug-Gefahrenindex für Deutschland ausgegeben vom Deutschen Wetterdienst",
        "content": [
            {
                "partregion_name": "Inseln und Marschen",
                "Pollen": {
                    "Hasel": {"dayafter_to": "0", "today": "0", "tomorrow": "0"},
                    "Birke": {"dayafter_to": "1", "tomorrow": "1", "today": "1"}
                },
                "region_name": "Schleswig-Holstein und Hamburg",
                "region_id": 10,
                "partregion_id": 11,
            },
            {
                "region_id": 10,
                "partregion_id": 12,
                "Pollen": {
                    "Birke": {"today": "1-2", "tomorrow": "1", "dayafter_to": "1"},
                    "Hasel": {"today": "0", "tomorrow": "0", "dayafter_to": "0"}
                },
                "partregion_name": "Geest,Schleswig-Holstein und Hamburg",
                "region_name": "Schleswig-Holstein und Hamburg",
            },
            {
                "partregion_id": 121,
                "region_id": 120,
                "region_name": "Bayern",
                "partregion_name": "Allgäu/Oberbayern/Bay. Wald",
                "Pollen": {
                    "Birke": {"dayafter_to": "1", "today": "0-1", "tomorrow": "1"},
                    "Hasel": {"dayafter_to": "0", "tomorrow": "0", "today": "0"}
                },
            },
            {
                "partregion_name": "Donauniederungen",
                "Pollen": {
                    "Birke": {"tomorrow": "1", "today": "0-1", "dayafter_to": "1"},
                    "Roggen": {"dayafter_to": "0", "today": "0", "tomorrow": "0"}
                },
                "region_name": "Bayern",
                "region_id": 120,
                "partregion_id": 122,
            },
            {
                "partregion_name": "Bayern nördl. der Donau, o. Bayr. Wald, o. Mainfranken",
                "Pollen": {
                    "Birke": {"today": "0-1", "tomorrow": "1", "dayafter_to": "1"},
                    "Esche": {"dayafter_to": "0", "tomorrow": "0", "today": "0"}
                },
                "region_name": "Bayern",
                "region_id": 120,
                "partregion_id": 123,
            },
            {
                "Pollen": {
                    "Hasel": {"today": "0", "tomorrow": "0", "dayafter_to": "0"},
                    "Birke": {"tomorrow": "1", "today": "0-1", "dayafter_to": "1"}
                },
                "partregion_name": "Mainfranken",
                "region_name": "Bayern",
                "region_id": 120,
                "partregion_id": 124,
            },
        ],
        "next_update": "2025-05-05 11:00 Uhr",
    }

    with aioresponses() as mock:
        mock.get(DWD_URL, payload=sample_data)
        await client.fetch()

    assert client.last_update.day == 4
    assert client.next_update.day == 5
    assert client.legend["2-3"]["severity"] == 5
    assert client.legend["0"]["desc"] == "keine Belastung"
    assert client.regions == ["Bayern", "Schleswig-Holstein und Hamburg"]
    assert client.region_id("Bayern") == 120
    assert client.partregion_id("Bayern", "Mainfranken") == 124
    assert client.partregions("Bayern") == ["Allgäu/Oberbayern/Bay. Wald", "Donauniederungen", "Bayern nördl. der Donau, o. Bayr. Wald, o. Mainfranken", "Mainfranken"]
    assert client.pollen("Bayern", "Bayern nördl. der Donau, o. Bayr. Wald, o. Mainfranken")["Birke"] == (1, 'keine bis geringe Belastung')

@pytest.mark.asyncio
async def test_invalid_region_raises():
    """Test that invalid region raises a ValueError."""
    client = PollenApiDwd()
    client.region_data = {"1": {"1": {"pollen": {}}}}
    client.last_update = client._parse_timestamp("2024-05-04 11:00 Uhr")

    with pytest.raises(ValueError):
        client.pollen("invalid", "1")

    with pytest.raises(ValueError):
        client.pollen("1", "invalid")
