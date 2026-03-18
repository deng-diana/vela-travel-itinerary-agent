"""Visa requirements tool.

Returns entry requirements for a destination based on the traveller's passport nationality.
Data covers the most common tourist destinations; falls back to a generic advisory for
unknown destinations.
"""
from __future__ import annotations

from src.tools.schemas import VisaInput, VisaRequirements

# nationality code → list of destination keywords that are visa-exempt
_BASE_DOCS = ["Valid passport (6+ months validity)", "Return/onward ticket", "Proof of sufficient funds"]

# destination keyword → { nationality → VisaRequirements dict }
_VISA_DB: dict[str, dict[str, dict]] = {
    "japan": {
        "US": dict(visa_type="Visa-exempt", max_stay_days=90, required_docs=_BASE_DOCS,
                   fee_usd=0, notes="US citizens can stay up to 90 days. Register at hotel on arrival.",
                   official_link="https://www.mofa.go.jp/j_info/visit/visa/short/novisa.html"),
        "UK": dict(visa_type="Visa-exempt", max_stay_days=90, required_docs=_BASE_DOCS,
                   fee_usd=0, notes="UK citizens can stay up to 90 days.",
                   official_link="https://www.mofa.go.jp/j_info/visit/visa/short/novisa.html"),
        "AU": dict(visa_type="Visa-exempt", max_stay_days=90, required_docs=_BASE_DOCS,
                   fee_usd=0, notes="Australian citizens can stay up to 90 days.",
                   official_link="https://www.mofa.go.jp/j_info/visit/visa/short/novisa.html"),
        "CA": dict(visa_type="Visa-exempt", max_stay_days=90, required_docs=_BASE_DOCS,
                   fee_usd=0, notes="Canadian citizens can stay up to 90 days.",
                   official_link="https://www.mofa.go.jp/j_info/visit/visa/short/novisa.html"),
        "DEFAULT": dict(visa_type="Check required", max_stay_days=None,
                        required_docs=["Valid passport"], fee_usd=None,
                        notes="Check Japan's Ministry of Foreign Affairs for your nationality.",
                        official_link="https://www.mofa.go.jp/j_info/visit/visa/index.html"),
    },
    "france": {
        "US": dict(visa_type="Visa-exempt (Schengen)", max_stay_days=90, required_docs=_BASE_DOCS,
                   fee_usd=0, notes="90 days within any 180-day period across the Schengen Area. ETIAS required from 2025.",
                   official_link="https://france-visas.gouv.fr"),
        "UK": dict(visa_type="Visa-exempt", max_stay_days=90, required_docs=_BASE_DOCS,
                   fee_usd=0, notes="UK citizens can visit without a visa for up to 90 days.",
                   official_link="https://france-visas.gouv.fr"),
        "AU": dict(visa_type="Visa-exempt (Schengen)", max_stay_days=90, required_docs=_BASE_DOCS,
                   fee_usd=0, notes="90 days within any 180-day Schengen period.",
                   official_link="https://france-visas.gouv.fr"),
        "DEFAULT": dict(visa_type="Schengen Visa may be required", max_stay_days=90,
                        required_docs=["Valid passport (3+ months beyond stay)", "Travel insurance", "Hotel bookings"],
                        processing_days=15, fee_usd=85,
                        notes="Apply at French consulate in your country 3-4 weeks before travel.",
                        official_link="https://france-visas.gouv.fr"),
    },
    "thailand": {
        "US": dict(visa_type="Visa-exempt", max_stay_days=60, required_docs=_BASE_DOCS,
                   fee_usd=0, notes="60-day visa-exempt entry. Extendable by 30 days at immigration.",
                   official_link="https://www.thaiembassy.com/thailand-visa/visa-exemption"),
        "UK": dict(visa_type="Visa-exempt", max_stay_days=60, required_docs=_BASE_DOCS,
                   fee_usd=0, notes="60-day entry without visa.",
                   official_link="https://www.thaiembassy.com/thailand-visa/visa-exemption"),
        "AU": dict(visa_type="Visa-exempt", max_stay_days=60, required_docs=_BASE_DOCS,
                   fee_usd=0, notes="60-day entry without visa.",
                   official_link="https://www.thaiembassy.com/thailand-visa/visa-exemption"),
        "DEFAULT": dict(visa_type="Visa on Arrival (VOA) available for many nationalities",
                        max_stay_days=30, required_docs=["Valid passport", "1 passport photo", "Return ticket", "THB 10,000 cash"],
                        processing_days=0, fee_usd=35,
                        notes="VOA queue at Bangkok Suvarnabhumi. Consider e-Visa to skip the queue.",
                        official_link="https://www.thaiembassy.com/thailand-visa/visa-on-arrival"),
    },
    "italy": {
        "US": dict(visa_type="Visa-exempt (Schengen)", max_stay_days=90, required_docs=_BASE_DOCS,
                   fee_usd=0, notes="90 days per 180-day Schengen period. ETIAS required from 2025.",
                   official_link="https://vistoperitalia.esteri.it"),
        "UK": dict(visa_type="Visa-exempt", max_stay_days=90, required_docs=_BASE_DOCS,
                   fee_usd=0, notes="90 days without a visa for UK passport holders.",
                   official_link="https://vistoperitalia.esteri.it"),
        "DEFAULT": dict(visa_type="Schengen Visa may be required", max_stay_days=90,
                        required_docs=["Valid passport", "Travel insurance", "Bank statements", "Hotel bookings"],
                        processing_days=15, fee_usd=85,
                        notes="Apply at Italian consulate 4-6 weeks before travel.",
                        official_link="https://vistoperitalia.esteri.it"),
    },
    "singapore": {
        "US": dict(visa_type="Visa-exempt", max_stay_days=90, required_docs=_BASE_DOCS,
                   fee_usd=0, notes="90-day visa-free stay. Fill in SG Arrival Card digitally before landing.",
                   official_link="https://www.ica.gov.sg/enter-transit-depart/entering-singapore"),
        "UK": dict(visa_type="Visa-exempt", max_stay_days=90, required_docs=_BASE_DOCS,
                   fee_usd=0, notes="90-day visa-free stay.",
                   official_link="https://www.ica.gov.sg/enter-transit-depart/entering-singapore"),
        "DEFAULT": dict(visa_type="Check required", max_stay_days=30,
                        required_docs=["Valid passport", "Return ticket"],
                        fee_usd=None,
                        notes="Most nationalities can enter Singapore visa-free for 30 days. Verify at ICA.",
                        official_link="https://www.ica.gov.sg/enter-transit-depart/entering-singapore"),
    },
    "bali": {
        "US": dict(visa_type="Visa on Arrival", max_stay_days=30, required_docs=_BASE_DOCS,
                   fee_usd=35, processing_days=0,
                   notes="Extendable once for another 30 days. Pay in USD/IDR at airport.",
                   official_link="https://molina.imigrasi.go.id"),
        "UK": dict(visa_type="Visa on Arrival", max_stay_days=30, required_docs=_BASE_DOCS,
                   fee_usd=35, processing_days=0,
                   notes="Extendable once for another 30 days.",
                   official_link="https://molina.imigrasi.go.id"),
        "DEFAULT": dict(visa_type="Visa on Arrival", max_stay_days=30,
                        required_docs=["Valid passport (6+ months)", "Return ticket"],
                        fee_usd=35, processing_days=0,
                        notes="Visa on arrival available for most nationalities at Ngurah Rai Airport.",
                        official_link="https://molina.imigrasi.go.id"),
    },
    "indonesia": {
        "DEFAULT": dict(visa_type="Visa on Arrival", max_stay_days=30,
                        required_docs=["Valid passport (6+ months)", "Return ticket"],
                        fee_usd=35, processing_days=0,
                        notes="Most nationalities receive 30-day VoA, extendable once.",
                        official_link="https://molina.imigrasi.go.id"),
    },
    "vietnam": {
        "US": dict(visa_type="E-Visa", max_stay_days=90, required_docs=["Valid passport", "Digital photo", "Online application"],
                   fee_usd=25, processing_days=3,
                   notes="Apply online at least 3 business days before travel. Multiple-entry available.",
                   official_link="https://evisa.xuatnhapcanh.gov.vn"),
        "UK": dict(visa_type="E-Visa", max_stay_days=90, required_docs=["Valid passport", "Digital photo"],
                   fee_usd=25, processing_days=3,
                   notes="90-day e-Visa, multiple entry.",
                   official_link="https://evisa.xuatnhapcanh.gov.vn"),
        "DEFAULT": dict(visa_type="E-Visa", max_stay_days=90,
                        required_docs=["Valid passport", "Digital photo", "Credit card for online payment"],
                        fee_usd=25, processing_days=3,
                        notes="Apply online. E-Visa available to most nationalities.",
                        official_link="https://evisa.xuatnhapcanh.gov.vn"),
    },
}

