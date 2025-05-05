"""Client for fetching and parsing pollen data from the DWD API."""

import asyncio
import datetime
import json
import logging
from zoneinfo import ZoneInfo

import aiohttp

logger = logging.getLogger(__name__)


class PollenApiDwd:
    """Client for fetching and parsing pollen data from the DWD API."""

    URL = "https://opendata.dwd.de/climate_environment/health/alerts/s31fg.json"

    def __init__(self) -> None:
        """Initialize the DwdPollenApiClient with default attributes."""
        self.raw_data = {}
        self.region_data = {}
        self.last_update = None
        self.next_update = None
        self.legend = {}

    async def fetch(self):
        """Fetch and parse the pollen data from the DWD API."""
        async with (
            aiohttp.ClientSession() as session,
            session.get(self.URL) as response,
        ):
            response.raise_for_status()
            self.raw_data = await response.text()
            self._parse_data()

    def _parse_legend(self):
        """Parse the legend data from the raw JSON response."""
        parsed_legend = {}
        for key, value in self.legend.items():
            if key.startswith("id") and "_desc" not in key:
                parsed_legend[value] = {
                    "severity": int(key.replace("id", "")) - 1,
                    "desc": self.legend[key + "_desc"],
                }
        self.legend = parsed_legend

    def _parse_region_data(self):
        """Group pollen data by region and partregion."""
        self.region_data.clear()
        for entry in self.content:
            region_name = entry.get("region_name")
            if not region_name:
                continue
            partregion = entry.get("partregion_name") or region_name
            pollen_data = entry.get("Pollen", {})
            self.region_data.setdefault(region_name, {})[partregion] = {
                "pollen": pollen_data
            }

    def _parse_data(self):
        data = json.loads(self.raw_data)

        if not isinstance(data, dict):
            raise TypeError("Expected top-level JSON object to be a dictionary")

        for key, value in data.items():
            setattr(self, key, value)

        self.last_update = self._parse_timestamp(data.get("last_update"))
        self.next_update = self._parse_timestamp(data.get("next_update"))

        self._parse_region_data()
        delattr(self, "content")
        self._parse_legend()

    def _parse_timestamp(self, timestamp_str):
        if not timestamp_str:
            return None
        return datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M Uhr")

    @property
    def regions(self):
        """Return the names of all regions available in the data."""
        return sorted(self.region_data)

    def partregions(self, region):
        """Return a list of partregions for the given region."""
        if region not in self.region_data:
            raise ValueError(f"Region '{region}' not found")
        return list(self.region_data[region])

    def pollen(self, region, partregion, days_ahead=0):
        """Return a dictionary of pollen data for the specified region and partregion."""
        days = ("today", "tomorrow", "dayafter_to")
        if region not in self.region_data:
            raise ValueError(f"Region '{region}' not found")
        if partregion not in self.region_data[region]:
            raise ValueError(f"Partregion '{partregion}' not found")

        tz = ZoneInfo("Europe/Berlin")
        now = datetime.datetime.now(tz).replace(tzinfo=None)
        day_diff = (now + datetime.timedelta(days=days_ahead) - self.last_update).days
        if day_diff < 0 or day_diff >= len(days):
            return {}

        day_key = days[day_diff]
        pollen_data = self.region_data[region][partregion]["pollen"]
        return {
            k: (
                self.legend.get(v.get(day_key), {}).get("severity"),
                self.legend.get(v.get(day_key), {}).get("desc"),
            )
            for k, v in pollen_data.items()
            if v.get(day_key)
        }

    def __repr__(self):
        """Return a string representation of the DwdPollenApiClient instance."""
        keys = list(self.__dict__.keys())
        return f"<DwdPollenApiClient keys={keys} regions={len(self.region_data)}>"


# Example usage
if __name__ == "__main__":

    async def main():
        """Run the DwdPollenApiClient to fetch and display pollen data."""
        client = PollenApiDwd()
        await client.fetch()
        print(client)
        print("Regionen: ", client.regions, "\n")  # noqa: T201
        for region in client.regions:
            print(f"Region: {region}")  # noqa: T201
            print("   Partregions:", client.partregions(region), "\n")  # noqa: T201
        print("Last Update: ", client.last_update)  # noqa: T201
        print("Next Update: ", client.next_update, "\n")  # noqa: T201
        print(
            "Pollenflug heute:",
            client.pollen(
                "Schleswig-Holstein und Hamburg", "Geest,Schleswig-Holstein und Hamburg"
            ),
        )  # noqa: T201
        print()  # noqa: T201
        print(client.raw_data)  # noqa: T201

    asyncio.run(main())
