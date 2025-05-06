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
        self.legend = {}
        self.last_update = None
        self.next_update = None
        self._pollendata = {}
        self._id2region = {}
        self._region2id = {}
        self._region_id2partregions = {}

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

        for entry in data.get("content"):
            region = entry.get("region_name")
            region_id = entry.get("region_id")
            partregion = entry.get("partregion_name") or region
            partregion_id = entry.get("partregion_id")
            data = entry.get("Pollen")

            self._id2region[region_id] = region
            self._region2id[region] = region_id
            self._region_id2partregions.setdefault(region_id, [])
            self._region_id2partregions[region_id].append(
                {"id": partregion_id,
                 "name": partregion}
            )
            self._pollendata.setdefault(region_id, {})
            self._pollendata[region_id][partregion_id] = self._parse_pollendata(data)

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

    def _parse_pollendata(self, pollendata):
        parsed = {}
        today = self.last_update
        for ptype, pdata in pollendata.items():
            for day, value in pdata.items():
                parsed.setdefault(day, {})[ptype] = (self.legend[value]["severity"], self.legend[value]["desc"])
        return parsed

    @staticmethod
    def _parse_timestamp(timestamp_str):
        if not timestamp_str:
            return None
        return datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M Uhr").replace(tzinfo=TZ)

    def region_id(self, region):
        return self._region2id[region]

    @property
    def regions(self):
        """Return the names of all regions available in the data."""
        return sorted(self._region2id.keys())

    def partregion_id(self, region, partregion):
        region_id = self.region_id(region)
        return next(entry["id"] for entry in self._region_id2partregions[region_id]
                    if entry["name"] == partregion)

    def partregions(self, region):
        """Return a list of partregions for the given region."""
        region_id = self.region_id(region)
        return [partregion["name"] for partregion in self._region_id2partregions[region_id]]

    def pollen(self, region, partregion, days_ahead=0):
        """Return a dictionary of pollen data for the specified region and partregion."""
        if region not in self.regions:
            raise ValueError(f"Region '{region}' not found")
        if partregion not in self.partregions(region):
            raise ValueError(f"Partregion '{partregion}' not found")

        now = datetime.datetime.now(TZ).date()
        day_diff = (now + datetime.timedelta(days=days_ahead) - self.last_update.date()).days
        if day_diff < 0 or day_diff >= len(DAY_KEYS):
            raise ValueError(f"No data available for requested day")

        day_key = DAY_KEYS[day_diff]
        region_id = self.region_id(region)
        partregion_id = self.partregion_id(region, partregion)
        pollen_data = self._pollendata[region_id][partregion_id].get(day_key)
        return pollen_data

    def region_id(self, region_name):
        return self._region2id.get(region_name)

    def __repr__(self):
        """Return a string representation of the PollenApiDwd instance."""
        keys = list(self.__dict__.keys())
        return f"<PollenApiDwd keys={keys} regions={len(self.regions)}>"


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
            "Schleswig-Holstein und Hamburg",
            "Geest,Schleswig-Holstein und Hamburg",
        )
        print("Pollenflug heute:", pollen_today)
        print(f"Region ID Bayern | Mainfranken: {client.region_id('Bayern')} | {client.partregion_id('Bayern', 'Mainfranken')}")

    asyncio.run(main())
