"""Tests for the DwdPollenApiClient."""

from aioresponses import (
    aioresponses,
)  # Ensure `aioresponses` is installed in your environment
import pytest

import pollen_api_dwd


@pytest.mark.asyncio
async def test_fetch_parses_legend_and_last_update():
    """Test that fetch parses legend and last update correctly."""
    client = client.DwdPollenApiClient()

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
        mock.get(client.URL, payload=sample_data)
        await client.fetch()

    assert client.last_update.year == 2025
    assert client.legend["2-3"]["severity"] == 5
    assert client.legend["0"]["desc"] == "keine Belastung"
    assert client.region_data["Bayern"]["Bayern nördl. der Donau, o. Bayr. Wald, o. Mainfranken"]["pollen"]["Birke"] == {'dayafter_to': '1', 'today': '0-1', 'tomorrow': '1'}

@pytest.mark.asyncio
async def test_invalid_region_raises():
    """Test that invalid region raises a ValueError."""
    client = DwdPollenApiClient()
    client.region_data = {"1": {"1": {"pollen": {}}}}
    client.last_update = client._parse_timestamp("2024-05-04 11:00 Uhr")

    with pytest.raises(ValueError):
        client.pollen("invalid", "1")

    with pytest.raises(ValueError):
        client.pollen("1", "invalid")
