"""Client for fetching and parsing pollen data from the DWD API."""

import asyncio
import datetime
import json
import logging
from zoneinfo import ZoneInfo

import aiohttp

logger = logging.getLogger(__name__)

DAY_KEYS = ("today", "tomorrow", "dayafter_to")
DWD_URL = "https://opendata.dwd.de/climate_environment/health/alerts/s31fg.json"
TZ = ZoneInfo("Europe/Berlin")


class PollenApiDwd:
    """Client for fetching and parsing pollen data from the DWD API."""

    def __init__(self) -> None:
        """Initialize the DwdPollenApiClient with default attributes."""
        self.raw_data = ""
        self.name = ""
        self.sender = ""
        self.region_data = {}
        self.last_update = None
        self.next_update = None
        self.legend = {}

    async def fetch(self):
        """Fetch and parse the pollen data from the DWD API."""
        async with (
            aiohttp.ClientSession() as session,
            session.get(DWD_URL) as response,
        ):
            response.raise_for_status()
            self.raw_data = await response.text()
            self._parse_data()

    def _parse_data(self):
        data = json.loads(self.raw_data)

        if not isinstance(data, dict):
            raise TypeError("Expected top-level JSON object to be a dictionary")

        self.name = data.get("name")
        self.sender = data.get("sender")
        self.last_update = self._parse_timestamp(data.get("last_update"))
        self.next_update = self._parse_timestamp(data.get("next_update"))
        self.legend = self._parse_legend(data.get("legend", {}))
        self.region_data = self._parse_region_data(data.get("content", {}))

    @staticmethod
    def _parse_legend(legend):
        """Parse the legend data from the raw JSON response."""
        parsed = {}
        for key, value in legend.items():
            if key.startswith("id") and "_desc" not in key:
                parsed[value] = {
                    "severity": int(key.replace("id", "")) - 1,
                    "desc": legend.get(key + "_desc"),
                }
        return parsed

    @staticmethod
    def _parse_region_data(region_data):
        parsed= {}
        for entry in region_data:
            region_name = entry.get("region_name")
            if not region_name:
                continue
            partregion = entry.get("partregion_name") or region_name
            pollen_data = entry.get("Pollen", {})
            parsed.setdefault(region_name, {})[partregion] = pollen_data
        return parsed

    @staticmethod
    def _parse_timestamp(timestamp_str):
        if not timestamp_str:
            return None
        return datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M Uhr").replace(tzinfo=TZ)

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
        if region not in self.region_data:
            raise ValueError(f"Region '{region}' not found")
        if partregion not in self.region_data[region]:
            raise ValueError(f"Partregion '{partregion}' not found")

        now = datetime.datetime.now(TZ).date()
        day_diff = (now + datetime.timedelta(days=days_ahead) - self.last_update.date()).days
        if day_diff < 0 or day_diff >= len(DAY_KEYS):
            return {}

        day_key = DAY_KEYS[day_diff]
        pollen_data = self.region_data[region][partregion]
        return {
            k: (
                self.legend.get(v.get(day_key), {}).get("severity"),
                self.legend.get(v.get(day_key), {}).get("desc"),
            )
            for k, v in pollen_data.items()
            if v.get(day_key)
        }

    def __repr__(self):
        """Return a string representation of the PollenApiDwd instance."""
        keys = list(self.__dict__.keys())
        return f"<PollenApiDwd keys={keys} regions={len(self.region_data)}>"


# Example usage
if __name__ == "__main__":

    async def main():
        client = PollenApiDwd()
        await client.fetch()

        print(client)
        print("Regionen:", ", ".join(client.regions))

        for region in client.regions:
            parts = ", ".join(client.partregions(region))
            print(f"Region: {region} | Partregions: {parts}")

        print("Last Update:", client.last_update)
        print("Next Update:", client.next_update)

        pollen_today = client.pollen(
            "Schleswig-Holstein und Hamburg", "Geest,Schleswig-Holstein und Hamburg"
        )
        print("Pollenflug heute:", pollen_today)

    asyncio.run(main())