_GENERIC_ADVISORY = dict(
    visa_type="Research required",
    max_stay_days=None,
    required_docs=["Valid passport", "Return ticket"],
    fee_usd=None,
    notes=(
        "Visa requirements vary. Check your government's travel advisory and "
        "the destination country's embassy website for up-to-date information."
    ),
    official_link=None,
)


def get_visa_requirements(inp: VisaInput) -> VisaRequirements:
    destination_key = _match_destination(inp.destination)
    nationality_upper = inp.nationality.upper()

    if destination_key is None:
        data = dict(_GENERIC_ADVISORY)
    else:
        dest_data = _VISA_DB[destination_key]
        data = dest_data.get(nationality_upper) or dest_data.get("DEFAULT") or dict(_GENERIC_ADVISORY)

    return VisaRequirements(
        destination=inp.destination,
        nationality=inp.nationality,
        visa_type=data.get("visa_type", "Research required"),
        max_stay_days=data.get("max_stay_days"),
        required_docs=data.get("required_docs", []),
        processing_days=data.get("processing_days"),
        fee_usd=data.get("fee_usd"),
        notes=data.get("notes", ""),
        official_link=data.get("official_link"),
    )


def _match_destination(destination: str) -> str | None:
    lower = destination.lower()
    for key in _VISA_DB:
        if key in lower or lower in key:
            return key
    return None
