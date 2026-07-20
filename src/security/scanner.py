"""
Rinox Sentinel - Advanced Scanner
Deep file scanning, VirusTotal integration, malware detection
"""

import logging
from typing import Optional, Dict, Any
import aiohttp

logger = logging.getLogger("Rinox.Security.Scanner")


class AdvancedScanner:
    """Advanced file and URL scanning"""

    def __init__(self, cache=None):
        self.cache = cache

    async def scan_url_virustotal(self, url: str, api_key: str) -> Dict[str, Any]:
        """Scan a URL using VirusTotal API"""
        if not api_key:
            return {"risk_score": 0, "malicious": False, "error": "No API key"}

        try:
            async with aiohttp.ClientSession() as session:
                # Submit URL for analysis
                async with session.post(
                    "https://www.virustotal.com/api/v3/urls",
                    headers={"x-apikey": api_key},
                    data={"url": url}
                ) as resp:
                    if resp.status != 200:
                        return {"risk_score": 0, "malicious": False,
                                "error": f"VT API error: {resp.status}"}

                    result = await resp.json()
                    analysis_id = result.get("data", {}).get("id", "")

                # Get analysis results
                async with session.get(
                    f"https://www.virustotal.com/api/v3/analyses/{analysis_id}",
                    headers={"x-apikey": api_key}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        stats = data.get("data", {}).get("attributes", {}).get("stats", {})
                        malicious = stats.get("malicious", 0)
                        suspicious = stats.get("suspicious", 0)

                        return {
                            "risk_score": min((malicious + suspicious) * 20, 100),
                            "malicious": malicious > 0,
                            "malicious_count": malicious,
                            "suspicious_count": suspicious,
                            "total_scans": sum(stats.values()),
                        }

        except Exception as e:
            logger.warning(f"VirusTotal scan error: {e}")

        return {"risk_score": 0, "malicious": False, "error": "Scan failed"}

    async def check_google_safebrowsing(self, url: str, api_key: str) -> bool:
        """Check URL against Google Safe Browsing"""
        if not api_key:
            return False

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={api_key}",
                    json={
                        "client": {"clientId": "rinox-sentinel", "clientVersion": "1.0.0"},
                        "threatInfo": {
                            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"],
                            "platformTypes": ["ANY_PLATFORM"],
                            "threatEntryTypes": ["URL"],
                            "threatEntries": [{"url": url}]
                        }
                    }
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return "matches" in data and len(data["matches"]) > 0

        except Exception as e:
            logger.warning(f"Safe Browsing check error: {e}")

        return False