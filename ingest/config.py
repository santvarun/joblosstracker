"""Static configuration for the India job-loss tracker pipeline.

Holds the controlled vocabularies (sectors, regions), the geography lookups
(state -> region, city -> coordinates), and the news search queries. Keeping
these in one place makes the taxonomy auditable and the extractor deterministic.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Controlled vocabulary
# ---------------------------------------------------------------------------

# Sectors the extractor is allowed to assign. "Other" is the catch-all so the
# model never invents a new bucket. Keep this list stable -- changing it
# re-buckets historical data.
SECTORS: list[str] = [
    "Technology / IT Products",
    "IT Services",
    "Startups",
    "E-commerce",
    "Edtech",
    "Fintech",
    "Banking & Financial Services",
    "Telecom",
    "Manufacturing",
    "Automotive",
    "Retail & FMCG",
    "Media & Entertainment",
    "Healthcare & Pharma",
    "Aviation",
    "Logistics & Supply Chain",
    "Real Estate & Construction",
    "Consulting & Professional Services",
    "BPO / Customer Support",
    "Energy & Utilities",
    "Gaming",
    "Other",
]

REGIONS: list[str] = [
    "North",
    "South",
    "East",
    "West",
    "Central",
    "Northeast",
    "Pan-India",
    "Unknown",
]

# ---------------------------------------------------------------------------
# Geography
# ---------------------------------------------------------------------------

# Indian state / UT -> broad region. Used to derive a region when the article
# names a state or a city we can map to a state.
STATE_TO_REGION: dict[str, str] = {
    # North
    "Delhi": "North",
    "Haryana": "North",
    "Punjab": "North",
    "Uttar Pradesh": "North",
    "Uttarakhand": "North",
    "Himachal Pradesh": "North",
    "Jammu and Kashmir": "North",
    "Ladakh": "North",
    "Rajasthan": "North",
    "Chandigarh": "North",
    # South
    "Karnataka": "South",
    "Tamil Nadu": "South",
    "Kerala": "South",
    "Telangana": "South",
    "Andhra Pradesh": "South",
    "Puducherry": "South",
    # East
    "West Bengal": "East",
    "Bihar": "East",
    "Jharkhand": "East",
    "Odisha": "East",
    # West
    "Maharashtra": "West",
    "Gujarat": "West",
    "Goa": "West",
    # Central
    "Madhya Pradesh": "Central",
    "Chhattisgarh": "Central",
    # Northeast
    "Assam": "Northeast",
    "Meghalaya": "Northeast",
    "Manipur": "Northeast",
    "Mizoram": "Northeast",
    "Nagaland": "Northeast",
    "Tripura": "Northeast",
    "Arunachal Pradesh": "Northeast",
    "Sikkim": "Northeast",
}

# Major Indian cities -> (state, latitude, longitude). Used to place markers on
# the map and to infer state/region. Names are the canonical spellings the
# extractor is told to use.
CITY_INFO: dict[str, tuple[str, float, float]] = {
    "Bengaluru": ("Karnataka", 12.9716, 77.5946),
    "Hyderabad": ("Telangana", 17.3850, 78.4867),
    "Chennai": ("Tamil Nadu", 13.0827, 80.2707),
    "Mumbai": ("Maharashtra", 19.0760, 72.8777),
    "Pune": ("Maharashtra", 18.5204, 73.8567),
    "Delhi": ("Delhi", 28.7041, 77.1025),
    "New Delhi": ("Delhi", 28.6139, 77.2090),
    "Gurugram": ("Haryana", 28.4595, 77.0266),
    "Noida": ("Uttar Pradesh", 28.5355, 77.3910),
    "Kolkata": ("West Bengal", 22.5726, 88.3639),
    "Ahmedabad": ("Gujarat", 23.0225, 72.5714),
    "Jaipur": ("Rajasthan", 26.9124, 75.7873),
    "Chandigarh": ("Chandigarh", 30.7333, 76.7794),
    "Kochi": ("Kerala", 9.9312, 76.2673),
    "Thiruvananthapuram": ("Kerala", 8.5241, 76.9366),
    "Coimbatore": ("Tamil Nadu", 11.0168, 76.9558),
    "Indore": ("Madhya Pradesh", 22.7196, 75.8577),
    "Bhopal": ("Madhya Pradesh", 23.2599, 77.4126),
    "Nagpur": ("Maharashtra", 21.1458, 79.0882),
    "Lucknow": ("Uttar Pradesh", 26.8467, 80.9462),
    "Surat": ("Gujarat", 21.1702, 72.8311),
    "Vadodara": ("Gujarat", 22.3072, 73.1812),
    "Visakhapatnam": ("Andhra Pradesh", 17.6868, 83.2185),
    "Mysuru": ("Karnataka", 12.2958, 76.6394),
    "Mangaluru": ("Karnataka", 12.9141, 74.8560),
    "Mohali": ("Punjab", 30.7046, 76.7179),
    "Faridabad": ("Haryana", 28.4089, 77.3178),
    "Thane": ("Maharashtra", 19.2183, 72.9781),
    "Navi Mumbai": ("Maharashtra", 19.0330, 73.0297),
    "Bhubaneswar": ("Odisha", 20.2961, 85.8245),
    "Guwahati": ("Assam", 26.1445, 91.7362),
    "Patna": ("Bihar", 25.5941, 85.1376),
    "Nashik": ("Maharashtra", 19.9975, 73.7898),
    "Goa": ("Goa", 15.2993, 74.1240),
}

# ---------------------------------------------------------------------------
# News search queries
# ---------------------------------------------------------------------------

# Queries issued against Google News RSS. Each is scoped to India by the
# India edition parameters on the feed URL plus the word "India" where helpful.
SEARCH_QUERIES: list[str] = [
    "layoffs India",
    "job cuts India",
    "India tech layoffs",
    "Indian startup layoffs",
    "employees laid off India",
    "retrenchment India company",
    "India IT layoffs",
    "workforce reduction India",
    "AI layoffs India",
    "automation job losses India",
    "India company fires employees",
    "mass layoffs India",
]

# Extra queries used only for the historical backfill, paired with date windows.
BACKFILL_QUERIES: list[str] = [
    "layoffs India",
    "job cuts India",
    "Indian startup layoffs",
    "India tech layoffs",
    "AI layoffs India",
]
